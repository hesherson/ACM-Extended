/* [true ASL, ambient pressure, exposed/cabin pressure, supplied oxygen, Air].
 * Personal oxygen never changes the pressure surrounding trapped gas.
 * Aircraft have ambient pressure unless an actual pressure/altitude is
 * explicitly supplied by a vehicle object or inherited config property.
 * Object values are live pressure controls; config supplies a declared cabin
 * limit. No generic aircraft, sealed-door or equipment-name immunity exists.
 */
params ["_patient"];
if (isNull _patient) exitWith {[0,1,1,false,objNull]};
private _height = [_patient] call ACME_fnc_altitudeTrue;
private _ambient = [_height] call ACME_fnc_pressureAtAltitude;
private _pressure = _ambient;
// Healthy low-altitude ground vital updates must not perform aircraft surface
// rays. Such cabin pressure cannot constrain their oxygen ceiling, and their
// normal blood volume makes maneuver stress inert. Containment owns its own
// aircraft lookup independently of this physiology optimization.
private _nativeAltitude = missionNamespace getVariable ["ACM_breathing_altitudeAffectOxygen", false];
private _parent = objectParent _patient;
private _hasPtx = (_patient getVariable ["ACM_breathing_Pneumothorax_State", 0]) > 0
    || {_patient getVariable ["ACM_breathing_TensionPneumothorax_State", false]}
    || {((_patient getVariable ["ACME_ptx_state", [1,0]]) param [1,0]) > 0};
private _needsAirframe = _height >= (missionNamespace getVariable ["ACME_altitude_minMetres", 500])
    || {_nativeAltitude} || {_hasPtx}
    || {(_patient getVariable ["ACM_circulation_Blood_Volume", 6]) < 5.5}
    || {abs (_patient getVariable ["ACME_flightG_resistAdd", 0]) > 0.01}
    || {(_patient getVariable ["ACME_flightG_stress", 0]) > 0.01}
    || {!isNull _parent && {_parent isKindOf "Air"}};
private _airframe = if (_needsAirframe) then {[_patient] call ACME_fnc_flightAirframe} else {objNull};
if (!isNull _airframe && {[_patient, _airframe] call ACME_fnc_flightEnclosed}) then {
    private _cfg = configOf _airframe;
    private _ratio = _airframe getVariable ["ACME_cabinPressureRatio", -1];
    private _cabinHeight = _airframe getVariable ["ACME_cabinAltitude", -1];
    private _ratioValid = _ratio isEqualType 0 && {finite _ratio} && {_ratio >= 0} && {_ratio <= 1};
    private _heightValid = _cabinHeight isEqualType 0 && {finite _cabinHeight} && {_cabinHeight >= 0};
    // Live ratio/height takes precedence over a static config declaration.
    // A live ratio of zero explicitly vents the cabin back to ambient.
    if (!_ratioValid && {!_heightValid}) then {
        if (isNumber (_cfg >> "ACME_cabinPressureRatio")) then {
            _ratio = getNumber (_cfg >> "ACME_cabinPressureRatio");
            _ratioValid = finite _ratio && {_ratio >= 0} && {_ratio <= 1};
        };
        if (!_ratioValid && {isNumber (_cfg >> "ACME_cabinAltitude")}) then {
            _cabinHeight = getNumber (_cfg >> "ACME_cabinAltitude");
            _heightValid = finite _cabinHeight && {_cabinHeight >= 0};
        };
    };
    if (_ratioValid) then {
        _pressure = _ambient max _ratio;
    } else {
        if (_heightValid) then {
            _pressure = _ambient max ([_cabinHeight] call ACME_fnc_pressureAtAltitude);
        };
    };
};
[_height, _ambient, _pressure, [_patient] call ACME_fnc_oxygenSupply, _airframe]
