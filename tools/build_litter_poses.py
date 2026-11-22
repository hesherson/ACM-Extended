#!/usr/bin/env python3
"""Poses of a casualty on a litter, made from ACM's lying pose (addons/core/anim/ACM_LyingState.rtm).

The trunk and the head stay exactly as they are in the lying pose, so the place of the casualty on a litter
(fn_align.sqf) is the same in every pose. Only the limbs are set:

  side    legs straight and together, arms along the body, palms on the thighs: SKED, and any litter with the HPMK
  cross   legs straight and together, forearms crossed on the chest, palms down: Talon II

For each pose one file is written to addons/acme_sked_ace/anim: acme_litter_<pose>.rtm, the pose, held.
(between() can make a transition from one pose to another; the game does not use one: the casualty is put on the
litter at once.)

  python tools/build_litter_poses.py [--output <folder>]

Axes of an RTM in this file: X, Y level, Z up, the ground at Z = 0. A bone matrix is absolute: it takes a point of
the bind pose to its place in the pose. The joints of the bind pose are in tools/assets/man_skeleton.json.
"""
import argparse
import io
import json
import math
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "addons/core/anim/ACM_LyingState.rtm"
OUTPUT = ROOT / "addons/acme_sked_ace/anim"
PIV = {k: np.array(v, float) for k, v in json.loads((Path(__file__).with_name("assets") / "man_skeleton.json").read_text()).items()}
SECONDS, FPS = 2.4, 30

H = [("pelvis", ""), ("spine", "pelvis"), ("spine1", "spine"), ("spine2", "spine1"), ("spine3", "spine2"),
     ("camera", "pelvis"), ("weapon", "spine1"), ("launcher", "spine1"), ("neck", "spine3"), ("neck1", "neck"), ("head", "neck1")]
for s in ("left", "right"):
    H += [(s + "shoulder", "spine3"), (s + "arm", s + "shoulder"), (s + "armroll", s + "arm"), (s + "forearm", s + "armroll"),
          (s + "forearmroll", s + "forearm"), (s + "hand", s + "forearmroll"),
          (s + "handring", s + "hand"), (s + "handring1", s + "handring"), (s + "handring2", s + "handring1"), (s + "handring3", s + "handring2"),
          (s + "handpinky1", s + "handring"), (s + "handpinky2", s + "handpinky1"), (s + "handpinky3", s + "handpinky2"),
          (s + "handmiddle1", s + "hand"), (s + "handmiddle2", s + "handmiddle1"), (s + "handmiddle3", s + "handmiddle2"),
          (s + "handindex1", s + "hand"), (s + "handindex2", s + "handindex1"), (s + "handindex3", s + "handindex2"),
          (s + "handthumb1", s + "hand"), (s + "handthumb2", s + "handthumb1"), (s + "handthumb3", s + "handthumb2"),
          (s + "upleg", "pelvis"), (s + "uplegroll", s + "upleg"), (s + "leg", s + "uplegroll"), (s + "legroll", s + "leg"),
          (s + "foot", s + "legroll"), (s + "toebase", s + "foot")]
PARENT = dict(H)


# ---------------------------------------------------------------- RTM files
def read_rtm(path):
    f = io.BytesIO(Path(path).read_bytes())
    if f.read(8) != b"RTM_0101":
        raise ValueError("%s is not a plain RTM" % path)
    f.read(12)
    frames, count = struct.unpack("<2I", f.read(8))
    names = [f.read(32).split(b"\0", 1)[0].decode() for _ in range(count)]
    mats = np.zeros((frames, count, 4, 4))
    mats[:, :, 3, 3] = 1
    for i in range(frames):
        f.read(4)
        for j in range(count):
            f.read(32)
            d = struct.unpack("<12f", f.read(48))
            mats[i, j, :3, :] = [[d[0], d[6], d[3], d[9]], [d[2], d[8], d[5], d[11]], [d[1], d[7], d[4], d[10]]]
    return names, mats


