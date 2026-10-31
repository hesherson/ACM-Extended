// the true altitude for an object, corrected for the sea-level datum of the map.
// every piece of flight physiology should ask this rather than reading getPosASL directly, so a terrain whose base
// plate sits above sea level cannot make a casualty on the ground look like a casualty at altitude. see
// fn_altitudedatum for how the offset is worked out and how to override it.
// call it as [_obj] call ACME_fnc_altitudeTrue, which returns the meters above the intended sea level of the map,
// never below 0.
// it is clamped at 0 because nothing here models being below sea level: a casualty on a valley floor slightly under
// the datum is at sea level as far as alveolar oxygen is concerned, and a negative would invert the barometric
// curve.

params ["_obj"];
if (isNil "_obj" || {isNull _obj}) exitWith { 0 };

private _datum = call ACME_fnc_altitudeDatum;
if !(_datum isEqualType 0 && {finite _datum}) then {_datum = 0;};
private _position = getPosASL _obj;
private _height = _position param [2, 0];
if !(_height isEqualType 0 && {finite _height}) exitWith {0};
(_height - _datum) max 0
