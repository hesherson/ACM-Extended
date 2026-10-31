"""B234 reproducible field layers from the supplied asset archive and B233 sprites.

No newly drawn catheter: both gauges use their existing native 00..14 textures.
The longer source canvas is padded about the hub to a rotation-safe square, not
stretched into a square. Direct-port flush variants omit the baked extension.
"""
from pathlib import Path
import argparse, hashlib, json, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
TARGET=ROOT/'addons/acm_extended/ui/iv/field'
FINISH=TARGET.parent/'finish'

def main():
 p=argparse.ArgumentParser();p.add_argument('--assets',type=Path,required=True);p.add_argument('--hemtt',required=True);p.add_argument('--jobs',type=int,default=4);a=p.parse_args()
 TARGET.mkdir(parents=True,exist_ok=True)
 tmp=Path(tempfile.mkdtemp(prefix='acme-field-'))
 def convert(src,dst):
  subprocess.run([a.hemtt,'utils','paa','convert',str(src),str(dst)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=45)
 def save(name,image):
  out=TARGET/(name+'.paa')
  if out.is_file(): return out
  f=tmp/(name+'.png'); image.save(f);convert(f,out);return out
 def canvas():return Image.new('RGBA',(4096,4096))
 # Field source pixels are preserved spatially; [1006.5,1037] maps to canvas center.
 dx=2048-1006.5;dy=2048-1037
 def layer(comp,pos):
  im=canvas();im.alpha_composite(comp,(round(pos[0]+dx),round(pos[1]+dy)))
  return im.resize((2048,2048),Image.Resampling.LANCZOS)
 lock=Image.open(a.assets/'components/saline_lock.png').convert('RGBA')
 save('lock_ca',layer(lock,(983.5,1027)))
 for f in range(24):
  q=f/23;s=q*q*(3-2*q)
  save(f'lock_{f}_ca',layer(lock,(983.5,1027+50*(1-s))))
 for k,pos in [('lock',(894,854)),('field',(866,854))]:
  comp=Image.open(a.assets/f'components/tegaderm_{k}_overlay.png').convert('RGBA')
  save(f'dressing_{k}_ca',layer(comp,pos))
 icon=Image.new('RGBA',(256,256));tile=lock.copy();tile.thumbnail((196,210),Image.Resampling.LANCZOS)
 # Upscale for an actual visible tool icon, rather than the small placed component.
 tile=lock.resize((151,210),Image.Resampling.LANCZOS);icon.alpha_composite(tile,((256-tile.width)//2,23));save('icon_lock_ca',icon)
 def direct(src):
  out=TARGET/('direct_'+src.name)
  if out.is_file():return out
  decoded=tmp/(src.stem+'_decoded.png');convert(src,decoded)
  image=Image.open(decoded).convert('RGBA');v=np.array(image)
  # B233 extension's alpha ends at row 697 of the 1024 canvas; syringe starts
  # at that connection. All plunger components below this plane are retained.
  v[:698,:,3]=0
  if src.name=='post_flush_secure_0041_ca.paa':v[:,:,3]=0
  return save('direct_'+src.stem,Image.fromarray(v))
 sources=[]
 for seq in ['blood_return_flush','resisted_no_return','post_flush_secure']:
  sources.extend(sorted(FINISH.glob(seq+'_????_ca.paa')))
 with ThreadPoolExecutor(max_workers=a.jobs) as pool:list(pool.map(direct,sources))
 convert(FINISH/'cursor_flush_ca.paa',tmp/'cursor.png')
 save('cursor_flush_ca',Image.open(tmp/'cursor.png').convert('RGBA'))
 files={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(TARGET.glob('*.paa'))}
 manifest={'build':'B234','source':'ACME_Saline_Lock_Field_IV_Base_v1.zip','primary_socket':[1006.5,1037],'secondary_socket':[1006.5,1189],
  'source_canvas':[2048,2304],'padded_source_canvas':[4096,4096],'output_canvas':[2048,2048],'rotation_pivot':[.5,.5],
  'files':files,'notes':'Existing gauge-specific catheter sequence is reused, not pre-rendered into field artwork. Direct flush frames remove the extension only.'}
 (TARGET/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('Built',len(files),'field runtime textures')
if __name__=='__main__':main()
