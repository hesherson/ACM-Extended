"""Bake the mesh maps that drive the Hardigg shell textures. Runs inside Blender (Cycles):

  blender -b -P bake_hardigg_surface.py -- <acme_medchest_b2 folder> <medchest.p3d> <output folder>

Writes three 2048 x 4096 float arrays (.npy) in the layout of the shell atlas:
  hardigg_bake_ao      ambient occlusion, base and lid baked apart so neither shadows the other's rim
  hardigg_bake_normal  model space normal (Blender axes), 0.5 + 0.5 n
  hardigg_bake_pos     model space position, scaled to the box x -0.3..0.3, y -0.2..0.2, z 0..0.85
build_hardigg_surface.py --bake <output folder> turns them into the masks in tools/assets, so Blender is only
needed when the shell changes.
"""
import importlib.util
import sys
from pathlib import Path

import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
SOURCE, MODEL, OUT = Path(args[0]), Path(args[1]), Path(args[2])
SIZE = (2048, 4096)
OUT.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("mc_p3d", SOURCE / "acme_medchest_src/build/mc_p3d.py")
io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)
lod = io.read_p3d(str(MODEL))[0]
lid = lod["sels"].get("lid", set())
groups = {"base": [], "lid": [], "base_proud": [], "lid_proud": [], "hardware": []}
ROOM = ((-0.2275, 0.2275), (-0.1335, 0.1425), (0.0465, 0.8035))      # the interior of the case, x, y and z
INNER = ((1320, 1632, 704, 704),)                            # the atlas tile of the inside of the case
PROUD = 0.1502                                               # ribs stand out of the lid and back panels past this depth


def outside(face):
    """The inner skin of the lid shares its texels with the outer one. Only the outer skin is baked there."""
    points = np.array([lod["verts"][i] for i in face["v"]])
    u, v = np.mean(face["uv"], axis=0)
    px, py = u * SIZE[0], (1 - v) * SIZE[1]
    if any(x <= px < x + w and y <= py < y + h for x, y, w, h in INNER):
        return True
    return not all(low <= value <= high for value, (low, high) in zip(points.mean(0), ROOM))


def proud(face):
    """A rib lies on the panel, and the panel under it has the same texels. The rib is baked last, over it."""
    return abs(np.mean([lod["verts"][i][1] for i in face["v"]])) > PROUD


for face in lod["faces"]:
    if "lid_artwork" in face["tex"].lower():                 # decals lie on the lid: they must not shadow it
        continue
    if not face["tex"].lower().endswith("case_co.paa") or not outside(face):
        groups["hardware"].append(face)
    else:
        groups[("lid" if all(i in lid for i in face["v"]) else "base") + ("_proud" if proud(face) else "")].append(face)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 96
scene.render.bake.margin = 12
scene.render.bake.use_clear = False
objects = {}
for name, faces in groups.items():
    used = sorted({i for f in faces for i in f["v"]})
    index = {old: new for new, old in enumerate(used)}
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([lod["verts"][i] for i in used], [], [[index[i] for i in f["v"]] for f in faces])
    layer = mesh.uv_layers.new(name="uv")
    for poly, face in zip(mesh.polygons, faces):
        poly.use_smooth = True
        for k, loop in enumerate(poly.loop_indices):
            layer.data[loop].uv = face["uv"][k]
    mesh.update()
    sharp = {(index[a], index[b]) for a, b in lod["sharp"] if a in index and b in index}
    for edge in mesh.edges:                                  # keep the hard edges of the model hard
        a, b = edge.vertices
        edge.use_edge_sharp = (a, b) in sharp or (b, a) in sharp
    objects[name] = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(objects[name])

image = bpy.data.images.new("bake", SIZE[0], SIZE[1], float_buffer=True, is_data=True)
material = bpy.data.materials.new("bake")
material.use_nodes = True
nodes, links = material.node_tree.nodes, material.node_tree.links
nodes.clear()
target = nodes.new("ShaderNodeTexImage")
target.image = image
emission = nodes.new("ShaderNodeEmission")
output = nodes.new("ShaderNodeOutputMaterial")
links.new(emission.outputs[0], output.inputs["Surface"])
geometry = nodes.new("ShaderNodeNewGeometry")
scale = nodes.new("ShaderNodeVectorMath")
scale.operation = "MULTIPLY_ADD"
SKIN = ("base", "lid", "base_proud", "lid_proud")
for name in SKIN:
    objects[name].data.materials.append(material)
nodes.active = target


def run(names, margin, feed):
    """Bake these objects into a cleared image. The other half of the case is hidden, the rest occludes."""
    image.pixels.foreach_set(np.zeros(SIZE[0] * SIZE[1] * 4, np.float32))
    scene.render.bake.margin = margin
    for name in names:
        # A rib and the panel it rises from are one moulded skin: neither shades the other. The fittings do.
        for other in SKIN:
            objects[other].hide_render = other != name
        for obj in bpy.data.objects:
            obj.select_set(obj.name == name)
        bpy.context.view_layer.objects.active = objects[name]
        emit = feed()
        bpy.ops.object.bake(type="EMIT" if emit else "AO")
    for other in SKIN:
        objects[other].hide_render = False
    pixels = np.empty(SIZE[0] * SIZE[1] * 4, np.float32)
    image.pixels.foreach_get(pixels)
    return pixels.reshape(SIZE[1], SIZE[0], 4)[::-1, :, :3].copy()


def bake(kind, feed):
    """feed() wires the emission input, or returns False for the built in occlusion pass."""
    pixels = run(("base", "lid"), 12, feed)
    pixels = np.where(COVER, run(("base_proud", "lid_proud"), 0, feed), pixels)
    np.save(OUT / f"hardigg_bake_{kind}.npy", np.clip(pixels, 0, 1).astype(np.float16))
    print("baked", kind, float(pixels.mean()))


def white():
    for link in list(emission.inputs["Color"].links):
        links.remove(link)
    emission.inputs["Color"].default_value = (1, 1, 1, 1)
    return True


def wire(socket, vector=None):
    for link in list(emission.inputs["Color"].links):
        links.remove(link)
    if vector:
        mul, add = vector
        for link in list(scale.inputs[0].links):
            links.remove(link)
        links.new(socket, scale.inputs[0])
        scale.inputs[1].default_value, scale.inputs[2].default_value = mul, add
        links.new(scale.outputs[0], emission.inputs["Color"])
    else:
        links.new(socket, emission.inputs["Color"])
    return True


COVER = run(("base_proud", "lid_proud"), 0, white)[..., :1] > 0.5       # the texels the ribs own
print("rib texels", int(COVER.sum()))
np.save(OUT / "hardigg_bake_rib.npy", COVER[..., 0])
bake("ao", lambda: False)
bake("normal", lambda: wire(geometry.outputs["Normal"], ((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))))
bake("pos", lambda: wire(geometry.outputs["Position"], ((1 / 0.6, 1 / 0.4, 1 / 0.85), (0.5, 0.5, 0.0))))
