params ["_medic", "_patient", "_epoch", "_id", "_document"];
private _request = uiNamespace getVariable ["DD1380_openRequest", []];
if (!hasInterface || {count _request != 5} || {!((_request select [0, 4]) isEqualTo [_medic, _patient, _epoch, _id])}
    || {isNull _medic} || {isNull _patient} || {!local _medic} || {!(_medic isEqualTo ACE_player)}) exitWith {false};
uiNamespace setVariable ["DD1380_openRequest", nil];
private _sourceDisplay = _request select 4;
if (!isNull _sourceDisplay && {!((findDisplay 38580) isEqualTo _sourceDisplay) || {!(ace_medical_gui_target isEqualTo _patient)}}) exitWith {false};
if (isNull _sourceDisplay && {dialog}) exitWith {false};
if (!alive _medic || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {!(_document isEqualType [])} || {count _document != 2}) exitWith {false};
private _sameVehicle = !isNull objectParent _medic && {objectParent _medic isEqualTo objectParent _patient};
if (!_sameVehicle && {_medic distance _patient > 6}) exitWith {false};
ace_medical_gui_pendingReopen = false;
call ACM_GUI_fnc_pauseMedicalMenuPFH;
if (dialog) then {closeDialog 0;};
_document params ["_revision", "_data"];
uiNamespace setVariable ["DD1380_context", [_medic, _patient, _epoch, _id, _revision, _data, +_data]];
createDialog "DD1380_Card1_dlg"
