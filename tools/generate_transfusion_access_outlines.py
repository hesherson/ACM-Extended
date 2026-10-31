#!/usr/bin/env python3
"""Derive thin selection contours from original IV/IO alpha masks; never alter medical artwork."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageChops, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'addons/acm_extended/ui/transfusion/access'

def contour(image):
    alpha=image.convert('RGBA').getchannel('A').point(lambda x:255 if x>=32 else 0)
    ring=ImageChops.subtract(alpha.filter(ImageFilter.MaxFilter(5)),alpha)
    result=Image.new('RGBA',image.size,(255,255,255,0));result.putalpha(ring)
    return result

def sources():
    text=(ROOT/'addons/acm_extended/functions/fn_skSiteGeometry.sqf').read_text()
    for key,*_ in json.loads(text[text.index('[\n'):]):
        key=key.lower()
        if key.endswith('_ej'): source=ROOT/f'addons/acm_extended/ui/iv/iv_ej_{key.split("_")[0]}_ca.paa'
        else:
            name='torso_fast_io' if key=='body_io' else key if key.endswith('_io') else key.replace('_','_iv_',1)
            source=ROOT/f'addons/gui/data/body_image/{name}.paa'
        yield key,source

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--hemtt',required=True);args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);assets=[]
    with tempfile.TemporaryDirectory(prefix='acme-access-outline-') as temporary:
        temp=Path(temporary)
        for key,source in sources():
            decoded=temp/(key+'.png');png=temp/(key+'_outline.png');paa=OUT/(key+'_ca.paa')
            subprocess.run([args.hemtt,'utils','paa','convert',str(source),str(decoded),'--no-color'],check=True,capture_output=True)
            image=Image.open(decoded).convert('RGBA').resize((512,512),Image.Resampling.LANCZOS);contour(image).save(png)
            subprocess.run([args.hemtt,'utils','paa','convert',str(png),str(paa),'--no-color'],check=True,capture_output=True)
            assets.append({'key':key,'source':source.relative_to(ROOT).as_posix(),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'file':paa.name,'sha256':hashlib.sha256(paa.read_bytes()).hexdigest(),'size':list(image.size)})
    (OUT/'manifest.json').write_text(json.dumps({'alphaThreshold':32,'radiusPixels':2,'assets':assets},indent=2)+'\n')
    print(f'Generated {len(assets)} alpha-only access contours')

if __name__=='__main__':main()
