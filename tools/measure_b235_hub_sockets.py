#!/usr/bin/env python3
"""Reproduce B235 seated-hub calibration from native 16g PAA artwork.

Uses HEMTT to decode the exact shipped texture. It does not synthesize, repaint,
rotate or replace catheter art. The four-pixel inset gives the male fitting an
under-collar overlap. This is an offline calibration, not a native Arma test.
Run: python tools/measure_b235_hub_sockets.py --hemtt hemtt --verify
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'tools/b235-hub-sockets.json'

def measure(path: Path, suffix: str, executable: str, scratch: Path) -> dict:
    png=scratch/((suffix or 'base')+'.png')
    subprocess.run([executable,'utils','paa','convert',str(path),str(png)],check=True,stdout=subprocess.DEVNULL)
    with Image.open(png) as image:
        if image.size!=(2048,2048):
            raise ValueError(f'Unexpected source canvas: {path}: {image.size}')
        alpha=np.asarray(image.convert('RGBA'))[:,:,3]
    y,x=np.nonzero(alpha>140)
    if len(x)<20:raise ValueError(f'Insufficient opaque artwork: {path}')
    points=np.column_stack((x,y));center=points.mean(axis=0)
    _,vectors=np.linalg.eigh(np.cov(points.T));axis=vectors[:,-1]
    if axis[1]*(1 if suffix.startswith('_ej') else -1)<0:axis=-axis
    projection=(points-center)@axis
    mouth=points[projection<projection.min()+3].mean(axis=0)
    socket=mouth+axis*4
    return {'suffix':suffix,'source':path.relative_to(ROOT).as_posix(),
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'axis':axis.round(8).tolist(),
        'socket_px':socket.round(3).tolist(),'mouth_px':mouth.round(3).tolist(),
        'socket_uv':(socket/2048).round(8).tolist(),
        'angle_deg':float(np.degrees(np.arctan2(axis[0],-axis[1])))}

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hemtt',default='hemtt');parser.add_argument('--verify',action='store_true')
    args=parser.parse_args();data=json.loads(MANIFEST.read_text())
    with tempfile.TemporaryDirectory(prefix='acme-hub-') as tmp:
        results=[measure(ROOT/d['source'],d['suffix'],args.hemtt,Path(tmp)) for d in data['families']]
    if args.verify:
        if results!=data['families']:raise SystemExit('Hub calibration differs from the recorded source; review before changing runtime maps.')
        print('B235 hub calibration: all five texture families reproduced exactly.')
    else:print(json.dumps(results,indent=2))

if __name__=='__main__':main()
