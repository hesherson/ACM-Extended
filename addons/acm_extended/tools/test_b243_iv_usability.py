"""B243 IV finishing usability contracts."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
FUN=ROOT/"addons"/"acm_extended"/"functions"
def read(name): return (FUN/f"fn_{name}.sqf").read_text(encoding="utf-8-sig")
def test_click_capture_is_larger_than_hard_snap_but_smaller_than_attraction_field():
    t=read("ivFinishTarget"); m=read("ivMagnetGeometry")
    assert "if (_close) then {0.018} else {0.052}" in t
    assert "private _near=_bodyH*0.004;private _far=_bodyH*0.052;" in m
def test_field_click_retains_selected_14_or_16_gauge():
    c=read("ivMinigameClick")
    assert 'private _g=uiNamespace getVariable ["ACME_IV_Gauge",16];' in c
    assert "if (_g in [14,16])" in c and 'format ["field%1",_g]' in c
def test_switching_large_bore_needles_keeps_selected_gauge():
    g=read("ivMinigameGrabNeedle")
    assert g.index('uiNamespace getVariable ["ACME_IV_Gauge",16]) == _gauge') < g.index('private _grabMedic =') < g.index('uiNamespace setVariable ["ACME_IV_Gauge", _gauge];')
def test_both_field_gauges_have_owner_supply_and_commit_paths():
    a=read("ivFinishStart"); b=read("ivFinishCommit"); c=read("ivSupplyScopeCheck")
    for action,item in (("field14","ACM_IV_14g"),("field16","ACM_IV_16g")):
        assert action in a and item in a and action in b and item in b and action in c and item in c
def test_extension_seats_twenty_authored_pixels_deeper():
    assert '["_socketV",1032/2048]' in read("ivFinishPose")
    assert "1052/2048" in read("ivFinishTick") and "1052/2048" in read("ivFieldRender")
    assert "_y+334.52" in read("ivFieldPort") and "1386.52-1052" in read("ivFieldAccessoryRow")
    assert "private _deepOrigin=[1006.5/2048,1052/2048];" in read("ivFinishTarget")
