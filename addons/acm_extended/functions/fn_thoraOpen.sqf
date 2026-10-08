// Open the thoracostomy mini-game after one simple patient-side chest-access preparation.
// Stable rule: thoracostomy preparation never owns a provider medic4 pose. The casualty/gear transaction may
// animate, but the medic stays free while the source medical menu is closed and Preparing... is visible.
params ["_medic", "_patient", ["_bodyPart", ""]];
if (isNull _patient || {isNull _medic} || {!local _medic}) exitWith {};
if !([_medic, _patient] call ACME_fnc_thoraCanOpen) exitWith {
    ["Thoracostomy cannot start: kit, procedure permission, or site availability changed.", 3, _medic] call ACME_fnc_netNotice;
};

// Recover any provider presentation left by an older build before starting this providerless flow.
private _oldChest = _medic getVariable ["ACME_chestAccessProvider", []];
if ((_oldChest param [0, objNull]) isEqualTo _patient) then {
    private _oldToken = _oldChest param [2, ""];
    if (_oldToken != "") then {
        [_medic, _patient, "stop", false, _oldToken] call ACME_fnc_chestAccessVestProvider;
    };
};

// Thoracostomy is modal, not a normal timed ACE treatment. Clear stale generic treatment/menu presentation.
_medic setVariable ["ACME_treatmentPreflightActive", false, false];
_medic setVariable ["ACME_treatmentPreflightToken", "", false];
_medic setVariable ["ACME_treatmentPreflightBypass", [], false];
_medic setVariable ["ACME_treatmentPreflightStartedAt", -1, false];
_medic setVariable ["ACME_nativeTreatmentRate", [], true];
[_medic, [["treatmentEndInAnim"]]] call ACM_core_fnc_setAceMedicalState;
[_medic, "", -1, true] call ACME_fnc_treatmentPoseStop;
[_medic, true] call ACME_fnc_menuPoseStop;
// No provider animation follows this handoff. Release temporary stance/speed ownership immediately and leave
// the selected weapon alone; the thoracostomy workspace itself must never control the medic skeleton.
_medic setUnitPos "AUTO";
_medic setAnimSpeedCoef 1;
["ace_common_setAnimSpeedCoef", [_medic, 1]] call CBA_fnc_globalEvent;

private _ecgJostleKey = "ui:thora:" + str clientOwner;
[_patient, _ecgJostleKey, true] call ACME_fnc_ecgJostleRequest;

uiNamespace setVariable ["ACME_Thora_Medic", _medic];
uiNamespace setVariable ["ACME_Thora_Patient", _patient];
uiNamespace setVariable ["ACME_Thora_BodyPart", _bodyPart];

private _serial = (uiNamespace getVariable ["ACME_Thora_ChestAccessSerial", 0]) + 1;
uiNamespace setVariable ["ACME_Thora_ChestAccessSerial", _serial];
private _lease = format ["thora:%1:%2:%3", clientOwner, floor (CBA_missionTime * 1000), _serial];
uiNamespace setVariable ["ACME_Thora_ChestAccessLease", _lease];
uiNamespace setVariable ["ACME_Thora_EntryCancelToken", ""];

// Reuse the same preflight flag the medical renderer already understands. This is the important menu-lifetime
// ownership: while it is true, no generic same-click reopen is allowed over Preparing...
_medic setVariable ["ACME_chestAccessPreflightActive", true, false];
_medic setVariable ["ACME_chestAccessPreflightToken", _lease, false];
_medic setVariable ["ACME_chestAccessPreflightCancel", false, false];

// B263: take ownership of both ACE and ACME menu PFHs synchronously. Waiting
// until the procedure's onLoad leaves an unsafe interval on mod-heavy clients.
ace_medical_gui_pendingReopen = false;
call ACM_GUI_fnc_pauseMedicalMenuPFH;
private _menuDisplay = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
if (!isNull _menuDisplay) then {_menuDisplay closeDisplay 1;};
if (dialog) then {closeDialog 0;};
[true, _medic, _patient, _lease] call ACME_fnc_chestAccessPreparing;

