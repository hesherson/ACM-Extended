"""The Hang Bag arm gestures: addons/acm_extended/animations/acme_hangbag_arm_{in,hold,out}.rtm (B395).

("take the exact animation of hanging a bag and keep the arm placement exactly the same for when it goes up and
down, but i want to be able to stand and crouch and move my head", 2026-11-23.)

The old hold played the game's crew-aid crouch (Acts_Jets_crewaidF_crouch_thumbup_in / _loop / _out) as a full-body
move. These files keep only its right arm: every frame, each arm bone (upper arm to finger tips) is turned exactly
as in that animation, measured in the man's own axes (so relative to the way he faces), and the arm is moved as a
whole so that its shoulder joint sits where the provider's own shoulder is. A gesture's arm follows the torso it is
played on, so each stance has its own set, made against that stance's idle torso (the game's
AmovPercMstpSnonWnonDnon, and AmovPknlMstpSnonWnonDnon for the _k files): the torso bones carry that idle pose, the
arm bones the target. On a provider standing or crouching (walking too: the torso hardly differs) the arm then points
where it pointed in the crouch hold. The gesture mask (CfgGesturesMale >> BlendAnims >> ACME_HangBagArm) applies
only the arm. (Playing the crouch hold's own arm turns on another torso pointed the arm forward instead of up, and
so did composing it against a torso at rest: both measured in game in B395.)

Source: the game's binarized RTMs (BMTR v5) in Jets\\Addons\\anims_f_jets.pbo. Their bones' turns are relative to
the parent bone; the chain is composed with the man skeleton's parents below. Our RTM_0101 files use the same
model space turned half round the vertical (x and z negated), measured against our own CPR RTMs.

Run: python tools/build_hangbag_arm_gesture.py   (reads the game install, writes addons/acm_extended/animations)
"""
import os
import struct
import sys

import numpy as np

GAME = r"F:\Program Files (x86)\Steam\steamapps\common\Arma 3"
PBO = os.path.join(GAME, "Jets", "Addons", "anims_f_jets.pbo")
SRC = "anim\\Acts_Jets_crewaidF_crouch_thumbup_%s.rtm"
IDLE_PBO = os.path.join(GAME, "Addons", "anims_f_data.pbo")
IDLE = {"": "Anim\\sdr\\mov\\erc\\stp\\non\\non\\AmovPercMstpSnonWnonDnon.rtm",
        "_k": "Anim\\sdr\\mov\\knl\\stp\\non\\non\\AmovPknlMstpSnonWnonDnon.rtm"}
# The crew-aid hold is a thumbs-up. "pose the thumb so it's not sticking out. pose it where it would normally be"
# (2026-11-23): the thumb takes its joint turns from the rifle grip (AmovPercMstpSrasWrflDnon), wrapped round with
# the curled fingers.
GRIP = "Anim\\sdr\\mov\\erc\\stp\\ras\\rfl\\AmovPercMstpSrasWrflDnon.rtm"
THUMB = ["righthandthumb1", "righthandthumb2", "righthandthumb3"]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "addons", "acm_extended", "animations")
NAMES_FROM = os.path.join(HERE, "..", "addons", "circulation", "anim", "acme_cpr_loop.rtm")

PARENT = {
    "rightshoulder": "spine3", "rightarm": "rightshoulder", "rightarmroll": "rightarm",
    "rightforearm": "rightarmroll", "rightforearmroll": "rightforearm", "righthand": "rightforearmroll",
    "righthandring": "righthand",
    "righthandring1": "righthandring", "righthandring2": "righthandring1", "righthandring3": "righthandring2",
    "righthandpinky1": "righthandring", "righthandpinky2": "righthandpinky1", "righthandpinky3": "righthandpinky2",
    "righthandmiddle1": "righthand", "righthandmiddle2": "righthandmiddle1", "righthandmiddle3": "righthandmiddle2",
    "righthandindex1": "righthand", "righthandindex2": "righthandindex1", "righthandindex3": "righthandindex2",
    "righthandthumb1": "righthand", "righthandthumb2": "righthandthumb1", "righthandthumb3": "righthandthumb2",
    "spine3": "spine2", "spine2": "spine1", "spine1": "spine", "spine": "pelvis", "pelvis": None,
}
ARM = [b for b in PARENT if b.startswith("right") and b != "rightshoulder"]
TORSO = ["pelvis", "spine", "spine1", "spine2", "spine3", "rightshoulder"]
FLIP = np.diag([-1.0, 1.0, -1.0])


