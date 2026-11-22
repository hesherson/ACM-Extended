"""The CPR animations for a casualty who lies higher than the ground the provider kneels on (on the Talon II
litter, whose bed is 0.148 m up): addons/circulation/anim/acme_cpr_{in,loop,loop_l,out}_t.rtm, made from the
ground ones (acme_cpr_{in,loop,loop_l,out}.rtm).

("there needs to be a small adjusted version for doing CPR on the TALON II litter", 2026-11-21.)

The provider kneels more upright: the body above the hips turns back about the line through the hip joints until
the hands are RISE higher. The arms turn back again by ARM_BACK of that at the shoulders, so they still push
mostly down, and the head by HEAD_BACK of it, so the looks stay on the face. The legs do not move (the thighs of
the ground pose are nearly upright already: the hips could rise 2 cm at most). The whole provider is then moved
along so that the hands are where they were over the sternum (fnc_cprSpot.sqf places the provider for the
ground animations). The entry and the exit blend the change in from the kneel and out to it.

Run: python tools/build_cpr_raised.py   (reads and writes addons/circulation/anim)

RTM_0101 as these files have it: per frame and bone a 3x4 matrix, the 3x3 by columns then the translation, taking
the bind pose to the pose (p' = R p + t), model axes with y up and the provider facing -z.
"""
import os
import struct
import sys

import numpy as np

ANIM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "addons", "circulation", "anim")
RISE = 0.148            # acmeLitterBedHeight of the Talon II
ARM_BACK = 0.6          # share of the turn the arms are turned back
HEAD_BACK = 0.5         # share of the turn the head is turned back

LEGS = {"LeftUpLeg", "LeftUpLegRoll", "LeftLeg", "LeftLegRoll", "LeftFoot", "LeftToeBase",
        "RightUpLeg", "RightUpLegRoll", "RightLeg", "RightLegRoll", "RightFoot", "RightToeBase"}
ARMS_PREFIX = ("LeftArm", "LeftForeArm", "LeftHand", "RightArm", "RightForeArm", "RightHand")
ARMS_EXTRA = {"weapon", "launcher"}
HEAD = {"neck", "neck1", "head", "Camera"}


def read(path):
    b = open(path, "rb").read()
    assert b[:8] == b"RTM_0101", path
    disp = struct.unpack_from("<3f", b, 8)
    frames, bones = struct.unpack_from("<ii", b, 20)
    o = 28
    names = []
    for _ in range(bones):
        names.append(b[o:o + 32].split(b"\0")[0].decode())
        o += 32
    times = np.zeros(frames)
    R = np.zeros((frames, bones, 3, 3))
    T = np.zeros((frames, bones, 3))
    for f in range(frames):
        times[f] = struct.unpack_from("<f", b, o)[0]
        o += 4
        for k in range(bones):
            assert b[o:o + 32].split(b"\0")[0].decode() == names[k]
            o += 32
            m = struct.unpack_from("<12f", b, o)
            o += 48
            R[f, k] = np.array(m[:9]).reshape(3, 3).T
            T[f, k] = m[9:12]
    assert o == len(b)
    return dict(disp=disp, names=names, times=times, R=R, T=T)


def write(path, a):
    out = bytearray(b"RTM_0101")
    out += struct.pack("<3f", *a["disp"])
    out += struct.pack("<ii", len(a["times"]), len(a["names"]))
    pad = [n.encode().ljust(32, b"\0") for n in a["names"]]
    for p in pad:
        out += p
    for f in range(len(a["times"])):
        out += struct.pack("<f", a["times"][f])
        for k in range(len(a["names"])):
            out += pad[k]
            out += struct.pack("<12f", *np.concatenate([a["R"][f, k].T.reshape(9), a["T"][f, k]]))
    open(path, "wb").write(bytes(out))


