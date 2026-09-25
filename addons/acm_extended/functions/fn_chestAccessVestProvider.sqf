// Provider-side owner for temporary chest-access carrier handling.
// The provider fully holsters/crouches through treatmentPoseStart, enters literal medic4, then publishes a
// presentation-ready token. Patient lift waits for that exact state when possible, with a bounded fail-open.
params [
    ["_medic", objNull, [objNull]],
    ["_patient", objNull, [objNull]],
    ["_op", "start", [""]],
    ["_handoff", false, [false]],
    ["_episodeToken", "", [""]],
    ["_preparationToken", "", [""]]
];
if (isNull _medic) exitWith {-1};
_op = toLowerANSI _op;

if (!local _medic) exitWith {
    [_medic, "chestAccessVestProvider", [_medic, _patient, _op, _handoff, _episodeToken, _preparationToken]] call ACME_fnc_ownerDispatch;
    -1
};

if (_op == "stop") exitWith {
    private _entry = _medic getVariable ["ACME_chestAccessProvider", []];
    private _entryPatient = _entry param [0, objNull];
    private _epoch = _entry param [1, -1];
    private _token = _entry param [2, ""];
    private _pose = _medic getVariable ["ACME_treatmentPoseState", []];

    // Callers resolve their already-validated preflight/clinical episode to its
    // provider token before stopping. Never infer ownership from patient identity:
    // an old same-patient callback may arrive while a newer preparation is running.
    if (_episodeToken == "" || {_episodeToken != _token}) exitWith {-1};

    if ((_entryPatient isEqualTo _patient)
        && {_epoch >= 0}
        && {(_pose param [0, -2]) == _epoch}
        && {(_pose param [1, ""]) == "chestAccess"}) then {
        [_medic, "chestAccess", _epoch, _handoff] call ACME_fnc_treatmentPoseStop;
    };

    if (_entryPatient isEqualTo _patient) then {
        _medic setVariable ["ACME_chestAccessProvider", [], false];
    };

    private _ready = _medic getVariable ["ACME_chestAccessProviderReady", []];
    if ((_ready param [0,""]) == _token) then {
        _medic setVariable ["ACME_chestAccessProviderReady", [], true];
    };
    _epoch
};

if (!alive _medic
    || {_medic getVariable ["ACE_isUnconscious", false]}
    || {[_medic] call ACME_fnc_animBlocked}
    || {_medic isEqualTo _patient}) exitWith {-1};

// A delayed owner packet may arrive after cancel/reopen or after the workspace has already opened. Carrier
// presentation belongs only to the original pending viewer; it must never replace a newer workspace/episode.
private _chestSealEntry = (_episodeToken find "vest:chestseal:") == 0;
if (_chestSealEntry && {
    _preparationToken == ""
    || {(uiNamespace getVariable ["ACME_CS_SessionToken", ""]) != _preparationToken}
    || {(uiNamespace getVariable ["ACME_CS_Medic", objNull]) isNotEqualTo _medic}
    || {(uiNamespace getVariable ["ACME_CS_Patient", objNull]) isNotEqualTo _patient}
    || {(uiNamespace getVariable ["ACME_CS_EntryKeys", []]) isEqualTo []}
    || {(uiNamespace getVariable ["ACME_CS_EntryCancelToken", ""]) == _preparationToken}
}) exitWith {-1};

// Ordinary chest-access start is routed through the casualty owner as well. Its
// preflight can be cancelled or handed to clinical work before this packet reaches
// the provider. Other callers (for example thoracostomy) have no preflight token.
if ((_episodeToken find "vest:access:") == 0 && {_preparationToken != ""} && {
    !(_medic getVariable ["ACME_chestAccessPreflightActive", false])
    || {(_medic getVariable ["ACME_chestAccessPreflightToken", ""]) != _preparationToken}
    || {((_medic getVariable ["ACME_chestAccess_treatment", []]) param [0, objNull]) isNotEqualTo _patient}
}) exitWith {-1};