def pbo_file(path, name):
    b = open(path, "rb").read()
    o = 0
    ents = []
    while True:
        e = b.index(b"\0", o)
        n = b[o:e].decode("latin1")
        o = e + 1
        mime, _orig, _res, _ts, size = struct.unpack_from("<5I", b, o)
        o += 20
        if n == "" and mime == 0x56657273:
            while True:
                e = b.index(b"\0", o)
                k = b[o:e]
                o = e + 1
                if k == b"":
                    break
                o = b.index(b"\0", o) + 1
            continue
        if n == "":
            break
        ents.append((n, size))
    for n, size in ents:
        if n.lower() == name.lower():
            return b[o:o + size]
        o += size
    raise KeyError(name)


def lzo1x(src, ip, out_len):
    dst = bytearray()
    state = 0

    def lit(n):
        nonlocal ip
        dst.extend(src[ip:ip + n])
        ip += n

    def copy(dist, n):
        p = len(dst) - dist
        assert p >= 0
        for i in range(n):
            dst.append(dst[p + i])

    if src[ip] > 17:
        t = src[ip] - 17
        ip += 1
        lit(t)
        state = 4 if t >= 4 else t
    while True:
        t = src[ip]
        ip += 1
        if t < 16:
            if state == 0:
                if t == 0:
                    while src[ip] == 0:
                        t += 255
                        ip += 1
                    t += 15 + src[ip]
                    ip += 1
                lit(t + 3)
                state = 4
                continue
            if state != 4:
                nxt = t & 3
                d = 1 + (t >> 2) + (src[ip] << 2)
                ip += 1
                copy(d, 2)
                lit(nxt)
                state = nxt
                continue
            nxt = t & 3
            d = 1 + 0x800 + (t >> 2) + (src[ip] << 2)
            ip += 1
            n = 3
        elif t >= 64:
            nxt = t & 3
            d = 1 + ((t >> 2) & 7) + (src[ip] << 3)
            ip += 1
            n = (t >> 5) + 1
        elif t >= 32:
            n = (t & 31) + 2
            if n == 2:
                while src[ip] == 0:
                    n += 255
                    ip += 1
                n += 31 + src[ip]
                ip += 1
            v = src[ip] | (src[ip + 1] << 8)
            ip += 2
            d = 1 + (v >> 2)
            nxt = v & 3
        else:
            hi = (t & 8) << 11
            n = (t & 7) + 2
            if n == 2:
                while src[ip] == 0:
                    n += 255
                    ip += 1
                n += 7 + src[ip]
                ip += 1
            v = src[ip] | (src[ip + 1] << 8)
            ip += 2
            d = hi + (v >> 2)
            nxt = v & 3
            if d == 0:
                break
            d += 0x4000
        copy(d, max(n, 3))
        lit(nxt)
        state = nxt
    assert len(dst) == out_len
    return bytes(dst), ip


def carray(b, o, elem):
    n = struct.unpack_from("<I", b, o)[0]
    o += 4
    flag = b[o]
    o += 1
    if flag == 0:
        return n, b[o:o + n * elem], o + n * elem
    assert flag == 2, flag
    data, o = lzo1x(b, o, n * elem)
    return n, data, o


def quat(q):
    # stored x, y, z, w (/16384); the bone turn is the conjugate's matrix
    x, y, z, w = -q[0], -q[1], -q[2], q[3]
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def read_bmtr(b):
    assert b[:4] == b"BMTR" and struct.unpack_from("<I", b, 4)[0] == 5
    o = 9 + 12
    nf, _u, nb, _nb2 = struct.unpack_from("<4I", b, o)
    o += 16
    names = []
    for _ in range(nb):
        e = b.index(b"\0", o)
        names.append(b[o:e].decode().lower())
        o = e + 1
    o += 8
    _n, data, o = carray(b, o, 4)
    phases = list(np.frombuffer(data, "<f4"))
    frames = []
    for _ in range(nf):
        _n, data, o = carray(b, o, 14)
        fr = {}
        for k in range(nb):
            q = np.array(struct.unpack_from("<4h", data, k * 14)) / 16384.0
            t = np.frombuffer(data[k * 14 + 8:k * 14 + 14], "<f2").astype(float)
            fr[names[k]] = (quat(q), t)
        frames.append(fr)
    assert o == len(b)
    return phases, frames


