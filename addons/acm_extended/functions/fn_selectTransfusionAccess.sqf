/*
 * Select one exact established IV or IO from the transfusion body map.
 * This deliberately bypasses ACM's old IV/IO toggle. The catheter or IO image itself is the route selector.
 */
params ["_bodyPart", ["_iv", true], ["_site", -1]];

disableSerialization;
private _display = findDisplay 86000;
if (isNull _display) exitWith {};
private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
if (isNull _patient) exitWith {};
_bodyPart = toLowerANSI _bodyPart;

private _valid = if (_iv) then {
    _site >= 0 && {[_patient, _bodyPart, 0, _site] call ACM_circulation_fnc_hasIV}
} else {
    [_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIO
};
if (!_valid) exitWith {};
private _selected = [missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1]];
if (_selected isEqualTo [_bodyPart,_iv,if (_iv) then {_site} else {0}]) exitWith {};


[[["transfusionSelectIV", _iv], ["transfusionSelectedBodyPart", _bodyPart], ["transfusionSelectedAccessSite", if (_iv) then {_site} else {0}]]] call ACM_circulation_fnc_setLocalUiState;
call ACM_circulation_fnc_TransfusionMenu_UpdateSelection;
[false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;

// Any access-site change can change the active and prepared pane contents. Force both stable-ID lists to rebuild.
uiNamespace setVariable ["ACME_infusion_ActiveInfusionListSignature", ""];
uiNamespace setVariable ["ACME_infusion_PreparedListSignature", ""];
call ACME_fnc_updateTransfusionAccessHotspots;
call ACME_fnc_updateTransfusionControls;