def write_rtm(path, names, mats):
    out = io.BytesIO()
    out.write(b"RTM_0101" + struct.pack("<3f", 0, 0, 0) + struct.pack("<2I", len(mats), len(names)))
    for name in names:
        out.write(name.encode().ljust(32, b"\0"))
    for i, frame in enumerate(mats):
        out.write(struct.pack("<f", i / max(1, len(mats) - 1)))
        for name, m in zip(names, frame):
            out.write(name.encode().ljust(32, b"\0"))
            out.write(struct.pack("<12f", m[0, 0], m[2, 0], m[1, 0], m[0, 2], m[2, 2], m[1, 2],
                                  m[0, 1], m[2, 1], m[1, 1], m[0, 3], m[2, 3], m[1, 3]))
    Path(path).write_bytes(out.getvalue())


# ---------------------------------------------------------------- small geometry
def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def joint(pose, bone):
    return pose[bone][:3, :3] @ PIV[bone] + pose[bone][:3, 3]


def turn(a, b):
    """The smallest rotation that takes direction a to direction b."""
    a, b = unit(a), unit(b)
    axis = np.cross(a, b)
    s, c = np.linalg.norm(axis), float(a @ b)
    if s < 1e-9:
        return np.eye(3)
    k = axis / s
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + s * K + (1 - c) * (K @ K)


def spin(axis, angle):
    """The rotation by an angle (radians) about an axis."""
    k = unit(axis)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(angle) * K + (1 - math.cos(angle)) * (K @ K)


def roll_leg(pose, side, sign, left, up, degrees):
    """Roll a whole leg in the hip, about the line from the hip to the ankle, until its toes point outward by so
    many degrees (seen from the foot end, against straight up)."""
    hip = joint(pose, side + "upleg")
    ankle = joint(pose, side + "foot")

    def out(p):
        toe = unit(joint(p, side + "toebase") - joint(p, side + "foot"))
        return math.degrees(math.atan2(sign * (toe @ left), toe @ up))

    need = degrees - out(pose)
    R = spin(ankle - hip, math.radians(need))
    # (which way round is outward is found by trying)
    trial = {b: m.copy() for b, m in pose.items()}
    swing(trial, side + "upleg", hip, R)
    if abs(out(trial) - degrees) > abs(need):
        R = spin(ankle - hip, -math.radians(need))
    swing(pose, side + "upleg", hip, R)


def about(point, R):
    m = np.eye(4)
    m[:3, :3] = R
    m[:3, 3] = point - R @ point
    return m


def tree(bone):
    out = [bone]
    for child, parent in H:
        if parent in out:
            out.append(child)
    return out


def swing(pose, bone, point, R):
    """Turn a bone and everything that hangs on it about a point."""
    m = about(point, R)
    for b in tree(bone):
        pose[b] = m @ pose[b]


def frame(first, second):
    x = unit(first)
    y = unit(second - (second @ x) * x)
    return np.stack([x, y, np.cross(x, y)], 1)


def hand_to(pose, side, wrist, fingers, palm):
    """Put a hand at a wrist place with its fingers along one direction and its palm facing another.
    NOT USED: seen in the game on 2026-11-17, the hands came out palm up with the fingers in the air. The finger
    joints of the bind pose in man_skeleton.json are not good enough to build a hand frame from (fingers hardly move
    in the animations they were solved from). The hands now simply stay on their forearms as they are in the lying
    pose, which keeps the wrists straight and the palms the way the forearm turns them."""
    name = side + "hand"
    f = unit(PIV[side + "handmiddle1"] - PIV[name])
    across = PIV[side + "handpinky1"] - PIV[side + "handindex1"]
    F = frame(f, across)
    n = np.cross(F[:, 1], F[:, 0]) if side == "left" else np.cross(F[:, 0], F[:, 1])
    bind = np.stack([F[:, 0], F[:, 1], n], 1)
    f = unit(fingers)
    n = unit(palm - (palm @ f) * f)
    a = np.cross(f, n) if side == "left" else np.cross(n, f)
    R = np.stack([f, a, n], 1) @ np.linalg.inv(bind)
    new = np.eye(4)
    new[:3, :3] = R
    new[:3, 3] = wrist - R @ PIV[name]
    move = new @ np.linalg.inv(pose[name])
    for b in tree(name):
        pose[b] = move @ pose[b]


