// Close thoracostomy workspace and release the one patient-side chest-access lease.
// Stable thoracostomy entry is providerless; the provider cleanup below exists only to recover stale state from
// an older/hot-loaded build and is not part of the normal lifecycle.
private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
private _medic = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
private _lease = uiNamespace getVariable ["ACME_Thora_ChestAccessLease", ""];

private _entryKeys = uiNamespace getVariable ["ACME_Thora_EntryKeys", []];
{
    if (!(_x isEqualTo -1) && {!(_x isEqualTo "")}) then {[_x, "keydown"] call CBA_fnc_removeKeyHandler;};
} forEach (_entryKeys param [1, []]);
uiNamespace setVariable ["ACME_Thora_EntryKeys", []];
uiNamespace setVariable ["ACME_Thora_EntryCancelToken", ""];
[false, _medic, _patient, _lease] call ACME_fnc_chestAccessPreparing;

if (!isNull _medic && {local _medic}) then {
    if ((_medic getVariable ["ACME_chestAccessPreflightToken", ""]) == _lease || {_lease == ""}) then {
        _medic setVariable ["ACME_chestAccessPreflightActive", false, false];
        _medic setVariable ["ACME_chestAccessPreflightToken", "", false];
        _medic setVariable ["ACME_chestAccessPreflightCancel", false, false];
    };

    _medic setVariable ["ACME_treatmentPreflightActive", false, false];
    _medic setVariable ["ACME_treatmentPreflightToken", "", false];
    _medic setVariable ["ACME_treatmentPreflightBypass", [], false];
    _medic setVariable ["ACME_treatmentPreflightStartedAt", -1, false];
    _medic setVariable ["ACME_nativeTreatmentRate", [], true];
    [_medic, [["treatmentEndInAnim"]]] call ACM_core_fnc_setAceMedicalState;

    // Hot-load/backward compatibility only: current thoracostomy never starts this provider animation.
    private _oldProvider = _medic getVariable ["ACME_chestAccessProvider", []];
    if ((_oldProvider param [0, objNull]) isEqualTo _patient) then {
        private _oldToken = _oldProvider param [2, ""];
        if (_oldToken != "") then {
            [_medic, _patient, "stop", false, _oldToken] call ACME_fnc_chestAccessVestProvider;
        };
    };

    if !([_medic] call ACME_fnc_providerStanceOwned) then {
        _medic setUnitPos "AUTO";
        _medic setAnimSpeedCoef 1;
        ["ace_common_setAnimSpeedCoef", [_medic, 1]] call CBA_fnc_globalEvent;
    };
};

if (_lease != "") then {
    uiNamespace setVariable ["ACME_Thora_ChestAccessLease", ""];
    if (!isNull _patient) then {
        [_patient, _medic, _lease, false, "thoracostomy"] call ACME_fnc_chestAccessVestEvent;
    };
};

if (!isNull _patient) then {
    [_patient, "ui:thora:" + str clientOwner, false] call ACME_fnc_ecgJostleRequest;
};
if (!isNull _patient && {_patient getVariable ["ACME_headElev_Suspended", false]}) then {
    _patient setVariable ["ACME_headElev_ResumePending", true, true];
    [{
        _this call ACME_fnc_headElevTryResume
    }, _patient, missionNamespace getVariable ["ACME_headElev_resumeDelay", 0.75]] call CBA_fnc_waitAndExecute;
};

private _pfh = uiNamespace getVariable ["ACME_Thora_PFH", -1];
if (_pfh isEqualType 0 && {_pfh >= 0}) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
uiNamespace setVariable ["ACME_Thora_PFH", -1];

call ACM_GUI_fnc_resumeMedicalMenuPFH;

uiNamespace setVariable ["ACME_Thora_Held", ""];
uiNamespace setVariable ["ACME_Thora_Palpating", false];
uiNamespace setVariable ["ACME_Thora_Cutting", false];
uiNamespace setVariable ["ACME_Thora_Prepping", false];
uiNamespace setVariable ["ACME_Thora_TubeSnap", false];
uiNamespace setVariable ["ACME_Thora_KellyArmed", false];
uiNamespace setVariable ["ACME_Thora_LMBDown", false];
uiNamespace setVariable ["ACME_Thora_DLG", displayNull];
uiNamespace setVariable ["ACME_Thora_ShakeBase", []];
uiNamespace setVariable ["ACME_Thora_ShakeBase_off", [0, 0]];
uiNamespace setVariable ["ACME_Thora_Shade", []];
uiNamespace setVariable ["ACME_Thora_Shade_n", -1];
uiNamespace setVariable ["ACME_minigame_open", false];

ace_medical_gui_pendingReopen = false;
if (!isNull _patient && {!isNull _medic} && {alive _medic} && {local _medic}
    && {!(_medic getVariable ["ACE_isUnconscious", false])} && {[_medic] call ace_common_fnc_isPlayer}) then {
    [_patient, "airway"] call ACME_fnc_reopenMedicalMenu;
};
