"""Native HEMTT model parser gates for the original field trays/cosmetic cable."""
import json
import math
import os
from pathlib import Path
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name,points,faces',[
    ('tempus_pro_mount',32,24),('tempus_ls_mount',32,24),('monitor_cable',18,24)
])
def test_native_parser_geometry_is_finite_small_closed_and_has_correct_outward_normals(name,points,faces,tmp_path):
    hemtt=os.environ.get('HEMTT');assert hemtt,'HEMTT executable required for native geometry validation'
    path=ROOT/'addons/acme_equipment/models'/(name+'.p3d');out=tmp_path/'mesh.json'
    subprocess.run([hemtt,'utils','p3d','json',str(path),str(out)],check=True,capture_output=True)
    d=json.loads(out.read_text());assert d['version']==257 and len(d['lods'])==1
    lod=d['lods'][0];assert lod['resolution']==0 and len(lod['points'])==points and len(lod['faces'])==faces
    coords=[v['coords'] for v in lod['points']]
    assert all(math.isfinite(v) for row in coords for v in row)
    tags=dict(lod['taggs']);raw=bytes(tags['#Property#']);assert raw[:64].split(b'\0')[0]==b'autocenter' and raw[64:].split(b'\0')[0]==b'0'
    edges={}
    for index,face in enumerate(lod['faces']):
        vertices=[v['point_index'] for v in face['vertices']]
        assert len(vertices) in (3,4) and len(set(vertices))==len(vertices)
        for a,b in zip(vertices,vertices[1:]+vertices[:1]):
            edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
        normal=lod['face_normals'][face['vertices'][0]['normal_index']]
        center=[sum(coords[i][axis] for i in vertices)/len(vertices) for axis in range(3)]
        if name!='monitor_cable':
            group=coords[(index//6)*8:(index//6+1)*8]
            origin=[sum(v[axis] for v in group)/8 for axis in range(3)]
        else:origin=[0,0,0]
        assert sum(normal[i]*(center[i]-origin[i]) for i in range(3))>0,'inverted surface normal'
        assert face['texture'].startswith('#(') and face['material']=='', 'unexpected asset dependency'
    assert set(edges.values())=={2},'open/nonmanifold primitive'
