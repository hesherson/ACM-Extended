"""Positive and negative controls for historical owner-route source contracts."""
from pathlib import Path
import shutil
import pytest
from owner_route_contract import ROOT, assert_owner_route

ROUTES = [
 ('fn_discardYTubing.sqf','discardYTubing','discardYTubingCommit'),
 ('fn_transfusionPullBag.sqf','transfusionPull','transfusionPullCommit'),
 ('fn_hangPreparedSet.sqf','preparedHang','preparedHangCommit'),
 ('fn_transfusionSpikeOrAdd.sqf','yRefill','yRefillCommit'),
 ('fn_transfusionSpikeOrAdd.sqf','rehangUsedBag','rehangUsedBagCommit'),
 ('fn_updateTransfusionControls.sqf','yEnsureSlots','yEnsureSlots'),
]

@pytest.mark.parametrize('request_path,operation,handler',ROUTES)
def test_registered_owner_route_reaches_authoritative_writer(request_path,operation,handler):
    assert_owner_route(request_path,operation,handler,'ivBagsCommit')

@pytest.mark.parametrize('fault',['frontend_dispatch','frontend_operation','dispatch_case','dispatch_handler',
 'locality_guard','writer_call','registration','commented_writer','commented_case'])
def test_missing_route_or_writer_is_rejected(tmp_path,fault):
    req,op,handler=ROUTES[0]
    relative=Path('addons/acm_extended/functions')
    paths=[relative/req,relative/'fn_ownerDispatch.sqf',relative/f'fn_{handler}.sqf',Path('addons/acm_extended/config.cpp')]
    for path in paths:
        dest=tmp_path/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,dest)
    if fault=='frontend_dispatch':target=paths[0];old='call ACME_fnc_ownerDispatch';new='call obsolete_dispatch'
    elif fault=='frontend_operation':target=paths[0];old='"discardYTubing"';new='"unhandled"'
    elif fault=='dispatch_case':target=paths[1];old='case "discardYTubing"';new='case "unhandled"'
    elif fault=='dispatch_handler':target=paths[1];old='call ACME_fnc_discardYTubingCommit';new='call unrelated_handler'
    elif fault=='locality_guard':target=paths[1];old='!local _patient';new='false'
    elif fault=='writer_call':target=paths[2];old='call ACME_fnc_ivBagsCommit';new='call unrelated_writer'
    elif fault=='registration':target=paths[3];old='class discardYTubingCommit {};';new=''
    elif fault=='commented_writer':target=paths[2];old='call ACME_fnc_ivBagsCommit';new='/* call ACME_fnc_ivBagsCommit */ call unrelated_writer'
    else:target=paths[1];old='case "discardYTubing"';new='/* case "discardYTubing" */ case "unhandled"'
    dest=tmp_path/target;text=dest.read_text();assert old in text;dest.write_text(text.replace(old,new))
    with pytest.raises(AssertionError):assert_owner_route(req,op,handler,'ivBagsCommit',tmp_path)
