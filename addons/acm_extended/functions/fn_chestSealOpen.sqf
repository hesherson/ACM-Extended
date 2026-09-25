params ["_medic", "_patient", ["_bodyPart", ""], ["_startTool", "seal"]];
if (isNull _patient || {isNull _medic} || {!local _medic} || {!alive _medic}
    || {_medic getVariable ["ACE_isUnconscious", false]}) exitWith {};

if !(missionNamespace getVariable ["ACME_sys_chestSeal", true]) exitWith {
    if (_startTool == "spear") then {
        if (([_medic, "ACME_NARSPEAR"] call ace_common_fnc_getCountOfItem) > 0) then {
            _medic removeItem "ACME_NARSPEAR";
            [_medic, _patient] call ACM_breathing_fnc_performNCD;
        };
    } else {
        if (([_medic, "ACM_ChestSeal"] call ace_common_fnc_getCountOfItem) > 0) then {
            _medic removeItem "ACM_ChestSeal";
            [_medic, _patient] call ACM_breathing_fnc_applyChestSeal;
        };
    };
};

if (!isNull (uiNamespace getVariable ["ACME_CS_DLG", displayNull])
    || {(uiNamespace getVariable ["ACME_CS_SessionToken", ""]) != ""}) exitWith {};
uiNamespace setVariable ["ACME_CS_Medic", _medic];
uiNamespace setVariable ["ACME_CS_Patient", _patient];
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
// The initial click owns preparation immediately. Install cancellation only after closing the old menu, so
// that accepted click is not interpreted as a cancellation of the session it just created.
closeDialog 0;
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
    params ["_p", "_tok", "_m"];
    if ((uiNamespace getVariable ["ACME_CS_SessionToken", ""]) != _tok) exitWith {};
    if (isNull _p || {isNull _m} || {!alive _m} || {!local _m}
        || {_m getVariable ["ACE_isUnconscious", false]}
        || {!isNull objectParent _m} || {!isNull objectParent _p}
        || {_m distance _p > (missionNamespace getVariable ["ace_medical_gui_maxDistance", 3])}) exitWith {
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

    ["ACME_ChestSeal_Dialog"] call ACME_fnc_minigameOpen;
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
    _args params ["_p", "_tok", "_m", "_open", "_patientOwner", "_joined", "_presentationUntil"];
    if ((uiNamespace getVariable ["ACME_CS_SessionToken", ""]) != _tok) exitWith {
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };
    private _member = _tok in (_p getVariable ["ACME_CS_ProcedureTokens", []]);
    if (isNull _p || {isNull _m} || {!alive _m} || {!local _m} || {_m isNotEqualTo ACE_player}
        || {_m getVariable ["ACE_isUnconscious", false]}
        || {!isNull objectParent _m} || {!isNull objectParent _p}
        || {_m distance _p > (missionNamespace getVariable ["ace_medical_gui_maxDistance", 3])}
        || {owner _p != _patientOwner}
        || {_joined && {!_member}}
        || {(uiNamespace getVariable ["ACME_CS_EntryCancelToken", ""]) == _tok}) exitWith {
        [] call ACME_fnc_chestSealClose;
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
    [_p, _tok, _m] call _open;
}, 0, [_patient, _sessionToken, _medic, _open, owner _patient, false, -1]] call CBA_fnc_addPerFrameHandler;
uiNamespace setVariable ["ACME_CS_EntryPFH", _entryPFH];