def limb(pose, upper, lower, end, target, hint):
    """Two bones: bring the joint of `end` to the target, with the middle joint toward the hint."""
    root = joint(pose, upper)
    l1 = np.linalg.norm(PIV[lower] - PIV[upper])
    l2 = np.linalg.norm(PIV[end] - PIV[lower])
    reach = target - root
    d = min(np.linalg.norm(reach), l1 + l2 - 1e-4)
    n = unit(reach)
    along = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    side = unit(hint - (hint @ n) * n)
    middle = root + along * n + math.sqrt(max(l1 * l1 - along * along, 0)) * side
    swing(pose, upper, root, turn(joint(pose, lower) - root, middle - root))
    middle = joint(pose, lower)
    swing(pose, lower, middle, turn(joint(pose, end) - middle, root + d * n - middle))
    return joint(pose, lower), joint(pose, end)


# ---------------------------------------------------------------- the poses
def body_frame(pose):
    """Origin at the pelvis on the ground; unit vectors toward the head, toward the casualty's left, and up."""
    pelvis, neck = joint(pose, "pelvis"), joint(pose, "neck")
    head = neck - pelvis
    head[2] = 0
    head = unit(head)
    left = joint(pose, "leftarm") - joint(pose, "rightarm")
    left[2] = 0
    left = unit(left - (left @ head) * head)
    origin = pelvis.copy()
    origin[2] = 0
    return origin, head, left, np.array([0.0, 0.0, 1.0])


def legs(pose):
    origin, head, left, up = body_frame(pose)
    for side, sign in (("left", 1), ("right", -1)):
        hip = joint(pose, side + "upleg")
        length = np.linalg.norm(PIV[side + "leg"] - PIV[side + "upleg"]) + np.linalg.norm(PIV[side + "foot"] - PIV[side + "leg"])
        # the ankle 9 cm from the middle line, resting 7 cm over the ground; the knee a little up, never locked
        lateral = (hip - origin) @ left
        ankle = origin + head * ((hip - origin) @ head) + left * (sign * 0.09) + up * 0.07
        ankle = ankle - head * math.sqrt(max((length * 0.997) ** 2 - (sign * 0.09 - lateral) ** 2 - (0.07 - hip[2]) ** 2, 0))
        limb(pose, side + "upleg", side + "leg", side + "foot", ankle, up)
        # The foot keeps the ankle of the lying pose this is made from; the toes fall a little outward because
        # the whole leg rolls in the hip. (A foot turned at the ankle alone looked broken in the game.)
        roll_leg(pose, side, sign, left, up, 18)


def pose_side(source):
    pose = {b: m.copy() for b, m in source.items()}
    legs(pose)
    origin, head, left, up = body_frame(pose)
    for side, sign in (("left", 1), ("right", -1)):
        # The arms lie tight against the body, so that every strap of a litter can go round body and arms
        # together and nothing of an arm stands out through one: the upper arm at the ribs, the forearm at the
        # waist, the hand fallen against the thigh. Seen in game: with the elbows bent outward the SKED's and the
        # Talon's straps cut through the arms (2026-11-19).
        # They are limp, and no two limp arms lie alike: the forearm fallen onto its little-finger side, the
        # wrist sagging, the fingers curled.
        out, along, height, half_turn, sag, curl, inward = ARMS[side]
        wrist = origin + left * (sign * out) - head * along + up * height
        elbow, wrist = limb(pose, side + "arm", side + "forearm", side + "hand", wrist, left * sign * 0.25 - up * 1.0)
        aim = -head * math.cos(math.radians(inward)) - left * (sign * math.sin(math.radians(inward)))
        relax_hand(pose, side, up, half_turn, sag, curl, aim)
    return pose


# for each arm: the wrist's place (out from the middle line, toward the feet from the pelvis, over the deck), how
# far the forearm has fallen onto its little-finger side (degrees; 90: the palm faces the thigh), how far the
# wrist sags toward the palm (degrees), how much the fingers curl (1 = a hand at rest), and how far the hand
# points in toward the thigh (degrees)
ARMS = {"left": (0.198, 0.063, 0.080, 30, 5, 1.0, 3),
        "right": (0.200, 0.086, 0.078, 24, 7, 1.12, 5)}
# a hand at rest on something: the bend in each joint of a finger, from the knuckle outward (degrees; the knuckle
# is bent back a little, so that the finger stands on its tip like an arch); it grows toward the little finger
CURL = {"index": (-6, 30, 14), "middle": (-8, 34, 16), "ring": (-8, 38, 18), "pinky": (-6, 40, 20)}
FINGERS = ("index", "middle", "ring", "pinky", "thumb")


