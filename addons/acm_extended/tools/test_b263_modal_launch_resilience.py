"""B263 modal handoff, ownership, legacy alias and cleanup contracts."""
from pathlib import Path
from test_menu_death_lifecycle import adapt, execute

ROOT = Path(__file__).resolve().parents[3]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8-sig")

def test_pfh_retirement_executes_both_owners_once():
    s = read("addons/gui/functions/fnc_pauseMedicalMenuPFH.sqf")
    execute(r"""
        private _removedIds = [];
        CBA_fnc_removePerFrameHandler = {_removedIds pushBack (_this select 0);};
        private _pause = {
    """ + adapt(s) + r"""
        };
        missionNamespace setVariable ["ace_medical_gui_menuPFH", 16];
        uiNamespace setVariable ["ACME_medicalMenuRendererPFH", 22];
        [call _pause, "active menu PFHs could not be paused"] call _check;
        [_removedIds isEqualTo [22, 16], "did not retire native and custom renderers"] call _check;
        [(missionNamespace getVariable ["ace_medical_gui_menuPFH", -2]) == -1
            && {(uiNamespace getVariable ["ACME_medicalMenuRendererPFH", -2]) == -1},
            "PFH handle survived pause"] call _check;
        [!(call _pause) && {count _removedIds == 2}, "repeat pause touched another PFH"] call _check;
        _removedIds = [];
        missionNamespace setVariable ["ace_medical_gui_menuPFH", 9];
        uiNamespace setVariable ["ACME_medicalMenuRendererPFH", 9];
        [call _pause && {_removedIds isEqualTo [9]}, "shared PFH ID removed twice"] call _check;
    """)

def test_legacy_actions_execute_canonical_alias_in_sqfvm():
    s = read("addons/core/overrides/fnc_treatment.sqf")
    begin = s.index('params ["_medic", "_patient", "_bodyPart", "_classname"];')
    end = s.index("// An explicit successor click", begin)
    block = s[begin:end].replace('if (isNull _patient) then {"null"} else {netId _patient}', '"patient"')
    execute(r"""
        private _oldSeal=[_medic,_patient,"Body","ApplyChestSeal"];
        _oldSeal call {
    """ + adapt(block) + r"""
        };
        [(_oldSeal select 3) == "ACME_ApplyChestSeal", "old seal action was not canonicalized"] call _check;
        private _oldThora=[_medic,_patient,"Body","PerformThoracostomy"];
        _oldThora call {
    """ + adapt(block) + r"""
        };
        [(_oldThora select 3) == "ACME_PerformThoracostomy", "old thora action was not canonicalized"] call _check;
        private _normal=[_medic,_patient,"Body","CheckPulse"];
        _normal call {
    """ + adapt(block) + r"""
        };
        [(_normal select 3) == "CheckPulse", "unrelated ACE action intercepted"] call _check;
    """)