private _armReadyProbe = {
    params ["_m","_epoch","_token"];
    if (_token == "") exitWith {};

    _m setVariable ["ACME_chestAccessProviderReady", [_token, -1], true];
    private _requiredStage = [1, 3] select (((_m getVariable ["ACME_chestAccess_treatment", []]) param [1, ""]) == "checkbreathing");

    [{
        params ["_m","_epoch","_token","_requiredStage"];
        if (isNull _m || {!local _m} || {!alive _m}
            || {_m getVariable ["ACE_isUnconscious", false]}) exitWith {true};

        private _entry = _m getVariable ["ACME_chestAccessProvider", []];
        if ((_entry param [2,""]) != _token || {(_entry param [1,-1]) != _epoch}) exitWith {true};

        private _state = _m getVariable ["ACME_treatmentPoseState", []];
        (_state param [0,-2]) == _epoch
            && {(_state param [1,""]) == "chestAccess"}
            && {(_state param [3,-2]) >= _requiredStage}
            && {(toLowerANSI animationState _m) == "ainvpknlmstpsnonwnondnon_medic4"}
    }, {
        params ["_m","_epoch","_token","_requiredStage"];
        if (isNull _m || {!local _m} || {!alive _m}
            || {_m getVariable ["ACE_isUnconscious", false]}) exitWith {};
        private _entry = _m getVariable ["ACME_chestAccessProvider", []];
        private _state = _m getVariable ["ACME_treatmentPoseState", []];
        if ((_entry param [2,""]) == _token && {(_entry param [1,-1]) == _epoch}
            && {(_state param [0,-2]) == _epoch} && {(_state param [1,""]) == "chestAccess"}
            && {(_state param [3,-2]) >= _requiredStage}
            && {(toLowerANSI animationState _m) == "ainvpknlmstpsnonwnondnon_medic4"}) then {
            _m setVariable ["ACME_chestAccessProviderReady", [_token, serverTime], true];
        };
    }, [_m,_epoch,_token,_requiredStage], 4.5, {
        params ["_m","_epoch","_token"];
        if (isNull _m || {!local _m} || {!alive _m}
            || {_m getVariable ["ACE_isUnconscious", false]}) exitWith {};
        private _entry = _m getVariable ["ACME_chestAccessProvider", []];
        if ((_entry param [2,""]) == _token && {(_entry param [1,-1]) == _epoch}) then {
            // -2 means the provider presentation timed out. The patient transaction may proceed fail-open.
            _m setVariable ["ACME_chestAccessProviderReady", [_token, -2], true];
        };
    }] call CBA_fnc_waitUntilAndExecute;
};

private _entry = _medic getVariable ["ACME_chestAccessProvider", []];
private _existingPatient = _entry param [0, objNull];
private _existingEpoch = _entry param [1, -1];
private _pose = _medic getVariable ["ACME_treatmentPoseState", []];

if ((_existingPatient isEqualTo _patient)
    && {_existingEpoch >= 0}
    && {(_pose param [0, -2]) == _existingEpoch}
    && {(_pose param [1, ""]) == "chestAccess"}) exitWith {
    if (_episodeToken != "") then {
        _medic setVariable ["ACME_chestAccessProvider", [_patient, _existingEpoch, _episodeToken], false];
        if (_chestSealEntry) then {
            uiNamespace setVariable ["ACME_CS_EntryProvider", [_existingEpoch, _episodeToken]];
        };
        [_medic,_existingEpoch,_episodeToken] call _armReadyProbe;
    };
    _existingEpoch
};

// A finished chest action may still own a frozen provider pose. Retire only known chest presentation owners
// as a handoff, so reverse carrier handling starts from the current work frame instead of inserting a neutral crouch.
private _prior = _medic getVariable ["ACME_treatmentPoseState", []];
private _priorMode = _prior param [1, ""];
private _priorEpoch = _prior param [0, -1];
if (_priorMode in ["stethoscope","inspect","chestSealWorkspace","roll"]
    && {_priorEpoch >= 0}) then {
    [_medic, _priorMode, _priorEpoch, true] call ACME_fnc_treatmentPoseStop;
};

private _epoch = [_medic, "chestAccess", -1, _patient] call ACME_fnc_treatmentPoseStart;
if (_epoch >= 0) then {
    _medic setVariable ["ACME_chestAccessProvider", [_patient, _epoch, _episodeToken], false];
    if (_chestSealEntry) then {
        uiNamespace setVariable ["ACME_CS_EntryProvider", [_epoch, _episodeToken]];
    };

    // treatmentPoseStart owns the rate for chest-seal preparation and ordinary access alike.
    [_medic,_epoch,_episodeToken] call _armReadyProbe;
};
_epoch
