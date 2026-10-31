params ["_medic", "_patient", ["_bodyPart", ""], ["_startTool", "seal"]];
if (isNull _patient || {isNull _medic} || {!local _medic} || {!alive _medic}
    || {_medic getVariable ["ACE_isUnconscious", false]}) exitWith {};

if !(missionNamespace getVariable ["ACME_sys_chestSeal", true]) exitWith {
    private _item = ["ACM_ChestSeal", "ACME_NARSPEAR"] select (_startTool == "spear");
    private _receipt = [_medic, _patient, [_item]] call ACME_fnc_treatmentSupplyTake;
    if (_receipt isEqualTo []) exitWith {};
    [_receipt, false] call ACME_fnc_treatmentSupplyRefund;
    if (_startTool == "spear") then {
        [_medic, _patient] call ACM_breathing_fnc_performNCD;
    } else {
        [_medic, _patient] call ACM_breathing_fnc_applyChestSeal;
    };
};

if (!isNull (uiNamespace getVariable ["ACME_CS_DLG", displayNull])
    || {(uiNamespace getVariable ["ACME_CS_SessionToken", ""]) != ""}) exitWith {};

// B263: acquire modal UI ownership BEFORE the old ACE menu is closed. The
// stock PFH and our independent renderer can otherwise run closeDialog 0 on
// this procedure's first frame. Repeated pause is safe; onLoad also pauses.
ace_medical_gui_pendingReopen = false;
call ACM_GUI_fnc_pauseMedicalMenuPFH;
private _oldMedicalMenu = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
private _sourceMedicalEpoch = uiNamespace getVariable ["ACME_medicalMenuRendererEpoch", 0];
if (!isNull _oldMedicalMenu) then {_oldMedicalMenu closeDisplay 1;};
if (dialog) then {closeDialog 0;};
uiNamespace setVariable ["ACME_CS_Medic", _medic];
uiNamespace setVariable ["ACME_CS_Patient", _patient];
uiNamespace setVariable ["ACME_CS_PatientKitEpoch", _patient getVariable ["ACME_equipmentKitEpoch", 0]];
uiNamespace setVariable ["ACME_CS_BodyPart", _bodyPart];
uiNamespace setVariable ["ACME_CS_StartTool", _startTool];