def joint(anims, a, b):
    """The point bones a and b move alike, over all frames (least squares)."""
    A, y = [], []
    for an in anims:
        ia, ib = an["names"].index(a), an["names"].index(b)
        A.append((an["R"][:, ia] - an["R"][:, ib]).reshape(-1, 3))
        y.append((an["T"][:, ib] - an["T"][:, ia]).reshape(-1))
    A, y = np.vstack(A), np.concatenate(y)
    p = np.linalg.lstsq(A, y, rcond=None)[0]
    assert np.sqrt(np.mean((A @ p - y) ** 2)) < 1e-4, (a, b)
    return p


def rot_axis(u, angle):
    """Rotation by angle about the unit axis u (right hand)."""
    u = u / np.linalg.norm(u)
    K = np.array([[0, -u[2], u[1]], [u[2], 0, -u[0]], [-u[1], u[0], 0]])
    return np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * K @ K


class Rig:
    def __init__(self, anims):
        self.hipL = joint(anims, "Pelvis", "LeftUpLeg")
        self.hipR = joint(anims, "Pelvis", "RightUpLeg")
        self.shL = joint(anims, "LeftShoulder", "LeftArm")
        self.shR = joint(anims, "RightShoulder", "RightArm")
        self.neck = joint(anims, "Spine3", "neck")
        self.wristL = joint(anims, "LeftForeArmRoll", "LeftHand")
        self.wristR = joint(anims, "RightForeArmRoll", "RightHand")
        self.kneeL = joint(anims, "LeftUpLeg", "LeftLeg")
        self.kneeR = joint(anims, "RightUpLeg", "RightLeg")

    def at(self, an, f, bone, p):
        k = an["names"].index(bone)
        return an["R"][f, k] @ p + an["T"][f, k]


def change(an, f, rig, turn, shift):
    """Frame f turned by `turn` (radians, hands up) and moved by `shift`; returns new R, T for all bones."""
    names = an["names"]
    hipL, hipR = rig.at(an, f, "LeftUpLeg", rig.hipL), rig.at(an, f, "RightUpLeg", rig.hipR)
    hips = 0.5 * (hipL + hipR)
    u = hipL - hipR                                       # about the line through the hip joints (x in the kneel)
    shoulders = 0.5 * (rig.at(an, f, "LeftArm", rig.shL) + rig.at(an, f, "RightArm", rig.shR))
    neck = rig.at(an, f, "neck", rig.neck)
    G = rot_axis(u, turn)
    g = hips - G @ hips                                   # about the hips
    sh2 = G @ shoulders + g
    A = rot_axis(u, -ARM_BACK * turn)
    a = sh2 - A @ sh2                                     # the arms back about the shoulders, after the turn
    n2 = G @ neck + g
    H = rot_axis(u, -HEAD_BACK * turn)
    h = n2 - H @ n2
    R = an["R"][f].copy()
    T = an["T"][f].copy()
    for k, name in enumerate(names):
        if name in LEGS:
            Rg, tg = np.eye(3), np.zeros(3)
        else:
            Rg, tg = G, g
            if name.startswith(ARMS_PREFIX) or name in ARMS_EXTRA:
                Rg, tg = A @ Rg, A @ tg + a
            elif name in HEAD:
                Rg, tg = H @ Rg, H @ tg + h
        R[k] = Rg @ R[k]
        T[k] = Rg @ T[k] + tg + shift
    return R, T


def hands(an, f, rig, R=None, T=None):
    R = an["R"][f] if R is None else R
    T = an["T"][f] if T is None else T
    kl, kr = an["names"].index("LeftHand"), an["names"].index("RightHand")
    return 0.5 * ((R[kl] @ rig.wristL + T[kl]) + (R[kr] @ rig.wristR + T[kr]))


