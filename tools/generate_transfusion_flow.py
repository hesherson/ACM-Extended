"""Code-drawn, seamless white flow stripes shared by native and React progress bars."""
from pathlib import Path
import argparse,subprocess
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def render():
    image=Image.new('RGBA',(1024,8))
    image.putdata([(255,255,255,255) if (x+2*y)%32<16 else (180,180,180,255) for y in range(8) for x in range(1024)])
    return image
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--hemtt',required=True);a=p.parse_args()
    png=ROOT/'frontend/medical-ui/assets/flow-stripes.png';render().save(png)
    paa=ROOT/'addons/acm_extended/ui/transfusion/flow_stripes.paa'
    subprocess.run([a.hemtt,'utils','paa','convert',str(png),str(paa)],check=True)
