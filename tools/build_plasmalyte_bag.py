"""Plasma-Lyte IV bag textures: addons/acm_extended/data/iv_bag/IVBag_plasmalyte_{250,500,1000}ml_ca.paa (B396).

A Plasma-Lyte bag used to wear ACE's saline texture, whose label reads "0.9% Sodium Chloride Injection USP". These
are ACE's own saline textures (same clear bag, same volume marks, barcode and bag maker) with the drug name and the
composition block re-lettered for Plasma-Lyte A (multiple electrolytes injection, type 1, pH 7.4). The label is
printed sideways on the texture, reading from the bottom up, like ACE's; the boxes below were measured from ACE's
saline textures (all three sizes share the layout).

Run: python tools/build_plasmalyte_bag.py   (reads ACE from the game install, writes the .paa files with HEMTT)
"""
import os
import struct
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

ACE = r"F:\Program Files (x86)\Steam\steamapps\common\Arma 3\!Workshop\@ace\addons\ace_medical_treatment.pbo"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "addons", "acm_extended", "data", "iv_bag")
FONT = r"C:\Windows\Fonts\arial.ttf"
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
INK = (16, 16, 16, 255)
CLEAR = (255, 255, 255, 26)   # the bag film around the print

# [x0, y0, x1, y1] on the 1024 x 1024 texture
TITLE = (262, 645, 330, 898)        # "0.9% Sodium Chloride / Injection USP" (two lines)
NOTE = (331, 612, 359, 717)         # "each 100mL contain / 900 mg Sodium" beside the volume
BLOCK = (359, 616, 610, 800)        # the composition and directions block (the container and maker lines after it stay)
TITLE_LINES = ["PLASMA-LYTE A", "Injection pH 7.4"]
NOTE_LINES = ["each 100 mL contains", "NaCl 526 mg"]
BLOCK_LINES = [
    "Sodium Gluconate 502 mg",
    "Sodium Acetate 368 mg",
    "Potassium Chloride 37 mg",
    "Magnesium Chloride 30 mg",
    "pH 7.4 (6.5 to 8.0)",
    "mEq/L: Na 140  K 5  Mg 3",
    "Cl 98  Acetate 27  Gluconate 23",
    "Osmolarity 294 mOsmol/L (calc)",
    "Multiple Electrolytes Injection",
    "Type 1 USP. Single dose.",
    "Do not use unless clear.",
    "Rx only. Discard unused portion.",
    "Squeeze and inspect inner bag;",
    "discard if leaks are found.",
    "Do not use in series connections.",
    "Store at room temperature",
    "(25 C / 77 F). Avoid excessive heat.",
    "Protect from freezing.",
    "Do not remove from overwrap",
    "until ready to use.",
]


def pbo_file(path, name):
    b = open(path, "rb").read()
    o = 0
    ents = []
    while True:
        e = b.index(b"\0", o)
        n = b[o:e].decode("latin1")
        o = e + 1
        mime, _a, _b, _c, size = struct.unpack_from("<5I", b, o)
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


def letter(img, box, lines, font_path, gap=1.0):
    """Write the lines into the box, reading from the bottom up, first line leftmost (as ACE's print)."""
    x0, y0, x1, y1 = box
    along, across = y1 - y0, x1 - x0
    size = int(across / len(lines) / gap)
    while size > 5:
        font = ImageFont.truetype(font_path, size)
        widest = max(font.getbbox(t)[2] for t in lines)
        if widest <= along - 4:
            break
        size -= 1
    strip = Image.new("RGBA", (along, across), (0, 0, 0, 0))
    d = ImageDraw.Draw(strip)
    step = across / len(lines)
    for i, t in enumerate(lines):
        d.text((2, int(i * step + (step - size) / 2) - 1), t, font=font, fill=INK)
    img.alpha_composite(strip.rotate(90, expand=True), (x0, y0))


def main():
    os.makedirs(OUT, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for vol in (250, 500, 1000):
            src = os.path.join(tmp, f"saline_{vol}.paa")
            open(src, "wb").write(pbo_file(ACE, f"data\\IVBag_saline_{vol}ml_ca.paa"))
            png = os.path.join(tmp, f"saline_{vol}.png")
            subprocess.run(["hemtt", "utils", "paa", "convert", src, png], check=True, capture_output=True)
            img = Image.open(png).convert("RGBA")
            d = ImageDraw.Draw(img)
            for box in (TITLE, NOTE, BLOCK):
                d.rectangle(box, fill=CLEAR)
            letter(img, TITLE, TITLE_LINES, FONT_BOLD, gap=1.15)
            letter(img, NOTE, NOTE_LINES, FONT, gap=1.1)
            letter(img, BLOCK, BLOCK_LINES, FONT, gap=1.05)
            out_png = os.path.join(tmp, f"plasmalyte_{vol}.png")
            img.save(out_png)
            out = os.path.join(OUT, f"IVBag_plasmalyte_{vol}ml_ca.paa")
            if os.path.exists(out):
                os.remove(out)   # (hemtt does not overwrite)
            subprocess.run(["hemtt", "utils", "paa", "convert", out_png, out], check=True, capture_output=True)
            img.save(os.path.join(OUT, f"_preview_{vol}.png")) if os.environ.get("PREVIEW") else None
            print(out)


if __name__ == "__main__":
    main()
