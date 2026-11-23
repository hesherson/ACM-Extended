"""Validate the texture build and preserve native models, UVs, materials and UI."""
from pathlib import Path
import hashlib
import shutil
import importlib.util
import os
import struct
import subprocess
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
import pytest
from build_tempus_panel_art import ROOT, SOURCE, TARGETS, NS, tags, layout, document

BASELINE='530b716ff4c7d41dd0de47a7a5c0907f0317c9f3'


def mip_sizes(data):
    at=2
    while data[at:at+4]==b'GGAT':at+=12+struct.unpack_from('<I',data,at+8)[0]
    palette=struct.unpack_from('<H',data,at)[0];at+=2+palette*3
    sizes=[]
    while True:
        w,h=struct.unpack_from('<HH',data,at);at+=4
        if w==0 and h==0:break
        size=int.from_bytes(data[at:at+3],'little');at+=3
        assert size>0 and at+size<=len(data)
        sizes.append((w&32767,h));at+=size
    return sizes


@pytest.mark.parametrize('kind',['pro','ls'])
def test_runtime_atlas_is_opaque_dxt1_4k_with_complete_square_mips(kind):
    data=(ROOT/'addons'/TARGETS[kind]).read_bytes()
    assert data[:2]==b'\x01\xff'
    assert mip_sizes(data)==[(4096>>i,4096>>i) for i in range(11)]
    assert tags(data)['CGVA'][1]==tags((SOURCE/(kind+'_base.paa')).read_bytes())['CGVA'][1]


@pytest.mark.parametrize('kind',['pro','ls'])
def test_original_base_texture_is_exact_b310_asset(kind):
    relative='addons/'+TARGETS[kind]
    original=subprocess.check_output(['git','show',BASELINE+':'+relative],cwd=ROOT)
    assert original==(SOURCE/(kind+'_base.paa')).read_bytes()


@pytest.mark.parametrize('kind',['pro','ls'])
def test_vector_source_has_self_contained_paths_and_clipped_uv_regions(kind):
    root=ET.parse(SOURCE/(kind+'_labels.svg')).getroot()
    assert root.attrib['viewBox']=='0 0 4096 2048'
    assert not any(e.tag.split('}')[-1] in ('image','script','text','foreignObject','filter') for e in root.iter())
    assert not any(k.startswith('on') or 'href' in k for e in root.iter() for k in e.attrib)
    groups=root.findall('{'+NS+'}g');assert len(groups)==len(layout(kind))
    for group in groups:
        box=[float(v) for v in group.attrib['data-uv-box'].split(',')]
        clip=group.find('.//{'+NS+'}clipPath/{'+NS+'}rect')
        assert [float(clip.attrib[k]) for k in ('x','y','width','height')]==box
        assert group.find('{'+NS+'}g').attrib['clip-path']=='url(#clip-'+group.attrib['id']+')'


@pytest.mark.parametrize('kind',['pro','ls'])
def test_svg_background_embedding_preserves_full_atlas_and_uv_aspect(kind):
    root=ET.fromstring(document(kind,b'png-for-contract'))
    assert root.attrib['width']==root.attrib['height']=='4096'
    assert root.attrib['viewBox']=='0 0 4096 2048' and root.attrib['preserveAspectRatio']=='none'
    background=root.find('{'+NS+'}image')
    assert background.attrib['{http://www.w3.org/1999/xlink}href'].startswith('data:image/png;base64,')
    assert background.attrib['width']=='4096' and background.attrib['height']=='2048'


@pytest.mark.parametrize('addon',['acme_tempus','acme_tempusls'])
def test_models_all_auxiliary_maps_materials_and_monitor_functions_are_unchanged(addon):
    # The B311 art job must not touch models, UV maps or materials; those stay exactly as at B310. Monitor
    # functions/config/HTML have since been developed on purpose (later batches), so they are no longer pinned,
    # and text files are compared without checkout line endings (core.autocrlf).
    checked=0
    for path in (ROOT/'addons'/addon).rglob('*'):
        if not path.is_file() or path.name in ('tempus_co.paa','tempusls_co.paa'):continue
        if path.suffix.lower() not in ('.p3d','.paa','.rvmat','.rtm'):continue
        relative=path.relative_to(ROOT).as_posix()
        original=subprocess.check_output(['git','show',BASELINE+':'+relative],cwd=ROOT)
        current=path.read_bytes()
        if path.suffix.lower()=='.rvmat':
            current,original=current.replace(b'\r\n',b'\n'),original.replace(b'\r\n',b'\n')
        assert current==original,relative
        checked+=1
    assert checked


@pytest.mark.parametrize('kind',['pro','ls'])
def test_rendered_changes_are_confined_to_declared_print_regions(kind):
    evidence=Path(os.environ.get('ACME_PANEL_EVIDENCE',ROOT.parent/'b311_art_evidence'))
    if not (evidence/(kind+'-after.png')).exists():
        pytest.skip('environment: no render evidence; run build_tempus_panel_art.py --evidence for this visual gate')
    before=np.array(Image.open(evidence/(kind+'-before.png')).convert('RGBA'))
    after=np.array(Image.open(evidence/(kind+'-after.png')).convert('RGBA'))
    assert before.shape==after.shape==(4096,4096,4)
    assert before[:,:,3].min()==after[:,:,3].min()==255,'Missing atlas background or unintended transparency'
    # A missing background in both renders must also fail, independently of differences.
    assert before[:,:,:3].mean()>12 and (before[:,:,:3]>80).sum()>10000
    allowed=np.zeros((4096,4096),dtype=bool)
    for x,y,w,h in layout(kind):
        allowed[int(y*2):int((y+h)*2),int(x):int(x+w)]=True
    changed=np.any(before!=after,axis=2)
    assert changed.sum()>1000
    assert not changed[~allowed].any(),'Artwork spilled into a different UV island'
    assert np.array_equal(before[:,:,3],after[:,:,3])


@pytest.mark.parametrize('kind',['pro','ls'])
def test_native_paa_roundtrip_keeps_non_printed_body_and_opaque_background(kind,tmp_path):
    hemtt=os.environ.get('HEMTT') or shutil.which('hemtt')  # HEMTT env var, else hemtt on PATH
    if not hemtt:
        pytest.skip('environment: set HEMTT to the native converter for this texture gate')
    evidence=Path(os.environ.get('ACME_PANEL_EVIDENCE',ROOT.parent/'b311_art_evidence'))
    if not (evidence/(kind+'-after.png')).exists():
        pytest.skip('environment: no render evidence; run build_tempus_panel_art.py --evidence for this texture gate')
    out=tmp_path/'decoded.png'
    subprocess.run([hemtt,'utils','paa','convert',str(ROOT/'addons'/TARGETS[kind]),str(out)],check=True,capture_output=True)
    encoded=np.array(Image.open(out).convert('RGBA'))
    raster=np.array(Image.open(evidence/(kind+'-after.png')).convert('RGBA'))
    assert encoded.shape==raster.shape==(4096,4096,4)
    assert encoded[:,:,3].min()==255
    delta=np.abs(encoded[:,:,:3].astype(np.int16)-raster[:,:,:3].astype(np.int16))
    assert delta.mean()<3.5 and np.quantile(delta,.99)<18,'Unexpected compression/colour damage'
