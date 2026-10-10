"""B255: Direct Pressure ownership transfer and stale reservation regressions."""
from pathlib import Path
from test_menu_death_lifecycle import adapt, execute

ROOT = Path(__file__).resolve().parents[1] / "functions"

def _local():
    owner=(ROOT/"fn_ownerInit.sqf").read_text(encoding="utf-8-sig")
    block=owner.split("// B255 Direct Pressure locality teardown.",1)[1].split("// End B255 DP locality cleanup.",1)[0]
    retire=(ROOT/"fn_directPressureRetire.sqf").read_text(encoding="utf-8-sig")
    return (
        'private _unit=_medic; private _isLocal=true; private _dpEvents=[]; private _removedDP=[];'
        'ACME_fnc_ownerDispatch={_dpEvents pushBack _this;};'
        'CBA_fnc_removePerFrameHandler={_removedDP pushBack ["pfh",_this select 0];};'
        'CBA_fnc_removeKeyHandler={_removedDP pushBack ["key",_this select 0];};'
        'ACME_fnc_directPressureRetire={'+adapt(retire)+'};'
        'private _move={'+adapt(block)+'};'
    )

def test_transfer_gain_releases_exact_active_claim_and_state():
    execute(_local()+r"""
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_Patient",_patient];
        _medic setVariable ["ACME_DP_Part","leftarm"];
        _medic setVariable ["ACME_DP_ClaimToken","old-token"];
        _medic setVariable ["ACME_DP_ClaimEpoch",5];
        call _move;
        [count _dpEvents==1,"missing exact claim release"] call _check;
        private _release=_dpEvents select 0;
        [(_release select 0) isEqualTo _patient && {(_release select 1)=="directPressureClaim"},
            "claim release routed to wrong patient"] call _check;
        [(_release select 2) isEqualTo ["release",[_medic,"leftarm","old-token",5]],
            "wrong claim token/epoch released"] call _check;
        [!(_medic getVariable ["ACME_DP_Active",true]) && {(_medic getVariable ["ACME_DP_ClaimToken",""])==""},
            "incoming owner retained previous active claim"] call _check;
    """)

def test_transfer_loss_releases_claim_without_writing_successor_state():
    execute(_local()+r"""
        _isLocal=false;
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_Patient",_patient];
        _medic setVariable ["ACME_DP_Part","body"];
        _medic setVariable ["ACME_DP_ClaimToken","old"];
        _medic setVariable ["ACME_DP_ClaimEpoch",7];
        _medic setVariable ["ACME_DP_PFH",12];
        _medic setVariable ["ACME_DP_KeyIDs",["key"]];
        _medic setVariable ["ACME_DP_InPose",true];
        _medic setVariable ["ACME_DP_TreatmentBusy",true];
        call _move;
        [count _dpEvents==1,"departed owner left claim behind"] call _check;
        [_medic getVariable ["ACME_DP_Active",false],"former owner mutated successor provider state"] call _check;
        [count _removedDP==2 && {(_medic getVariable ["ACME_DP_PFH",0])==-1},
            "departing input/worker handles not removed"] call _check;
        [!(_medic getVariable ["ACME_DP_InPose",true])
            && {!(_medic getVariable ["ACME_DP_TreatmentBusy",true])},
            "departing machine retained stale stance hints"] call _check;
    """)

def test_pending_claim_cannot_reactivate_after_migration():
    execute(_local()+r"""
        _medic setVariable ["ACME_DP_ClaimPending",[_patient,"rightleg","pending",8]];
        _medic setVariable ["ACME_DP_ClaimRequestedAt",20];
        call _move;
        [count _dpEvents==1 && {((_dpEvents select 0) select 2) isEqualTo ["release",[_medic,"rightleg","pending",8]]},
            "pending owner claim not cancelled"] call _check;
        [(_medic getVariable ["ACME_DP_ClaimPending",[0]]) isEqualTo []
            && {(_medic getVariable ["ACME_DP_ClaimRequestedAt",0])==-1},
            "pending provider state survived"] call _check;
    """)

def test_claimless_transfer_never_cancels_foreign_hold():
    execute(_local()+r"""
        _medic setVariable ["ACME_DP_Patient",_patient];
        _medic setVariable ["ACME_DP_Part","head"];
        _medic setVariable ["ACME_DP_ClaimToken",""];
        call _move;
        [count _dpEvents==0,"claimless transfer emitted release"] call _check;
    """)

def _stale():
    s=(ROOT/"fn_directPressureClaimLocal.sqf").read_text(encoding="utf-8-sig")
    block=s.split("// A dead/disconnected/stale holder never blocks the next provider.",1)[1].split("private _reason =",1)[0]
    return (
        'private _part="leftarm"; private _claimKey="ACME_DP_claim_leftarm";'
        'private _pressKey="ACME_DP_press_leftarm";'
        'private _claim=[_medic,"old",4,7,100];'
        'private _currentMedic=_medic; private _currentToken="old";'
        'private _currentValid=false; private _bleedUpdates=0;'
        'ace_medical_status_fnc_updateWoundBloodLoss={_bleedUpdates=_bleedUpdates+1;};'
        '_patient setVariable [_claimKey,_claim];'
        '_patient setVariable [_pressKey,_medic];'
        '_patient setVariable ["ACME_DP_LimbMedic",_medic];'
        'private _repair={'+adapt(block)+'};'
    )

def test_stale_claim_retirement_recalculates_limb_bleeding_and_clears_markers():
    execute(_stale()+r"""
        call _repair;
        [(_patient getVariable [_claimKey,[1]]) isEqualTo [],"old claim retained"] call _check;
        [(_patient getVariable [_pressKey,missionNamespace]) isEqualTo objNull,"old site still pressured"] call _check;
        [(_patient getVariable ["ACME_DP_LimbMedic",missionNamespace]) isEqualTo objNull,"generic marker retained"] call _check;
        [_bleedUpdates==1,"blood loss not recomputed"] call _check;
    """)

def test_stale_cleanup_preserves_other_medics_marker():
    execute(_stale()+r"""
        _patient setVariable ["ACME_DP_LimbMedic",missionNamespace];
        call _repair;
        [(_patient getVariable ["ACME_DP_LimbMedic",objNull]) isEqualTo missionNamespace,
            "removed different medic's marker"] call _check;
    """)

def test_active_claim_not_incorrectly_retired():
    execute(_stale()+r"""
        _currentValid=true;
        call _repair;
        [(_patient getVariable [_pressKey,objNull]) isEqualTo _medic
            && {(_patient getVariable ["ACME_DP_LimbMedic",objNull]) isEqualTo _medic},
            "active pressure cleared"] call _check;
        [_bleedUpdates==0,"active pressure caused bleeding recomputation"] call _check;
    """)

def test_body_part_clear_replicates_on_regular_and_server_stop():
    stop=(ROOT/"fn_directPressureStop.sqf").read_text(encoding="utf-8-sig")
    server=(ROOT/"fn_initPressureAndAuscultationConfig.sqf").read_text(encoding="utf-8-sig")
    assert '["ACME_DP_Part", "", true]' in stop
    assert '_unit setVariable ["ACME_DP_Part", "", true];' in server