def solve(an, rig):
    """The turn that puts the hands of frame 0 RISE higher, and the shift that keeps them over the sternum."""
    h0 = hands(an, 0, rig)
    lo, hi = 0.0, 1.2
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        R, T = change(an, 0, rig, mid, np.zeros(3))
        if hands(an, 0, rig, R, T)[1] - h0[1] < RISE:
            lo = mid
        else:
            hi = mid
    R, T = change(an, 0, rig, lo, np.zeros(3))
    h1 = hands(an, 0, rig, R, T)
    shift = np.array([h0[0] - h1[0], 0.0, h0[2] - h1[2]])
    return lo, shift


def turn_onto(a, b):
    """The rotation that turns the direction of a onto that of b."""
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(a @ b)
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3)
    V = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + V + V @ V * (1 / (1 + c))


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def make(src, dst, rig, turn, shift, weight, stroke=False):
    an = read(os.path.join(ANIM, src))
    n = len(an["times"])
    ground = [hands(an, f, rig) for f in range(n)]
    for f in range(n):
        w = weight(f / (n - 1))
        an["R"][f], an["T"][f] = change(an, f, rig, turn * w, shift * w)
    if stroke:
        # The turn turns the stroke too: the hands went down 26 mm instead of 57 and slid 23 mm forward with each
        # compression (measured in game: it looked like twice the rate). The body above the legs is moved so that
        # the hands make the stroke of the ground animation, straight down, at its times.
        # (Spread up the spine: the pelvis stays on the thighs, which cannot stretch, and each joint above takes a
        # quarter of it, under 9 mm, which the blended skin there takes up.)
        share = {"Spine": 0.25, "Spine1": 0.5, "Spine2": 0.75}
        moved = [(k, share.get(name, 1.0)) for k, name in enumerate(an["names"]) if name not in LEGS and name != "Pelvis"]
        raised0 = hands(an, 0, rig)
        for f in range(n):
            fix = (ground[f] - ground[0]) - (hands(an, f, rig) - raised0)
            for k, part in moved:
                an["T"][f, k] += fix * part
            # the hands lag the full fix by the spine's share only where they hang from it: put them right
            rest = (ground[f] - ground[0]) - (hands(an, f, rig) - raised0)
            for k, part in moved:
                an["T"][f, k] += rest * part
    write(os.path.join(ANIM, dst), an)
    return an


def main():
    loop = read(os.path.join(ANIM, "acme_cpr_loop.rtm"))
    anims = [loop, read(os.path.join(ANIM, "acme_cpr_in.rtm")), read(os.path.join(ANIM, "acme_cpr_out.rtm"))]
    rig = Rig(anims)
    turn, shift = solve(loop, rig)
    print("turn %.1f deg, shift %s m" % (np.degrees(turn), shift.round(3)))
    for src, weight, stroke in (("acme_cpr_loop.rtm", lambda x: 1.0, True), ("acme_cpr_loop_l.rtm", lambda x: 1.0, True),
                                ("acme_cpr_in.rtm", lambda x: smooth(x), False), ("acme_cpr_out.rtm", lambda x: smooth(1 - x), False)):
        dst = src.replace(".rtm", "_t.rtm")
        an = make(src, dst, rig, turn, shift, weight, stroke)
        last = len(an["times"]) - 1
        print(dst, "frames", len(an["times"]), "hands first %s last %s" % (hands(an, 0, rig).round(3), hands(an, last, rig).round(3)))
    # what the provider looks like: hands, hips, knees of the loop's first frame, ground and raised
    t = read(os.path.join(ANIM, "acme_cpr_loop_t.rtm"))
    knee = joint(anims, "LeftUpLeg", "LeftLeg")
    for name, an in (("ground", loop), ("raised", t)):
        print(name, "hands", hands(an, 0, rig).round(3), "hips", rig.at(an, 0, "Pelvis", rig.hipL).round(3),
              "shoulders", rig.at(an, 0, "LeftArm", rig.shL).round(3), "left knee", rig.at(an, 0, "LeftLeg", knee).round(3))


if __name__ == "__main__":
    sys.exit(main())