// Escape/F0 cancels only this pending thoracostomy entry.
private _cancelCode = compile format [
    "private _m=uiNamespace getVariable ['ACME_Thora_Medic',objNull]; if (!isNull _m && {local _m} && {(_m getVariable ['ACME_chestAccessPreflightToken','']) == '%1'}) then {_m setVariable ['ACME_chestAccessPreflightCancel',true,false]; uiNamespace setVariable ['ACME_Thora_EntryCancelToken','%1'];}; false",
    _lease
];
private _keys = [];
_keys pushBack ([0x01, [false,false,false], _cancelCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler);
_keys pushBack ([0xF0, [false,false,false], _cancelCode, "keydown", "", false, 0] call CBA_fnc_addKeyHandler);
uiNamespace setVariable ["ACME_Thora_EntryKeys", [_lease, _keys]];

// Start exactly one casualty-owner gear/body transaction. chestAccessVestAcquire treats "thoracostomy" as
// providerless, so this cannot freeze the medic in chestAccess/medic4.
[_patient, _medic, _lease, true, "thoracostomy", _lease] call ACME_fnc_chestAccessVestEvent;

private _finishPrep = {
    params ["_m", "_p", "_lease"];
    private _entry = uiNamespace getVariable ["ACME_Thora_EntryKeys", []];
    if ((_entry param [0, ""]) == _lease) then {
        {
            if (!(_x isEqualTo -1) && {!(_x isEqualTo "")}) then {[_x, "keydown"] call CBA_fnc_removeKeyHandler;};
        } forEach (_entry param [1, []]);
        uiNamespace setVariable ["ACME_Thora_EntryKeys", []];
    };
    uiNamespace setVariable ["ACME_Thora_EntryCancelToken", ""];
    [false, _m, _p, _lease] call ACME_fnc_chestAccessPreparing;

    if (!isNull _m && {local _m} && {(_m getVariable ["ACME_chestAccessPreflightToken", ""]) == _lease}) then {
        _m setVariable ["ACME_chestAccessPreflightActive", false, false];
        _m setVariable ["ACME_chestAccessPreflightToken", "", false];
        _m setVariable ["ACME_chestAccessPreflightCancel", false, false];
    };
    ace_medical_gui_pendingReopen = false;
};

private _releaseLease = {
    params ["_p", "_m", "_lease"];
    if ((uiNamespace getVariable ["ACME_Thora_ChestAccessLease", ""]) != _lease) exitWith {};
    uiNamespace setVariable ["ACME_Thora_ChestAccessLease", ""];
    if (!isNull _p) then {
        [_p, _m, _lease, false, "thoracostomy"] call ACME_fnc_chestAccessVestEvent;
    };
};

private _abort = {
    params ["_p", "_m", "_lease", "_finish", "_release", ["_reopen", true, [false]]];
    // A late timeout must never tear down another provider's newer dialog.
    if ((uiNamespace getVariable ["ACME_Thora_ChestAccessLease", ""]) != _lease) exitWith {};
    private _cancelledByUser = (uiNamespace getVariable ["ACME_Thora_EntryCancelToken", ""]) == _lease;
    if (!_cancelledByUser) then {
        diag_log format ["[ACME MODAL B263] thoracostomy entry aborted; patient=%1 token=%2 owner=%3",
            if (isNull _p) then {"null"} else {netId _p}, _lease,
            if (isNull _p) then {-1} else {owner _p}];
        if (!isNull _m && {local _m}) then {
            ["Thoracostomy preparation interrupted; the workspace was released. Please retry.", 3, _m] call ACME_fnc_netNotice;
        };
    };
    // Full idempotent teardown also retires modal PFHs, ECG/jostle markers,
    // prep keys, scoped carrier lease, stance state and stale UI references.
    // The former partial _finish/_release path could leave these stranded.
    [] call ACME_fnc_thoraClose;
};

[{
    params ["_p", "_m", "_lease"];
    if (isNull _p || {isNull _m} || {!local _m}) exitWith {true};
    if ((uiNamespace getVariable ["ACME_Thora_ChestAccessLease", ""]) != _lease) exitWith {true};
    if ((_m getVariable ["ACME_chestAccessPreflightCancel", false])
        || {(uiNamespace getVariable ["ACME_Thora_EntryCancelToken", ""]) == _lease}
        || {!alive _m}
        || {_m getVariable ["ACE_isUnconscious", false]}
        || {isNull objectParent _m && {(_m distance _p) > ace_medical_gui_maxDistance}}
        || {objectParent _m isNotEqualTo objectParent _p}) exitWith {true};

    private _readyLease = _p getVariable ["ACME_chestAccess_readyLease", ""];
    private _ready = _p getVariable ["ACME_chestAccess_readyServer", -1];
    (_readyLease == _lease) && {_ready isEqualType 0} && {_ready >= 0} && {serverTime >= _ready}
}, {
    params ["_p", "_m", "_lease", "_finish", "_release", "_abort"];
    private _cancelled = isNull _p || {isNull _m} || {!local _m}
        || {(_m getVariable ["ACME_chestAccessPreflightCancel", false])}
        || {(uiNamespace getVariable ["ACME_Thora_EntryCancelToken", ""]) == _lease}
        || {(uiNamespace getVariable ["ACME_Thora_ChestAccessLease", ""]) != _lease}
        || {!alive _m}
        || {_m getVariable ["ACE_isUnconscious", false]}
        || {isNull objectParent _m && {(_m distance _p) > ace_medical_gui_maxDistance}}
        || {objectParent _m isNotEqualTo objectParent _p};
    if (_cancelled) exitWith {
        [_p, _m, _lease, _finish, _release, true] call _abort;
    };

    [_m, _p, _lease] call _finish;
    ["ACME_Thoracostomy_Dialog"] call ACME_fnc_minigameOpen;

    [{
        params ["_p", "_m", "_lease", "_release"];
        if ((uiNamespace getVariable ["ACME_Thora_ChestAccessLease", ""]) != _lease) exitWith {};
        if (isNull (findDisplay 86600)) then {
            diag_log format ["[ACME MODAL B263] thoracostomy dialog did not initialize; patient=%1 token=%2",
                if (isNull _p) then {"null"} else {netId _p}, _lease];
            if (!isNull _m && {local _m}) then {
                ["Thoracostomy panel could not open. Please retry.", 3, _m] call ACME_fnc_netNotice;
            };
            [] call ACME_fnc_thoraClose;
        };
    }, [_p, _m, _lease, _release], 0.6] call CBA_fnc_waitAndExecute;
}, [_patient, _medic, _lease, _finishPrep, _releaseLease, _abort], 20, {
    params ["_p", "_m", "_lease", "_finish", "_release", "_abort"];
    if ((uiNamespace getVariable ["ACME_Thora_ChestAccessLease", ""]) == _lease) then {
        diag_log format ["[ACME THORACOSTOMY] Chest-access preparation timed out on %1; aborting cleanly.", netId _p];
    };
    [_p, _m, _lease, _finish, _release, true] call _abort;
}] call CBA_fnc_waitUntilAndExecute;
