#!/usr/bin/env python3
"""Bake exact UV-space vector marks into the supplied Tempus colour atlases.

Developer-only asset build; ordinary HEMTT deployment uses the committed PAAs.
Requires Inkscape and HEMTT. No font, network, model conversion or image AI is
involved in this deterministic vector/texture build.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tools/assets/tempus_panels'
TARGETS = {'pro': 'acme_tempus/data/tempus_co.paa', 'ls': 'acme_tempusls/data/tempusls_co.paa'}
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')


def tags(data: bytes) -> dict[str, tuple[int, bytes]]:
    at = 2
    result = {}
    while data[at:at+4] == b'GGAT':
        name = data[at+4:at+8].decode('ascii')
        size = struct.unpack_from('<I', data, at+8)[0]
        result[name] = (at+12, data[at+12:at+12+size])
        at += 12+size
    return result


def keep_average(original: bytes, encoded: bytes) -> bytes:
    """Retain the original material's average-colour metadata (four bytes).

    HEMTT recomputes this tag on conversion. Preserving the author-supplied tag
    avoids an unrelated whole-material ambient/average-colour change.
    """
    before = tags(original); after = tags(encoded)
    assert len(before['CGVA'][1]) == len(after['CGVA'][1]) == 4
    out = bytearray(encoded)
    at = after['CGVA'][0]; out[at:at+4] = before['CGVA'][1]
    return bytes(out)


def layout(kind: str) -> list[list[float]]:
    svg = ET.parse(SOURCE / (kind+'_labels.svg')).getroot()
    boxes = []
    for g in svg.findall('{'+NS+'}g'):
        box = [float(x) for x in g.attrib['data-uv-box'].split(',')]
        x,y,w,h = box
        assert 0 <= x < x+w <= 4096 and 0 <= y < y+h <= 2048
        boxes.append(box)
    assert boxes
    return boxes


def document(kind: str, png: bytes, marks: bool = True) -> bytes:
    # Preserve normalized UV locations. Doubling the vertical texel count does
    # not change the model's texture aspect: its unchanged normalized UVs still
    # map the same source artwork to the same surfaces.
    svg = ET.Element('{'+NS+'}svg', dict(width='4096', height='4096',
        viewBox='0 0 4096 2048', preserveAspectRatio='none'))
    image = ET.SubElement(svg, '{'+NS+'}image', dict(x='0',y='0',width='4096',height='2048',preserveAspectRatio='none'))
    image.set('{http://www.w3.org/1999/xlink}href','data:image/png;base64,'+base64.b64encode(png).decode('ascii'))
    if marks:
        overlay = ET.parse(SOURCE / (kind+'_labels.svg')).getroot()
        for child in overlay:
            if child.tag in ('{'+NS+'}g','{'+NS+'}defs'):
                svg.append(child)
    return ET.tostring(svg, encoding='utf-8', xml_declaration=True)


def run(args: list[str]) -> None:
    subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def bake(kind: str, hemtt: str, inkscape: str, target: Path, evidence: Path | None) -> dict:
    original = SOURCE / (kind+'_base.paa')
    with tempfile.TemporaryDirectory(prefix='acme-panel-') as scratch:
        temp = Path(scratch); base = temp/'base.png'
        run([hemtt,'utils','paa','convert',str(original),str(base),'--no-color'])
        svg = temp/'panel.svg'; svg.write_bytes(document(kind,base.read_bytes()))
        png = temp/'panel.png'
        run([inkscape,str(svg),'--export-type=png','--export-filename='+str(png)])
        target.parent.mkdir(parents=True,exist_ok=True)
        encoded = temp/'panel_co.paa'
        run([hemtt,'utils','paa','convert',str(png),str(encoded),'--no-color','-t','2'])
        target.write_bytes(keep_average(original.read_bytes(),encoded.read_bytes()))
        if evidence:
            evidence.mkdir(parents=True,exist_ok=True)
            (evidence/(kind+'-after.png')).write_bytes(png.read_bytes())
            # A control render without vector changes makes UV-region isolation
            # verifiable independently of DXT recompression.
            svg.write_bytes(document(kind,base.read_bytes(),False))
            run([inkscape,str(svg),'--export-type=png','--export-filename='+str(evidence/(kind+'-before.png'))])
    return dict(device=kind,width=4096,height=4096,source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),uv_edit_boxes=layout(kind),average_tag=list(tags(target.read_bytes())['CGVA'][1]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hemtt',default='hemtt')
    parser.add_argument('--inkscape',default='inkscape')
    parser.add_argument('--output',type=Path,help='Optional output directory; default replaces the two runtime colour PAAs only.')
    parser.add_argument('--evidence',type=Path)
    args = parser.parse_args()
    results = []
    for kind,relative in TARGETS.items():
        target = args.output/(kind+'_co.paa') if args.output else ROOT/'addons'/relative
        results.append(bake(kind,args.hemtt,args.inkscape,target,args.evidence))
    if args.evidence:
        (args.evidence/'panel-build.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__ == '__main__':
    main()