def relax_hand(pose, side, up, half_turn, sag, curl, aim):
    """Make a hand limp. It comes in as the lying pose has it: the palm down."""
    hand = side + "hand"
    # The fingers take the hand's own shape first (as the model is built: together, nearly straight). The lying
    # pose has the ring and the little finger turned 14 degrees sideways, away from the middle finger: a gap.
    for b in tree(hand):
        pose[b] = pose[hand].copy()
    # the hand points along the body (the lying pose has one hand turned in and the other turned out)
    point = joint(pose, hand)
    now = joint(pose, hand + "middle1") - point
    angle = math.atan2(aim[1], aim[0]) - math.atan2(now[1], now[0])
    swing(pose, hand, point, spin(up, angle))

    wrist = joint(pose, hand)
    fingers = unit(joint(pose, hand + "middle1") - wrist)
    across = joint(pose, hand + "pinky1") - joint(pose, hand + "index1")
    across = unit(across - (across @ fingers) * fingers)
    normal = unit(np.cross(fingers, across))
    if normal @ up > 0:
        normal = -normal

    def bend(bone, axis, degrees, moves, toward):
        """Turn a bone about its joint so that a point that moves with it goes toward a direction (negative
        degrees: away from it)."""
        point = joint(pose, bone)
        R = spin(axis, math.radians(abs(degrees)))
        if ((R @ (moves - point) + point) - moves) @ toward < 0:
            R = R.T
        if degrees < 0:
            R = R.T
        swing(pose, bone, point, R)

    # the fingers curl toward the palm, each about the line across its own knuckle
    for finger, angles in CURL.items():
        along = unit(joint(pose, hand + finger + "2") - joint(pose, hand + finger + "1"))
        hinge = unit(np.cross(normal, along))
        for i, degrees in enumerate(angles):
            bone = hand + finger + str(i + 1)
            here = joint(pose, bone)
            ahead = here + unit(joint(pose, hand + finger + "3") - joint(pose, hand + finger + "2")) * 0.02
            bend(bone, hinge, degrees * curl, ahead, normal)
    # the thumb falls in under the palm's edge and bends toward the fingers
    tip = joint(pose, hand + "thumb3")
    bend(hand + "thumb1", fingers, 16 * curl, tip, normal)
    bend(hand + "thumb2", normal, 10 * curl, joint(pose, hand + "thumb3"), across)
    here = joint(pose, hand + "thumb3")
    bend(hand + "thumb3", normal, 14 * curl, here + unit(here - joint(pose, hand + "thumb2")) * 0.02, across)
    # the wrist sags: the hand hangs toward its palm
    bend(hand, across, sag, joint(pose, hand + "middle1"), normal)
    # the forearm falls onto its little-finger side: the thumb comes up
    elbow = joint(pose, side + "forearm")
    point = joint(pose, hand)
    before = joint(pose, hand + "thumb2")
    R = spin(point - elbow, math.radians(half_turn))
    if (R @ (before - point) + point)[2] < before[2]:
        R = R.T
    swing(pose, side + "forearmroll", point, R)


def pose_cross(source):
    pose = {b: m.copy() for b, m in source.items()}
    legs(pose)
    origin, head, left, up = body_frame(pose)
    chest = (joint(pose, "spine3") - origin) @ head
    # The right forearm lies on the chest, the left one over it. Each hand rests toward the other side.
    for side, sign, along, height in (("right", -1, chest - 0.115, 0.265), ("left", 1, chest - 0.050, 0.300)):
        wrist = origin + head * along - left * (sign * 0.075) + up * height
        elbow, wrist = limb(pose, side + "arm", side + "forearm", side + "hand", wrist, left * sign * 1.0 - head * 0.55 - up * 0.25)
    return pose


