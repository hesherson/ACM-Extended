"""Execute observer visual lifecycle with native object/rope creation simulated."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[3]


def execute(scenario):
    vm = os.environ.get('SQFVM') or shutil.which('sqfvm')
    if not vm:
        pytest.skip('SQF-VM required')
    s = (ROOT / 'addons/acm_extended/functions/fn_hangBagVisualSync.sqf').read_text()
    replacements = {
        '!isNull objectParent _medic': '_vehicle',
        'isNull _medic': '_nullMedic',
        'isNull _patient': '_nullPatient',
        'local _medic': '_local',
        'owner _medic': '_testOwner',
        'alive _medic': '_alive',
        'hasInterface': '_interface',
        'createSimpleObject [_bagModel, [0,0,0], true]': '([_bagModel] call _create)',
        '_anchorClass createVehicleLocal [0, 0, 0]': '([_anchorClass] call _create)',
        '_bag setObjectTexture [0, _bagTexture];': '_texture = _bagTexture;',
        '_bag attachTo [_medic, _handOffset, _handSel, true];': '_hand = [_handOffset, _handSel];',
    }
    for a,b in replacements.items():
        s = s.replace(a,b)
    s = re.sub(r'\bisNull (_\w+)', r'(\1 isEqualTo objNull)', s)
    s = re.sub(r'\b_\w+ (?:allowDamage|hideObject|attachTo|disableCollisionWith) [^;]+;', '0;', s)
    s = re.sub(r'\bdetach _\w+;', '0;', s)
    s = re.sub(r'\bdeleteVehicle (_\w+);', r'_deleted pushBack \1;', s)
    code=r'''
        private _ok = true;
        private _medic = uiNamespace;
        private _patient = profileNamespace;
        private _interface = true;
        private _local = false;
        private _testOwner = 7;
        private _alive = true;
        private _vehicle = false;
        private _nullMedic = false;
        private _nullPatient = false;
        private _created = [];
        private _deleted = [];
        private _destroyedRopes = [];
        private _handlers = [];
        private _waits = [];
        private _ropeArgs = [];
        private _texture = "";
        private _hand = [];
        private _rotations = [];
        private _create = {_created pushBack (_this select 0); count _created};
        private _data = [_patient, "bag_model.p3d", "blood_500.paa", [1,2,3], "RightHand", [4,5,6],
            "ace_fastroping_helper", [7,8,9], [10,11,12], [0,0.04,0.06], [0,0,0.12], "ACME_IVLine_Rope_Blood", 3, 24, true];
        _medic setVariable ["ACME_hang_VisualEpisode", [1, true]];
        CBA_fnc_addPerFrameHandler = {_handlers pushBack [_this select 0, _this select 2, true]; count _handlers - 1};
        CBA_fnc_removePerFrameHandler = {(_handlers select (_this select 0)) set [2, false];};
        CBA_fnc_waitUntilAndExecute = {_waits pushBack _this;};
        BIS_fnc_setObjectRotation = {_rotations pushBack _this;};
        ACME_fnc_ivLineCreate = {_ropeArgs = _this; ["rope"] call _create};
        ACME_fnc_ivLineDestroy = {_destroyedRopes pushBack (_this select 0);};
        private _tick = {
            params [["_id", 0]];
            private _h = _handlers select _id;
            if (_h select 2) then {[_h select 1, _id] call (_h select 0);};
        };
        private _show = {[_medic, 1, "show", _data, 7] call ACME_fnc_hangBagVisualSync;};
        private _hide = {[_medic, 1, "hide"] call ACME_fnc_hangBagVisualSync;};
        private _check = {if !(_this select 0) then {_ok = false; diag_log ("BAG_FIX_FAIL " + (_this select 1));};};
        ACME_fnc_hangBagVisualSync = {''' + s + '};\n' + scenario + r'''
        diag_log (if (_ok) then {"BAG_FIX_OK"} else {"BAG_FIX_FAIL"});
    '''
    result=subprocess.run([vm,'--automated','--suppress-welcome','--no-execute-print','--no-work-print','--sqf',code],capture_output=True,text=True,timeout=15)
    output=result.stdout+result.stderr
    assert result.returncode==0 and '[ERR]' not in output and '[FAT]' not in output,output
    assert 'BAG_FIX_OK' in output and 'BAG_FIX_FAIL' not in output,output


def test_observer_creates_matching_bag_and_custom_line_only_once():
    execute('''
        call _show; call _show;
        [count _created == 4 && {count _handlers == 1}, "missing or duplicate objects"] call _check;
        [_texture == "blood_500.paa" && {_hand isEqualTo [[1,2,3], "RightHand"]}, "bag presentation mismatch"] call _check;
        [(_ropeArgs select 6) == "ACME_IVLine_Rope_Blood", "rope class mismatch"] call _check;
    ''')


@pytest.mark.parametrize('context',['_local = true;','_interface = false;'])
def test_holder_and_dedicated_server_do_not_create_duplicate_replicas(context):
    execute(context+' call _show; [count _created == 0, "unwanted replica"] call _check;')


def test_props_remain_through_lowering_then_hide_rejects_late_show():
    execute('''
        call _show;
        _medic setVariable ["ACME_hang_Active", false];
        [] call _tick;
        [count _deleted == 0, "props removed before lowering finished"] call _check;
        call _hide; call _show;
        [count _deleted == 3 && {count _destroyedRopes == 1} && {count _created == 4}, "hide/late show cleanup failed"] call _check;
    ''')


def test_old_hide_cannot_delete_new_hold():
    execute('''
        call _show;
        _medic setVariable ["ACME_hang_VisualEpisode", [2, true]];
        [_medic, 2, "show", _data, 7] call ACME_fnc_hangBagVisualSync;
        call _hide;
        [count _created == 8 && {count _deleted == 3} && {(_handlers select 1) select 2}, "old hide removed new props"] call _check;
    ''')


def test_joining_observer_waits_for_episode_before_creating_props():
    execute('''
        _medic setVariable ["ACME_hang_VisualEpisode", [-1, false]];
        call _show;
        [count _created == 0 && {count _waits == 1}, "JIP did not wait"] call _check;
        _medic setVariable ["ACME_hang_VisualEpisode", [1, true]];
        private _wait = _waits select 0;
        (_wait select 2) call (_wait select 1);
        [count _created == 4, "JIP did not create props"] call _check;
    ''')


def test_release_wins_over_pending_jip_show():
    execute('''
        _medic setVariable ["ACME_hang_VisualEpisode", [-1, false]];
        call _show; call _hide;
        _medic setVariable ["ACME_hang_VisualEpisode", [1, true]];
        private _wait = _waits select 0;
        (_wait select 2) call (_wait select 1);
        [count _created == 0, "late JIP recreated ended props"] call _check;
    ''')


@pytest.mark.parametrize('end',['_alive = false;','_testOwner = 8;','_vehicle = true;','_nullPatient = true;','_nullMedic = true;'])
def test_abandoned_or_deleted_session_destroys_all_local_objects(end):
    execute('call _show; '+end+'''
        [] call _tick;
        [count _deleted == 3 && {count _destroyedRopes == 1}, "orphaned props"] call _check;
        [!((_handlers select 0) select 2), "orphaned handler"] call _check;
    ''')
