#!/usr/bin/env python3
"""A casualty who is dragged along the ground by the collar: a limp pose, and the same pose with loose limbs.

The game cannot make a dragged casualty a ragdoll (measured 2026-11-18: a unit that hangs on something never
becomes one, a force does nothing to a unit lying in an animation, and a body moves only in the two seconds of
its own fall). So the limbs are animated instead, which costs nothing on the network and is the same on every
machine:

  acme_drag_rest.rtm   the pose, held: chest and head a little off the ground (he hangs by the collar), the head
                       fallen back and to one side, arms beside the body with the hands on the ground, legs
                       straight and apart with the feet fallen outward
  acme_drag_limp.rtm   the same, one second long and looped: the heels skip and wander, the hands trail and
                       bounce, the head rolls, each limb at its own time

Made from ACM's lying pose with the tools of build_litter_poses.py. The place of the pelvis is unchanged.
(In the game the model's axes are turned half round against this file's: the neck printed here at y -0.45 is at
y +0.52 there. fn_dragLocal.sqf uses the places measured in the game.)

  python tools/build_drag_poses.py [--output <folder>]
"""
import argparse
import math
from pathlib import Path

import numpy as np

import build_litter_poses as L

FRAMES = 16


def pose_drag(source, phase=None):
    """phase None: the held pose. Otherwise the pose at this angle (radians) of the loop."""
    pose = {b: m.copy() for b, m in source.items()}
    origin, head, left, up = L.body_frame(pose)

    def wave(amount, shift=0.0):
        return 0.0 if phase is None else amount * math.sin(phase + shift)

    # the chest and the head, lifted by what he is pulled by
    lift = math.radians(9) + wave(math.radians(0.7), 0.4)
    at = L.joint(pose, "spine1")
    L.swing(pose, "spine1", at, L.turn(head, math.cos(lift) * head + math.sin(lift) * up))
    # the head falls back and to the side, and rolls
    back = math.radians(11)
    roll = math.radians(7) + wave(math.radians(3.5), 2.1)
    at = L.joint(pose, "neck")
    L.swing(pose, "neck", at, L.turn(up, math.cos(back) * up + math.sin(back) * head))
    L.swing(pose, "neck", at, L.turn(up, math.cos(roll) * up + math.sin(roll) * left))
    # the legs: straight, apart, the feet fallen outward; each heel skips and wanders at its own time
    for side, sign, shift in (("left", 1, 0.0), ("right", -1, 2.5)):
        hip = L.joint(pose, side + "upleg")
        length = np.linalg.norm(L.PIV[side + "leg"] - L.PIV[side + "upleg"]) + np.linalg.norm(L.PIV[side + "foot"] - L.PIV[side + "leg"])
        lateral = (hip - origin) @ left
        out = sign * 0.15 + wave(0.03, shift)
        height = 0.07 + abs(wave(0.022, shift + 0.5))
        ankle = origin + head * ((hip - origin) @ head) + left * out + up * height
        ankle = ankle - head * math.sqrt(max((length * 0.995) ** 2 - (out - lateral) ** 2 - (height - hip[2]) ** 2, 0))
        L.limb(pose, side + "upleg", side + "leg", side + "foot", ankle, up)
        # the foot keeps its ankle; the limp leg rolls outward in the hip, and rolls a little as it is dragged
        L.roll_leg(pose, side, sign, left, up, 32 + math.degrees(wave(0.07, shift + 1.0)))
    # the arms: beside the body, a little away from it, the hands trailing on the ground
    for side, sign, shift in (("left", 1, 1.3), ("right", -1, 4.4)):
        wrist = origin + left * (sign * 0.36) + head * (0.02 - wave(0.035, shift)) + up * (0.06 + abs(wave(0.014, shift)))
        L.limb(pose, side + "arm", side + "forearm", side + "hand", wrist, left * sign - up * 0.3)
    return pose


def report(name, pose):
    origin, head, left, up = L.body_frame(pose)
    low, lowest = min((L.joint(pose, b)[2], b) for b, _ in L.H if b not in ("camera", "weapon", "launcher"))
    neck = L.joint(pose, "neck")
    feet = (L.joint(pose, "leftfoot") + L.joint(pose, "rightfoot")) / 2
    print("%s | lowest joint %s %.3f | neck (model x, y, z) %.3f %.3f %.3f | middle of the feet %.3f %.3f %.3f | head joint height %.3f | to the head is %s" % (
        name, lowest, low, *neck, *feet, L.joint(pose, "head")[2], np.round(head, 2)))
    if low < 0.01:
        raise ValueError("%s has %s %.3f m over the ground" % (name, lowest, low))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=L.OUTPUT)
    args = parser.parse_args()
    names, mats = L.read_rtm(L.SOURCE)
    lower = [n.lower() for n in names]
    source = {b: mats[0, i] for i, b in enumerate(lower)}
    args.output.mkdir(parents=True, exist_ok=True)
    rest = pose_drag(source)
    report("rest", rest)
    L.write_rtm(args.output / "acme_drag_rest.rtm", names, np.array([[rest[b] for b in lower]] * 2))
    loop = []
    for k in range(FRAMES):
        pose = pose_drag(source, 2 * math.pi * k / FRAMES)
        if k in (0, 4, 8, 12):
            report("limp %2d" % k, pose)
        loop.append([pose[b] for b in lower])
    loop.append(loop[0])
    L.write_rtm(args.output / "acme_drag_limp.rtm", names, np.array(loop))
    print("wrote acme_drag_rest.rtm and acme_drag_limp.rtm")


if __name__ == "__main__":
    main()
