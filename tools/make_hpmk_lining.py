"""The HPMK-I shell's lining: addons/acme_hpmk/data/hpmk_in_co.paa, hpmk_in_nohq.paa, hpmk_in_smdi.paa.

The lining is a blue fleece ("the inside is a fuzzy blue", asked for on 2026-11-20 with photographs of the kit).
The picture it had was one flat blue (every pixel within 2 of the mean) over a map of cloth creases: in the game
a sheet of plastic. Here it is drawn as a nap: short fibres lying every way, brushed a little along the bag,
with the slow cloudiness and the pills a fleece has, and a relief of the same fibres. Dull: almost no shine.
It repeats every 0.40 m (1024 pixels: 0.4 mm each), without a seam.

  python tools/make_hpmk_lining.py            (writes the three pictures; needs Arma 3 Tools' ImageToPAA)
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "addons/acme_hpmk/data"
SIZE = 1024
BLUE = np.array([57.0, 115.0, 184.0])        # the mean stays what it was: how light it shows in the game follows it
TO_PAA = Path(r"F:\Program Files (x86)\Steam\steamapps\common\Arma 3 Tools\ImageToPAA\ImageToPAA.exe")


def blur(g, s):
    """Smoothed, going round at the edges (so that the picture repeats without a seam)."""
    f = np.fft.fftfreq(SIZE)
    k = np.exp(-2 * (np.pi * s) ** 2 * (f[:, None] ** 2 + f[None, :] ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(g) * k))


def fibres(rng, count, lengths, lean):
    """Short fibres as a height: each a line of a few pixels, most of them near the direction 'lean' is along."""
    g = np.zeros((SIZE, SIZE))
    ang = np.where(rng.random(count) < lean, rng.normal(np.pi / 2, 0.45, count), rng.uniform(0, np.pi, count))
    ln = rng.uniform(lengths[0], lengths[1], count)
    x0, y0 = rng.uniform(0, SIZE, count), rng.uniform(0, SIZE, count)
    amp = rng.normal(0.0, 1.0, count)
    bend = rng.normal(0.0, 0.015, count)
    for t in np.linspace(-0.5, 0.5, int(lengths[1] * 1.3)):
        a = ang + bend * t * ln
        xs = (x0 + np.cos(a) * t * ln).astype(int) % SIZE
        ys = (y0 + np.sin(a) * t * ln).astype(int) % SIZE
        np.add.at(g, (ys, xs), amp * (1 - (2 * t) ** 2))
    return g


def main():
    rng = np.random.default_rng(20261120)
    nap = blur(fibres(rng, 150000, (7, 26), 0.45), 0.55)
    fine = blur(fibres(rng, 260000, (3, 9), 0.2), 0.45)
    nap = nap / nap.std() * 0.75 + fine / fine.std() * 0.5
    cloud = blur(rng.normal(size=(SIZE, SIZE)), 38.0)
    cloud = cloud / cloud.std()
    patch = blur(rng.normal(size=(SIZE, SIZE)), 9.0)
    patch = patch / patch.std()
    # pills: little knots of fibre, lighter, a few to the hand's breadth
    pills = np.zeros((SIZE, SIZE))
    for _ in range(420):
        x, y, r = rng.uniform(0, SIZE), rng.uniform(0, SIZE), rng.uniform(1.2, 3.2)
        yy, xx = np.ogrid[:SIZE, :SIZE]
        dx = np.minimum(np.abs(xx - x), SIZE - np.abs(xx - x))
        dy = np.minimum(np.abs(yy - y), SIZE - np.abs(yy - y))
        pills += np.exp(-(dx ** 2 + dy ** 2) / (2 * r * r))
    height = nap + 0.35 * patch + 1.6 * pills
    height = height / height.std()

    shade = 1.0 + 0.085 * nap / nap.std() + 0.035 * cloud + 0.03 * patch + 0.10 * np.clip(pills, 0, 1)
    co = BLUE[None, None, :] * shade[:, :, None]
    # (the fibres' tips are a little paler and less blue, their roots deeper: what makes a nap look soft)
    tip = np.clip(nap / nap.std(), -2, 2)[:, :, None] * np.array([3.0, 2.0, -1.0])[None, None, :]
    co = co + tip
    co = co * (BLUE / co.reshape(-1, 3).mean(axis=0))[None, None, :]
    co = np.clip(co, 0, 255).astype(np.uint8)

    gx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5
    gy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5
    k = 0.55
    n = np.stack([-gx * k, gy * k, np.ones_like(gx)], axis=2)
    n /= np.linalg.norm(n, axis=2)[:, :, None]
    nohq = np.clip((n * 0.5 + 0.5) * 255, 0, 255).astype(np.uint8)

    # (red full, green how strongly it shines, blue how sharply: a fleece does neither, a little more on its pills)
    smdi = np.zeros((SIZE, SIZE, 3), np.uint8)
    smdi[:, :, 0] = 255
    smdi[:, :, 1] = np.clip(22 + 5 * nap / nap.std(), 8, 48)
    smdi[:, :, 2] = np.clip(34 + 6 * patch, 16, 60)

    work = Path(tempfile.mkdtemp(prefix="hpmk_lining_"))
    for name, picture in (("hpmk_in_co", co), ("hpmk_in_nohq", nohq), ("hpmk_in_smdi", smdi)):
        png = work / (name + ".png")
        Image.fromarray(picture).save(png)
        if "--png" in sys.argv:
            print("wrote", png)
            continue
        paa = OUT / (name + ".paa")
        done = subprocess.run([str(TO_PAA), str(png), str(paa)], capture_output=True, text=True)
        print("wrote", paa, "(%d bytes)" % paa.stat().st_size, done.stdout.strip().splitlines()[-1:] if done.stdout.strip() else "")
    print("mean colour", co.reshape(-1, 3).mean(axis=0).round(1), "spread", co.reshape(-1, 3).std(axis=0).round(1))
    if "--png" in sys.argv:
        print(work)


if __name__ == "__main__":
    main()
