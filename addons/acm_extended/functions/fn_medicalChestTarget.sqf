/* Resolve the visible model and its current state for both interaction menus. */
params ["_target"];
if (isNull _target || {isObjectHidden _target}) exitWith {[]};
private _chest = if (_target isKindOf "ACME_MedicalChest") then {_target} else {
    _target getVariable ["ACME_medicalChestAnchor", objNull]
};
if (isNull _chest || {_chest getVariable ["ACME_medicalChestTransition", false]}) exitWith {[]};
private _state = _chest getVariable ["ACME_medicalChestState", []];
if (_state isEqualTo []) exitWith {[]};
_state params ["_revision", "_open"];
private _active = if (_open) then {_chest getVariable ["ACME_medicalChestCabinet", objNull]} else {_chest};
if (_active isNotEqualTo _target) exitWith {[]};
[_chest, _revision, _open]
