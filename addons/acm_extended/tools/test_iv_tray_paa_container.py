"""Validate the PAA index used by texture loaders, then decode through HEMTT.

Sequential DXT decoding alone missed B153's absent OFFS table and blank icons.
The integration check runs when HEMTT is on PATH or HEMTT_BINARY is supplied.
"""
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess

from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = sorted((ROOT / "ui/iv/tray").glob("*.paa"))
HEMTT = os.environ.get("HEMTT_BINARY") or shutil.which("hemtt")


@pytest.mark.parametrize("path", ASSETS, ids=lambda path: path.name)
def test_paa_has_standard_metadata_and_exact_mipmap_index(path):
    raw = path.read_bytes()
    assert struct.unpack_from("<H", raw)[0] == 0xFF05
    cursor = 2
    tags = {}
    while raw[cursor:cursor + 4] == b"GGAT":
        name = raw[cursor + 4:cursor + 8]
        length = struct.unpack_from("<I", raw, cursor + 8)[0]
        assert name not in tags
        tags[name] = raw[cursor + 12:cursor + 12 + length]
        cursor += 12 + length
    assert list(tags) == [b"CGVA", b"CXAM", b"GALF", b"SFFO"]
    assert len(tags[b"CGVA"]) == len(tags[b"CXAM"]) == len(tags[b"GALF"]) == 4
    assert tags[b"GALF"][0] == 1
    assert len(tags[b"SFFO"]) == 64
    offsets = struct.unpack("<16I", tags[b"SFFO"])
    assert struct.unpack_from("<H", raw, cursor)[0] == 0  # no palette
    cursor += 2
    for index, size in enumerate((512, 256, 128, 64, 32, 16, 8, 4)):
        assert offsets[index] == cursor
        stored_width, height = struct.unpack_from("<HH", raw, cursor)
        assert (stored_width & 0x7FFF, height) == (size, size)
        length = int.from_bytes(raw[cursor + 4:cursor + 7], "little")
        assert 0 < length <= size * size
        assert cursor + 7 + length <= len(raw)
        cursor += 7 + length
    assert offsets[8:] == (0,) * 8
    assert raw[cursor:] == bytes(6)


@pytest.mark.skipif(not HEMTT, reason="Set HEMTT_BINARY to run independent PAA-loader checks")
@pytest.mark.parametrize("path", ASSETS, ids=lambda path: path.name)
def test_hemtt_loader_finds_every_mip_and_decodes_visible_pixels(path, tmp_path):
    def run(*args):
        return subprocess.run(
            [HEMTT, "utils", "paa", *map(str, args)],
            capture_output=True, text=True, check=True,
        ).stdout

    inspection = run("inspect", path)
    assert re.search(r"Maps:\s+8\b", inspection)
    assert "Format: DXT5" in inspection
    decoded = tmp_path / "decoded.png"
    run("convert", path, decoded)
    with Image.open(decoded) as image:
        assert image.size == (512, 512)
        alpha = image.convert("RGBA").getchannel("A")
        histogram = alpha.histogram()
        assert sum(histogram[128:]) > 4_000
        assert sum(histogram[:1]) > 200_000
        bounds = alpha.point(lambda a: 255 if a > 127 else 0).getbbox()
        assert bounds is not None
        x0, y0, x1, y1 = bounds
        assert 1 < x0 < x1 < 511 and 1 < y0 < y1 < 511
        assert x1 - x0 > 400


def test_all_twenty_expected_assets_are_present():
    assert {path.name for path in ASSETS} == {
        f"iv_tray_{gauge}g_{pose}_ca.paa"
        for gauge in (14, 16, 18, 20) for pose in range(5)
    }