# ---------------------------------------------------------------- from one pose to another
def quaternion(R):
    # The nearest true rotation first (the matrices of the source are a little off), then the largest term first.
    u, _, vt = np.linalg.svd(R)
    R = u @ np.diag([1.0, 1.0, np.linalg.det(u @ vt)]) @ vt
    trace = R[0, 0] + R[1, 1] + R[2, 2]
    if trace > 0:
        w = math.sqrt(1 + trace) / 2
        return np.array([w, (R[2, 1] - R[1, 2]) / (4 * w), (R[0, 2] - R[2, 0]) / (4 * w), (R[1, 0] - R[0, 1]) / (4 * w)])
    i = int(np.argmax([R[0, 0], R[1, 1], R[2, 2]]))
    j, k = (i + 1) % 3, (i + 2) % 3
    q = np.zeros(4)
    q[1 + i] = math.sqrt(max(1 + R[i, i] - R[j, j] - R[k, k], 0)) / 2
    q[0] = (R[k, j] - R[j, k]) / (4 * q[1 + i])
    q[1 + j] = (R[j, i] + R[i, j]) / (4 * q[1 + i])
    q[1 + k] = (R[k, i] + R[i, k]) / (4 * q[1 + i])
    return q


def rotation(q):
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def slerp(R0, R1, s):
    a, b = quaternion(R0), quaternion(R1)
    dot = float(a @ b)
    if dot < 0:
        b, dot = -b, -dot
    if dot > 0.9995:
        return rotation(a + s * (b - a))
    angle = math.acos(min(dot, 1.0))
    return rotation((math.sin((1 - s) * angle) * a + math.sin(s * angle) * b) / math.sin(angle))


def between(first, last, s):
    """A pose between two: every joint turns from one to the other on its parent, so no limb stretches."""
    out = {}
    for bone, parent in H:
        R0, R1 = first[bone][:3, :3], last[bone][:3, :3]
        if bone not in PIV:                                  # camera and weapon bones ride on their parent
            out[bone] = out[parent] @ np.linalg.inv(first[parent]) @ first[bone]
            continue
        if not parent:
            R = slerp(R0, R1, s)
            place = (1 - s) * joint(first, bone) + s * joint(last, bone)
        else:
            P0, P1 = first[parent], last[parent]
            R = out[parent][:3, :3] @ slerp(P0[:3, :3].T @ R0, P1[:3, :3].T @ R1, s)
            # where the joint sits on its parent, which in an authored pose is not always exactly the bind place
            rest = out[parent][:3, :3] @ PIV[bone] + out[parent][:3, 3]
            slack0 = P0[:3, :3].T @ (joint(first, bone) - (P0[:3, :3] @ PIV[bone] + P0[:3, 3]))
            slack1 = P1[:3, :3].T @ (joint(last, bone) - (P1[:3, :3] @ PIV[bone] + P1[:3, 3]))
            place = rest + out[parent][:3, :3] @ ((1 - s) * slack0 + s * slack1)
        m = np.eye(4)
        m[:3, :3] = R
        m[:3, 3] = place - R @ PIV[bone]
        out[bone] = m
    return out


def ease(t):
    return t * t * (3 - 2 * t)


def check(name, pose, source):
    origin, head, left, up = body_frame(pose)
    low, lowest = min((joint(pose, b)[2], b) for b, _ in H if b not in ("camera", "weapon", "launcher"))
    fixed = max(np.abs(pose[b] - source[b]).max() for b in ("pelvis", "spine", "spine1", "spine2", "spine3", "neck", "neck1", "head"))
    if fixed > 1e-9:
        raise ValueError("%s moved the trunk or the head" % name)
    if low < 0.015:
        raise ValueError("%s has %s %.3f m over the ground" % (name, lowest, low))
    report = []
    for b in ("leftforearm", "lefthand", "rightforearm", "righthand", "leftleg", "leftfoot", "rightfoot"):
        p = joint(pose, b) - origin
        report.append("%s %.2f %.2f %.2f" % (b, p @ left, p @ head, p @ up))
    print(name, "| joint: to the left, to the head, up |", "; ".join(report))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    names, mats = read_rtm(SOURCE)
    lower = [n.lower() for n in names]
    if sorted(lower) != sorted(b for b, _ in H):
        raise ValueError("The lying pose does not have the bones of the man skeleton")
    source = {b: mats[0, i] for i, b in enumerate(lower)}
    args.output.mkdir(parents=True, exist_ok=True)
    # pose_cross is not built: in the game its hands stood up off the chest (see hand_to).
    for name, make in (("side", pose_side),):
        pose = make(source)
        check(name, pose, source)
        held = np.array([[pose[b] for b in lower]] * 2)
        write_rtm(args.output / f"acme_litter_{name}.rtm", names, held)
        print("   wrote", name)


if __name__ == "__main__":
    main()