def glob(fr, bone):
    chain = []
    while bone is not None:
        chain.append(bone)
        bone = PARENT[bone]
    R = np.eye(3)
    t = np.zeros(3)
    for b in reversed(chain):
        Rl, tl = fr[b]
        t = R @ tl + t
        R = R @ Rl
    return R, t


def pivot(frames, bone):
    """The bind point a bone turns about (its own local turn leaves it in place), least squares over frames."""
    A = np.vstack([np.eye(3) - fr[bone][0] for fr in frames])
    B = np.concatenate([fr[bone][1] for fr in frames])
    return np.linalg.lstsq(A, B, rcond=None)[0]


def rtm_names():
    b = open(NAMES_FROM, "rb").read()
    assert b[:8] == b"RTM_0101"
    bones = struct.unpack_from("<i", b, 24)[0]
    return [b[28 + 32 * i:60 + 32 * i].split(b"\0")[0].decode() for i in range(bones)]


def write_rtm(path, names, times, poses):
    out = bytearray(b"RTM_0101")
    out += struct.pack("<3f", 0, 0, 0)
    out += struct.pack("<ii", len(times), len(names))
    pad = [n.encode().ljust(32, b"\0") for n in names]
    for p in pad:
        out += p
    for f, t in enumerate(times):
        out += struct.pack("<f", t)
        for k, n in enumerate(names):
            R, T = poses[f].get(n.lower(), (np.eye(3), np.zeros(3)))
            R = FLIP @ R @ FLIP
            T = FLIP @ T
            out += pad[k]
            out += struct.pack("<12f", *np.concatenate([R.T.reshape(9), T]))
    open(path, "wb").write(bytes(out))


def main():
    anims = {k: read_bmtr(pbo_file(PBO, SRC % k)) for k in ("in", "loop", "out")}
    every = [fr for _, frames in anims.values() for fr in frames]
    shoulder = pivot(every, "rightarm")
    names = rtm_names()
    grip = read_bmtr(pbo_file(IDLE_PBO, GRIP))[1][0]
    for _, frames in anims.values():
        for fr in frames:
            for b in THUMB:
                fr[b] = grip[b]
    for suffix, idle_file in IDLE.items():
        idle = read_bmtr(pbo_file(IDLE_PBO, idle_file))[1][0]
        torso = {b: glob(idle, b) for b in TORSO}
        Ri, ti = torso["rightshoulder"]
        target = Ri @ shoulder + ti   # where this stance's idle puts the shoulder joint
        for key, out, take in (("in", "acme_hangbag_arm_in%s.rtm", None), ("loop", "acme_hangbag_arm_hold%s.rtm", 1),
                               ("out", "acme_hangbag_arm_out%s.rtm", None)):
            phases, frames = anims[key]
            if take:
                frames = [frames[0], frames[0]]
                phases = [0.0, 1.0]
            poses = []
            for fr in frames:
                Rs, ts = glob(fr, "rightshoulder")
                delta = target - (Rs @ shoulder + ts)   # carry the shoulder joint to this stance's shoulder
                pose = dict(torso)
                for b in ARM:
                    R, t = glob(fr, b)
                    pose[b] = (R, t + delta)
                poses.append(pose)
            write_rtm(os.path.join(OUT, out % suffix), names, phases, poses)
            wrist = poses[0]["righthand"][0] @ np.array([0.587, 0.065, -0.074]) + poses[0]["righthand"][1]
            print(out % suffix, len(frames), "frames; first-frame wrist", np.round(wrist, 3), "shoulder", np.round(target, 3))


if __name__ == "__main__":
    sys.exit(main())
