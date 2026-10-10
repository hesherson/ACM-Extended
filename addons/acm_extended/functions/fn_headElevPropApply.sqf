// re-seat and orient the plate-carrier bolster prop on the upper back of the patient, at spine3, live.
// it reads the tunable offset and the pitch, yaw and roll, so the head-elevation tuner sliders move the carrier in
// real time, and the head-elevation start applies the saved placement when it first wedges the carrier. it is a
// no-op if the prop is not present, such as when the casualty had a backpack instead.
// the prop is a createSimpleObject of the world model of the vest: static and non-simulated, so it renders on
// creation and is pinned by attachto. re-calling attachto on an already-attached object simply updates the offset
// in place, so there is no detach and no vanish. there is no simulation toggling, because a simple object is not
// simulated, so it never falls or drifts.
// _this is [_patient].
params [["_patient", objNull]];
if (isNull _patient) then { _patient = missionNamespace getVariable ["ACME_headElev_TunePatient", objNull]; };
if (isNull _patient) exitWith {};
private _prop = _patient getVariable ["ACME_headElev_propObj", objNull];
if (isNull _prop) exitWith {};

private _off   = missionNamespace getVariable ["ACME_headElev_vestPropOffset", [-0.0624309, 0.327775, -0.262297]];
private _pitch = missionNamespace getVariable ["ACME_headElev_vestPropPitch", -180];
private _yaw   = missionNamespace getVariable ["ACME_headElev_vestPropYaw", -9.52483];
private _roll  = missionNamespace getVariable ["ACME_headElev_vestPropRoll", 0];

_prop attachTo [_patient, _off, "Spine3"];  // re-attach = update offset in place (no detach -> no vanish)

private _y = ((getDir _patient) + _yaw) * (pi / 180);
private _p = _pitch * (pi / 180);
private _r = _roll  * (pi / 180);
private _fwd   = [sin _y, cos _y, 0];
private _right = [cos _y, -(sin _y), 0];
private _up    = [0, 0, 1];
private _fwd2 = (_fwd vectorMultiply (cos _p)) vectorAdd (_up  vectorMultiply (sin _p));
private _up2  = (_up  vectorMultiply (cos _p)) vectorAdd (_fwd vectorMultiply (-(sin _p)));
private _up3  = (_up2 vectorMultiply (cos _r)) vectorAdd (_right vectorMultiply (sin _r));
_prop setVectorDirAndUp [_fwd2, _up3];

private _cargo = [_patient] call ACME_fnc_carrierInventoryGet;
if (local _patient && {!isNull _cargo}) then {_cargo setPosATL (getPosATL _prop);};
