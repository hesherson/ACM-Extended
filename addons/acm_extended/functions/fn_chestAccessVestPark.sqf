// Park the removed chest-access carrier once to the left of the casualty's head.
// The first call captures a fixed world-space target on the prop. Later patient movement/rolls never drag it.
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!local _patient}) exitWith {};

private _prop = _patient getVariable ["ACME_chestAccess_vestProp", objNull];
if (isNull _prop) exitWith {};

// While Semi-Fowler is borrowing this manually removed carrier, the fixed chest-access watchdog must not yank the
// prop back to the ground park. Re-seat the same object behind the upper back instead.
if ((_patient getVariable ["ACME_headElev_manualCarrierBorrowed", false])
    && {_patient getVariable ["ACME_headElevated", false]}
    && {!(_patient getVariable ["ACME_headElev_Suspended", false])}) exitWith {
    _prop setVariable ["ACME_chestFixedPark", nil, false];
    [_patient] call ACME_fnc_headElevPropApply;
};

private _park = _prop getVariable ["ACME_chestFixedPark", []];
if !(_park isEqualType [] && {count _park == 3}) then {
    _park = [_patient] call ACME_fnc_carrierParkTarget;
    _prop setVariable ["ACME_chestFixedPark", +_park, false];
};

_park params ["_pos", "_axis", "_up"];
detach _prop;
_prop disableCollisionWith _patient;
_patient disableCollisionWith _prop;
[_prop, _pos, _axis, _up, missionNamespace getVariable ["ACME_headElev_propEaseTime", 0.24]] call ACME_fnc_propEaseTo;

private _cargo = [_patient] call ACME_fnc_carrierInventoryGet;
if (!isNull _cargo && {(_cargo getVariable ["ACME_carrierSavedVar", ""]) == "ACME_chestAccess_vestLoadout"}) then {
    if (_cargo distance _pos > 0.02) then {_cargo setPosATL _pos;};
};
