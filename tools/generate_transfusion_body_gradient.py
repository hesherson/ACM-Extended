#!/usr/bin/env python3
"""Draw the native transfusion body-map backdrop; its transparent edge preserves native map geometry."""
from pathlib import Path
import argparse
import subprocess
import tempfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

def render():
    image = Image.new('RGBA', (256, 512))
    pixels = image.load()
    for y in range(512):
        for x in range(256):
            # Gentle charcoal halo under the body; no patient artwork or interaction surfaces change.
            radius = ((x - 127.5) / 120) ** 2 + ((y - 255.5) / 245) ** 2
            opacity = round(190 * max(0, 1 - radius) ** 1.5)
            pixels[x, y] = (30, 32, 36, opacity)
    return image

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hemtt', required=True)
    args = parser.parse_args()
    output = ROOT / 'addons/acm_extended/ui/transfusion/body_gradient_ca.paa'
    with tempfile.TemporaryDirectory(prefix='acme-body-gradient-') as folder:
        png = Path(folder) / 'body-gradient.png'
        render().save(png)
        subprocess.run([args.hemtt,'utils','paa','convert','--no-color',str(png),str(output)],check=True)
    print(output)

if __name__ == '__main__':
    main()
