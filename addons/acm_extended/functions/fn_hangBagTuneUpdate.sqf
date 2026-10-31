disableSerialization;
private _d = findDisplay 87100;
if (isNull _d) exitWith {};

private _off = [
    (sliderPosition 87101) / 100,
    (sliderPosition 87102) / 100,
    (sliderPosition 87103) / 100
];
private _rot = [sliderPosition 87104, sliderPosition 87105, sliderPosition 87106];
private _lineEnd = [
    (sliderPosition 87107) / 100,
    (sliderPosition 87108) / 100,
    (sliderPosition 87109) / 100
];
private _lineRot = [sliderPosition 87120, sliderPosition 87121, sliderPosition 87122];

missionNamespace setVariable ["ACME_hang_handOffset", _off];
missionNamespace setVariable ["ACME_hang_bagEuler", _rot];
missionNamespace setVariable ["ACME_hang_linePatientOffset", _lineEnd];
missionNamespace setVariable ["ACME_hang_linePatientEuler", _lineRot];

(_d displayCtrl 87111) ctrlSetText format ["X  %1 m", (_off#0) toFixed 3];
(_d displayCtrl 87112) ctrlSetText format ["Y  %1 m", (_off#1) toFixed 3];
(_d displayCtrl 87113) ctrlSetText format ["Z  %1 m", (_off#2) toFixed 3];
(_d displayCtrl 87114) ctrlSetText format ["Horizontal %1 deg", round (_rot#0)];
(_d displayCtrl 87115) ctrlSetText format ["Pitch      %1 deg", round (_rot#1)];
(_d displayCtrl 87116) ctrlSetText format ["Roll       %1 deg", round (_rot#2)];
(_d displayCtrl 87117) ctrlSetText format ["X  %1 m", (_lineEnd#0) toFixed 3];
(_d displayCtrl 87118) ctrlSetText format ["Y  %1 m", (_lineEnd#1) toFixed 3];
(_d displayCtrl 87119) ctrlSetText format ["Z  %1 m", (_lineEnd#2) toFixed 3];
(_d displayCtrl 87123) ctrlSetText format ["Horizontal %1 deg", round (_lineRot#0)];
(_d displayCtrl 87124) ctrlSetText format ["Pitch      %1 deg", round (_lineRot#1)];
(_d displayCtrl 87125) ctrlSetText format ["Roll       %1 deg", round (_lineRot#2)];

private _medic = (call ACME_fnc_controlledProvider);
private _bag = _medic getVariable ["ACME_hang_Bag", objNull];
if (!isNull _bag) then {
    detach _bag;
    _bag attachTo [
        _medic,
        _off,
        missionNamespace getVariable ["ACME_hang_handSel", "RightHand"],
        true
    ];
    [_bag, _rot] call BIS_fnc_setObjectRotation;
};

// this oriented helper is the patient-side rope endpoint. the local tip offset is deliberately not [0,0,0], so the
// yaw, pitch and roll produce a visible endpoint change while you tune.
private _patient = _medic getVariable ["ACME_hang_Patient", objNull];
private _anchor = _medic getVariable ["ACME_hang_LineAnchor", objNull];
if (!isNull _patient && {!isNull _anchor}) then {
    detach _anchor;
    _anchor attachTo [_patient, _lineEnd];
    [_anchor, _lineRot] call BIS_fnc_setObjectRotation;
};