// The minigame owns one temporary casualty workspace. The patient owner lowers Semi-Fowler once, moves any worn
// plate carrier beyond the head, and acknowledges when that workspace is ready. During the minigame only the normal
// front/back roll states are allowed to move the casualty.
private _serial = (uiNamespace getVariable ["ACME_CS_SessionSerial", 0]) + 1;
uiNamespace setVariable ["ACME_CS_SessionSerial", _serial];
private _sessionToken = format ["%1:%2:%3", clientOwner, CBA_missionTime, _serial];
uiNamespace setVariable ["ACME_CS_SessionToken", _sessionToken];
uiNamespace setVariable ["ACME_CS_EntryCancelToken", ""];
uiNamespace setVariable ["ACME_CS_EntryProvider", []];
// The old medical menu was closed under the modal PFH guard above; do not
// issue another unqualified closeDialog while this new episode is preparing.
[true, _medic, _patient, _sessionToken] call ACME_fnc_chestAccessPreparing;
private _cancelCode = compile format [
    "if ((uiNamespace getVariable ['ACME_CS_SessionToken','']) == '%1') then {uiNamespace setVariable ['ACME_CS_EntryCancelToken','%1'];}; false",
    _sessionToken
];
private _keys = [];
_keys pushBack ([0x01, [false,false,false], _cancelCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler);
_keys pushBack ([0xF0, [false,false,false], _cancelCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler);
uiNamespace setVariable ["ACME_CS_EntryKeys", _keys];
[_patient, "chestSealPatientBegin", [_patient, _sessionToken, _medic]] call ACME_fnc_ownerDispatch;

// Register pending viewers too, so disconnect/death before onLoad cannot strand a workspace token.
["ACME_CS_session", [_patient, _medic, "join", _sessionToken]] call CBA_fnc_serverEvent;
private _open = {
    params ["_p", "_tok", "_m", "_sourceMedicalMenu", "_generation", "_sourceMedicalEpoch", "_patientOwner"];
    if ((uiNamespace getVariable ["ACME_CS_SessionToken", ""]) != _tok) exitWith {};
    // Opening the medical menu during preparation is an explicit cancellation.
    // Never replace that newer display, including on the readiness frame.
    // Its renderer epoch also catches a key press/release that opened and
    // closed the medical display before this preparation worker next ran.
    private _medicalMenu = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
    if ((uiNamespace getVariable ["ACME_medicalMenuRendererEpoch", 0]) != _sourceMedicalEpoch
        || {!isNull _medicalMenu && {_medicalMenu isNotEqualTo _sourceMedicalMenu}}) exitWith {
        [] call ACME_fnc_chestSealClose;
    };
    if (isNull _p || {isNull _m} || {!alive _m} || {!local _m}
        || {_m getVariable ["ACE_isUnconscious", false]}
        || {objectParent _m isNotEqualTo objectParent _p}
        || {([_m, _p] call ACME_fnc_patientInteractionDistance) > (missionNamespace getVariable ["ace_medical_gui_maxDistance", 3])}) exitWith {
        [] call ACME_fnc_chestSealClose;
    };

    {
        if (!(_x isEqualTo -1) && {!(_x isEqualTo "")}) then {[_x, "keydown"] call CBA_fnc_removeKeyHandler;};
    } forEach (uiNamespace getVariable ["ACME_CS_EntryKeys", []]);
    uiNamespace setVariable ["ACME_CS_EntryKeys", []];
    uiNamespace setVariable ["ACME_CS_EntryPFH", -1];
    uiNamespace setVariable ["ACME_CS_EntryCancelToken", ""];
    uiNamespace setVariable ["ACME_CS_EntryProvider", []];
    [false, _m, _p, _tok] call ACME_fnc_chestAccessPreparing;

    // Presentation begins only after casualty/carrier preparation is complete. The workspace minigame still opens
    // even if the provider pose cannot start; animation can never veto the clinical UI.
    private _holdEpoch = [_m, _p] call ACME_fnc_chestSealProviderHoldStart;
    _m setVariable ["ACME_CS_providerHoldEpoch", _holdEpoch, false];
    uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch", _holdEpoch];

    // Experimental display mode creates its panel on the next frame. Recheck
    // this exact session and source menu there too: a late open cannot replace
    // an H-opened medical menu or create a dialog after cancel/retry.
    private _mayOpen = {
        params ["_token", "_sourceMenu", "_patient", "_medic", "_generation", "_kitEpoch", "_medicalEpoch",
            "_patientOwner", "_providerLocalityEpoch"];
        private _menu = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
        (uiNamespace getVariable ["ACME_CS_SessionToken", ""]) == _token
            && {(uiNamespace getVariable ["ACME_CS_SessionSerial", -1]) == _generation}
            && {(uiNamespace getVariable ["ACME_medicalMenuRendererEpoch", 0]) == _medicalEpoch}
            && {!isNull _patient} && {!isNull _medic} && {local _medic} && {alive _medic}
            && {!(_medic getVariable ["ACE_isUnconscious", false])}
            && {(uiNamespace getVariable ["ACME_CS_Patient", objNull]) isEqualTo _patient}
            && {(uiNamespace getVariable ["ACME_CS_Medic", objNull]) isEqualTo _medic}
            && {(_patient getVariable ["ACME_equipmentKitEpoch", 0]) == _kitEpoch}
            && {owner _patient == _patientOwner}
            && {(_medic getVariable ["ACME_providerLocalityEpoch", 0]) == _providerLocalityEpoch}
            && {isNull _menu || {_menu isEqualTo _sourceMenu}}
    };
    ["ACME_ChestSeal_Dialog", _mayOpen, [_tok, _sourceMedicalMenu, _p, _m, _generation,
        uiNamespace getVariable ["ACME_CS_PatientKitEpoch", 0], _sourceMedicalEpoch,
        _patientOwner, _m getVariable ["ACME_providerLocalityEpoch", 0]]] call ACME_fnc_minigameOpen;
    [{
        params ["_p", "_tok"];
        if ((uiNamespace getVariable ["ACME_CS_SessionToken", ""]) == _tok
            && {isNull (uiNamespace getVariable ["ACME_CS_DLG", displayNull])}) then {
            [] call ACME_fnc_chestSealClose;
        };
    }, [_p, _tok], 0.2] call CBA_fnc_waitAndExecute;
};
private _entryPFH = [{
    params ["_args", "_pfh"];
    _args params ["_p", "_tok", "_m", "_open", "_patientOwner", "_joined", "_presentationUntil",
        "_deadline", "_nextRetry", "_retryCount", "_sourceMedicalMenu", "_generation", "_sourceMedicalEpoch"];
    if ((uiNamespace getVariable ["ACME_CS_SessionToken", ""]) != _tok) exitWith {
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };
    // A deleted patient is objNull on this machine. Do not attempt its
    // replicated token/member lookup after removal or respawn.
    if (isNull _p) exitWith {[] call ACME_fnc_chestSealClose;};
    private _medicalMenu = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
    if ((uiNamespace getVariable ["ACME_medicalMenuRendererEpoch", 0]) != _sourceMedicalEpoch
        || {!isNull _medicalMenu && {_medicalMenu isNotEqualTo _sourceMedicalMenu}}) exitWith {
        [] call ACME_fnc_chestSealClose;
    };
    if ((_p getVariable ["ACME_equipmentKitEpoch", 0]) != (uiNamespace getVariable ["ACME_CS_PatientKitEpoch", 0])) exitWith {
        [] call ACME_fnc_chestSealClose;
    };
    private _member = _tok in (_p getVariable ["ACME_CS_ProcedureTokens", []]);
    if (isNull _p || {isNull _m} || {!alive _m} || {!local _m} || {!([_m] call ace_common_fnc_isPlayer)}
        || {_m getVariable ["ACE_isUnconscious", false]}
        || {objectParent _m isNotEqualTo objectParent _p}
        || {([_m, _p] call ACME_fnc_patientInteractionDistance) > (missionNamespace getVariable ["ace_medical_gui_maxDistance", 3])}
        || {_joined && {!_member}}
        || {(uiNamespace getVariable ["ACME_CS_EntryCancelToken", ""]) == _tok}) exitWith {
        [] call ACME_fnc_chestSealClose;
    };
    // Locality handoff invalidates the old patient's animation-preparation
    // worker. Retire this token instead of opening an unprepared shared UI.
    // The medic can retry after the owner has settled; never mutate a stale
    // machine's vest/roll state or leave an infinite "Preparing..." banner.
    if (owner _p != _patientOwner) exitWith {
        diag_log format ["[ACME MODAL B263] chest seal owner changed; patient=%1 old=%2 new=%3 token=%4",
            netId _p, _patientOwner, owner _p, _tok];
        ["Chest procedure interrupted by patient locality change. Please retry.", 4, _m] call ACME_fnc_netNotice;
        [] call ACME_fnc_chestSealClose;
    };
    if (CBA_missionTime >= _deadline) exitWith {
        diag_log format ["[ACME MODAL B263] chest seal preparation timeout; patient=%1 owner=%2 token=%3 joined=%4 ready=%5",
            netId _p, owner _p, _tok, _member, _p getVariable ["ACME_CS_ProcedureReadyAt", -1]];
        ["Chest procedure preparation timed out; no patient-owner readiness received. Please retry.", 4, _m] call ACME_fnc_netNotice;
        [] call ACME_fnc_chestSealClose;
    };
    // PatientBegin is token-idempotent on its owner. Bounded retries recover
    // a missing first dispatch / delayed replication without duplicating
    // patient animations or clinical edits. Never resend once joined.
    if (!_member && {CBA_missionTime >= _nextRetry} && {_retryCount < 4}) then {
        [_p, "chestSealPatientBegin", [_p, _tok, _m]] call ACME_fnc_ownerDispatch;
        _args set [8, CBA_missionTime + 3];
        _args set [9, _retryCount + 1];
    };
    if (_member) then {_args set [5, true];};
    private _pose = _m getVariable ["ACME_treatmentPoseState", []];
    private _mode = _pose param [1, ""];
    private _entry = _m getVariable ["ACME_chestAccessProvider", []];
    // Only the synchronously guarded chest-seal provider start can assign this identity. Observing a same-patient
    // chestAccess pose is insufficient: an incoming CPR/BVM chest-access episode may have replaced preparation.
    private _provider = uiNamespace getVariable ["ACME_CS_EntryProvider", []];
    if (!(_provider isEqualTo [])
        && {(!(_mode in ["", "chestAccess"]))
            || {_mode == "chestAccess" && {(_pose param [0, -2]) != (_provider select 0)}}
            || {(_entry param [2, ""]) != (_provider select 1)}}) exitWith {
        [] call ACME_fnc_chestSealClose;
    };
    private _readyAt = _p getVariable ["ACME_CS_ProcedureReadyAt", -1];
    // Only the patient owner acknowledges completed physical preparation. A slow network/frame may take longer
    // than any nominal animation duration; keep the cancellable session alive until that acknowledgement arrives.
    if (!_member || {_readyAt < 0} || {serverTime < _readyAt}) exitWith {};
    if (_presentationUntil < 0) then {
        _presentationUntil = CBA_missionTime + 4.5;
        _args set [6, _presentationUntil];
    };

    // Normal path hands the frozen medic4 straight into workspace. Bound only provider presentation after the
    // casualty is actually ready: an unobserved/overridden finite move cannot veto the clinical UI indefinitely.
    private _stage = _pose param [3,-2];
    if (!(_mode in ["", "chestAccess"]) || {_mode == "chestAccess" && {_provider isEqualTo []}}) exitWith {
        [] call ACME_fnc_chestSealClose;
    };
    if (_mode == "chestAccess" && {_stage < 3} && {CBA_missionTime < _presentationUntil}) exitWith {};
    [_pfh] call CBA_fnc_removePerFrameHandler;
    [_p, _tok, _m, _sourceMedicalMenu, _generation, _sourceMedicalEpoch, _patientOwner] call _open;
}, 0, [_patient, _sessionToken, _medic, _open, owner _patient, false, -1,
    CBA_missionTime + 30, CBA_missionTime + 3, 0, _oldMedicalMenu, _serial, _sourceMedicalEpoch]] call CBA_fnc_addPerFrameHandler;
uiNamespace setVariable ["ACME_CS_EntryPFH", _entryPFH];
