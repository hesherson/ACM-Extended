// Park carrier props to the left of the casualty's head at a fixed world-space point for this chest workspace.
// Once captured, the target never follows later patient rolls or body motion.
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!local _patient}) exitWith {};

private _props = [];
private _chestProp = _patient getVariable ["ACME_CS_vestProp", objNull];
if (!isNull _chestProp) then {_props pushBackUnique _chestProp;};

private _headProp = _patient getVariable ["ACME_headElev_propObj", objNull];
if ((_patient getVariable ["ACME_CS_ProcedureActive", false]) && {!isNull _headProp}) then {
    _props pushBackUnique _headProp;
};
if (_props isEqualTo []) exitWith {};

private _defaultPark = [_patient] call ACME_fnc_carrierParkTarget;

{
    private _prop = _x;
    private _park = _prop getVariable ["ACME_chestFixedPark", []];
    if !(_park isEqualType [] && {count _park == 3}) then {
        _park = +_defaultPark;
        _prop setVariable ["ACME_chestFixedPark", +_park, false];
    };
    _park params ["_pos", "_dir", "_up"];
    detach _prop;
    _prop disableCollisionWith _patient;
    _patient disableCollisionWith _prop;
    [_prop, _pos, _dir, _up, missionNamespace getVariable ["ACME_headElev_propEaseTime", 0.24]] call ACME_fnc_propEaseTo;
} forEach _props;

private _cargo = [_patient] call ACME_fnc_carrierInventoryGet;
if (!isNull _cargo && {(_cargo getVariable ["ACME_carrierSavedVar", ""]) == "ACME_CS_vestLoadout"}) then {
    private _park = _chestProp getVariable ["ACME_chestFixedPark", _defaultPark];
    if (_cargo distance (_park select 0) > 0.02) then {_cargo setPosATL (_park select 0);};
};
