#!/usr/bin/env python3
"""Build original, simple field mounting trays and a cosmetic cable segment.

These trays are generic ACME props, not replicas of a manufacturer's SmartMount.
Only a visual LOD is needed: mounting is scripted and the props carry no cargo.
"""
from pathlib import Path
import math
import struct

ROOT=Path(__file__).resolve().parents[1]/'addons/acme_equipment/models'

def model(points,faces,path):
    normals=[];outfaces=[]
    for indices in faces:
        a,b,c=(points[i] for i in indices[:3]);u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
        n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];length=math.sqrt(sum(x*x for x in n));assert length>0
        normals.append([x/length for x in n]);outfaces.append(indices)
    b=bytearray(b'MLOD'+struct.pack('<II',257,1)+b'P3DM'+struct.pack('<6I',28,256,len(points),len(normals),len(faces),0))
    for p in points:b+=struct.pack('<3fI',*p,0)
    for n in normals:b+=struct.pack('<3f',*n)
    for normal,indices in enumerate(outfaces):
        b+=struct.pack('<I',len(indices))
        for j in range(4):b+=struct.pack('<IIff',indices[j] if j<len(indices) else 0,normal,0,0)
        b+=struct.pack('<I',0)+b'#(argb,8,8,3)color(0.035,0.04,0.035,1,CO)\0\0'
    b+=b'TAGG'+b'\x01#Property#\0'+struct.pack('<I',128)
    b+=b'autocenter'.ljust(64,b'\0')+b'0'.ljust(64,b'\0')
    b+=b'\x01#EndOfFile#\0'+struct.pack('<I',0)+struct.pack('<f',0)
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)

def tray(width,depth,path):
    points=[];faces=[]
    def box(x0,y0,z0,x1,y1,z1):
        at=len(points);points.extend([(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)])
        faces.extend([[at+i for i in f] for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])
    w=width/2;d=depth/2
    box(-w,-d,0,w,d,.018)
    box(-w,-d,.018,-w+.008,d,.038);box(w-.008,-d,.018,w,d,.038)
    # Rear retaining rail, open front and low side guides leave screen access clear.
    box(-w+.008,d-.008,.018,w-.008,d,.045)
    model(points,faces,path)

def cable(path):
    points=[]
    for y in [-.5,.5]:
        points.extend([(.008*math.cos(i*math.tau/8),y,.008*math.sin(i*math.tau/8)) for i in range(8)])
    faces=[[i,(i+1)%8,(i+1)%8+8,i+8] for i in range(8)]
    points.extend([(0,-.5,0),(0,.5,0)])
    faces.extend([[16,(i+1)%8,i] for i in range(8)])
    faces.extend([[17,8+i,8+(i+1)%8] for i in range(8)])
    model(points,[list(reversed(f)) for f in faces],path)

if __name__=='__main__':
    tray(.40,.30,ROOT/'tempus_pro_mount.p3d');tray(.28,.20,ROOT/'tempus_ls_mount.p3d');cable(ROOT/'monitor_cable.p3d')
