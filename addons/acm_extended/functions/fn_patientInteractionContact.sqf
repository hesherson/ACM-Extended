/* Treatment contact shared by owner admission and native controllers.
 * Exact native seating keeps ACE's same-vehicle reachability contract. Ground
 * care keeps the existing treatment-distance contract, including a valid owned
 * elevation anchor. Separate seat helpers/walking occupants can share a live
 * aircraft, but must remain within actual 3D reach; ancestry grants no immunity,
 * cabin pressure, pose ownership, or unrestricted reach across an airframe.
 */
params [["_medic",objNull,[objNull]], ["_patient",objNull,[objNull]], ["_maxDistance",-1]];
if (isNull _medic || {isNull _patient}) exitWith {false};
if (_maxDistance isEqualTo -1) then {
    _maxDistance = missionNamespace getVariable ["ace_medical_gui_maxDistance",3];
};
if (!(_maxDistance isEqualType 0) || {!finite _maxDistance} || {_maxDistance < 0}) exitWith {false};
private _medicVehicle = objectParent _medic;
private _patientVehicle = objectParent _patient;
if (!isNull _medicVehicle && {_medicVehicle isEqualTo _patientVehicle}) exitWith {true};
if (isNull _medicVehicle && {isNull _patientVehicle}) exitWith {
    private _distance = [_medic,_patient] call ACME_fnc_patientInteractionDistance;
    _distance isEqualType 0 && {finite _distance} && {_distance >= 0} && {_distance <= _maxDistance}
};
private _distance = _medic distance _patient;
if (!finite _distance || {_distance > _maxDistance}) exitWith {false};
private _medicAir = [_medic,true] call ACME_fnc_flightAirframe;
if (isNull _medicAir) exitWith {false};
private _patientAir = [_patient,true] call ACME_fnc_flightAirframe;
!isNull _patientAir && {_patientAir isEqualTo _medicAir}
