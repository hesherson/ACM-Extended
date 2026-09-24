params ["_medic", "_patient", ["_bodyPart", ""], ["_startTool", "seal"]];
if (isNull _patient || {isNull _medic}) exitWith {};

if !(missionNamespace getVariable ["ACME_sys_chestSeal", true]) exitWith {
    if (_startTool == "spear") then {
        if (([_medic, "ACME_NARSPEAR"] call ACME_fnc_itemCount) > 0) then {
            [_medic, "ACME_NARSPEAR"] call ACME_fnc_itemTake;
            [_medic, _patient] call ACM_breathing_fnc_performNCD;
        };
    } else {
        if (([_medic, "ACM_ChestSeal"] call ACME_fnc_itemCount) > 0) then {
            [_medic, "ACM_ChestSeal"] call ACME_fnc_itemTake;
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
[_patient, "chestSealPatientBegin", [_patient, _sessionToken, _medic]] call ACME_fnc_ownerDispatch;

// Register pending viewers too, so disconnect/death before onLoad cannot strand a workspace token.
["ACME_CS_session", [_patient, _medic, "join", _sessionToken]] call CBA_fnc_serverEvent;
private _open = {
    params ["_p", "_tok", "_m"];
    if ((uiNamespace getVariable ["ACME_CS_SessionToken", ""]) != _tok) exitWith {};
    if (isNull _p || {isNull _m} || {!alive _m} || {!local _m}
        || {_m getVariable ["ACE_isUnconscious", false]}) exitWith {
        [] call ACME_fnc_chestSealClose;
    };

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
[{
    params ["_p", "_tok", "_m"];
    if (isNull _p || {!alive _m} || {(uiNamespace getVariable ["ACME_CS_SessionToken", ""]) != _tok}) exitWith {true};
    private _readyAt = _p getVariable ["ACME_CS_ProcedureReadyAt", -1];

    // Normal path: carrier medic4 is still owned and has reached its 2.2 s frozen stage. Open at that exact
    // boundary and chestSealProviderHoldStart hands directly into the workspace pose. If provider presentation
    // failed/retired, clinical UI remains fail-open instead of being blocked forever by theatre.
    private _pose = _m getVariable ["ACME_treatmentPoseState", []];
    private _mode = _pose param [1,""];
    private _stage = _pose param [3,-2];
    private _providerReady = (_mode == "chestAccess" && {_stage >= 3}) || {_mode != "chestAccess"};

    (_tok in (_p getVariable ["ACME_CS_ProcedureTokens", []]))
        && {_readyAt >= 0}
        && {serverTime >= _readyAt}
        && {_providerReady}
}, _open, [_patient, _sessionToken, _medic], 12, {
    params ["_p","_tok","_m"];
    if ((uiNamespace getVariable ["ACME_CS_SessionToken",""]) != _tok) exitWith {};
    diag_log format ["[ACME CHEST SEAL] Preparation timeout on %1; closing workspace instead of opening over an unfinished casualty.", netId _p];
    [] call ACME_fnc_chestSealClose;
}] call CBA_fnc_waitUntilAndExecute;