def test_chest_entry_pause_precedes_menu_close_and_ack_wait_is_bounded():
    s = read("addons/acm_extended/functions/fn_chestSealOpen.sqf")
    close = read("addons/acm_extended/functions/fn_chestSealClose.sqf")
    assert s.index("call ACM_GUI_fnc_pauseMedicalMenuPFH;") < s.index("_oldMedicalMenu closeDisplay 1;")
    assert s.index("_oldMedicalMenu closeDisplay 1;") < s.index('uiNamespace setVariable ["ACME_CS_SessionToken", _sessionToken];')
    assert "CBA_missionTime + 30, CBA_missionTime + 3, 0" in s
    assert "if (CBA_missionTime >= _deadline) exitWith {" in s
    assert 'if (!_member && {CBA_missionTime >= _nextRetry} && {_retryCount < 4}) then {' in s
    assert '[_p, "chestSealPatientBegin", [_p, _tok, _m]] call ACME_fnc_ownerDispatch;' in s
    assert "if (owner _p != _patientOwner) exitWith {" in s
    assert "[] call ACME_fnc_chestSealClose;" in s
    assert 'ACME_CS_EntryPFH' in close
    begin = read("addons/acm_extended/functions/fn_chestSealPatientBegin.sqf")
    # Same-owner retries remain idempotent. A fresh invocation on the new
    # owner may resume unfinished preparation while retaining its shared token.
    assert 'if (_token in _tokens && {!_resumePreparation}) exitWith {};' in begin
    assert '(_patient getVariable ["ACME_CS_ProcedureReadyAt", -1]) < 0' in begin
    assert '(_previousPreparationOwner param [2, _preparationOwner select 2]) == (_preparationOwner select 2)' in begin
    assert '(_patient getVariable ["ACME_CS_PreparationOwner", []]) isNotEqualTo _preparationOwner' in begin
    assert 'private _prep = if (_resumePreparation) then {_patient getVariable ["ACME_CS_PreparationToken", _token]} else {_token};' in begin
    # Both first admission and a resumed owner capture authority once. Delayed
    # acquire/retry continuations must carry those original epochs and token.
    authority = 'private _authority = [_patient getVariable ["ACME_equipmentKitEpoch", 0],\n    _patient getVariable ["ACME_providerLocalityEpoch", 0], "", _prep];'
    assert authority in begin
    assert begin.index(authority) < begin.index('call ACME_fnc_chestAccessVestAcquire;')
    assert '[_patient, _medic, "chestseal", false, "", "", _authority] call ACME_fnc_chestAccessVestAcquire;' in begin
    assert '[_p, _medic, "chestseal", false, "", "", _authority] call ACME_fnc_chestAccessVestAcquire;' in begin
    assert '[_patient,_preSide,_preGrounded,_prep,_medic,_authority]] call CBA_fnc_waitUntilAndExecute;' in begin

def test_thora_failure_cleanup_and_stale_unload_guard():
    s=read("addons/acm_extended/functions/fn_thoraOpen.sqf")
    c=read("addons/acm_extended/functions/fn_thoraClose.sqf")
    cfg=read("addons/acm_extended/config.cpp")
    assert s.index("call ACM_GUI_fnc_pauseMedicalMenuPFH;") < s.index("_menuDisplay closeDisplay 1;")
    assert 'if ((uiNamespace getVariable ["ACME_Thora_ChestAccessLease", ""]) != _lease) exitWith {};' in s
    assert s.count("[] call ACME_fnc_thoraClose;") >= 2
    assert "0.6] call CBA_fnc_waitAndExecute;" in s
    assert "_releaseLease, _abort], 20" in s
    assert 'onUnload = "_this call ACME_fnc_thoraClose";' in cfg
    assert 'if (_this isNotEqualTo [] && {_closing isNotEqualTo' in c
    assert 'ACME_Thora_DLG' in c and 'ACM_GUI_fnc_resumeMedicalMenuPFH' in c

def test_external_override_and_modal_ai_path_are_diagnosable():
    route=read("addons/core/overrides/fnc_treatment.sqf")
    ai=read("addons/core/overrides/fnc_playTreatmentAnim.sqf")
    compat=read("addons/acm_extended/functions/fn_compatCheck.sqf")
    assert "ACME-B263-modal-route" in route and "ACME-B263-modal-route" in compat
    assert 'ace_medical_treatment_fnc_treatment' in compat
    assert '[ACME MODAL B263] launch denied' in route and 'ACME_fnc_netNotice' in route
    assert '"ApplyChestSeal", "PerformThoracostomy"' in ai
    assert ai.index("if (_actionName in [") < ai.index("private _anim = getText")


def test_delayed_chest_begin_cannot_resurrect_closed_patient_workspace():
    begin=read("addons/acm_extended/functions/fn_chestSealPatientBegin.sqf")
    end=read("addons/acm_extended/functions/fn_chestSealPatientEnd.sqf")
    assert 'ACME_CS_ClosedTokens' in begin and 'ACME_CS_ClosedTokens' in end
    assert begin.index('ACME_CS_ClosedTokens') < begin.index('private _tokens')
    assert end.index('ACME_CS_ClosedTokens') < end.index('private _tokens')
    assert "serverTime + 180" in end
    assert 'if ((count _retired) > 64)' in end
    assert '_patient setVariable ["ACME_CS_ClosedTokens", _retired, true];' in end
    assert '(_x param [1, 0]) > serverTime' in begin
