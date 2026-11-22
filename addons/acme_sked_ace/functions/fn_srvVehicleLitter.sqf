/*
 * Server: a litter with its casualty goes onto the cabin floor of a vehicle, or comes out of it.
 * In: it hangs on the vehicle at a free place with room for it (fn_vehicleLitterSpot.sqf), handles in. The
 * casualty stays strapped in it; he hangs on the vehicle too (fn_reattach.sqf attaches him to what his litter
 * hangs on).
 * Out: it is set on the ground beside the vehicle, on the side of the rescuer who takes it out.
 * Arguments: 0: rescuer (may be null when the vehicle is lost), 1: litter, 2: vehicle, 3: in <BOOL>.
 */
params ["_actor", "_litter", "_vehicle", "_in"];
if (!isServer || {isNull _litter}) exitWith {};
private _patient = _litter getVariable ["acme_sked_patient", objNull];
if (_in) exitWith {
    if (!isNull (_litter getVariable ["acme_sked_inVehicle", objNull]) || {!isNull attachedTo _litter}) exitWith {};
    private _spot = [_vehicle, _litter] call acme_sked_fnc_vehicleLitterSpot;
    if (_spot isEqualTo []) exitWith {};
    _spot params ["_index", "_offset", "_heading"];
    private _held = +(_vehicle getVariable ["acme_sked_litters", []]);
    while {count _held <= _index} do {_held pushBack objNull;};
    _held set [_index, _litter];
    _vehicle setVariable ["acme_sked_litters", _held, true];
    _litter setVariable ["acme_sked_inVehicle", _vehicle, true];
    acme_sked_vehicleLitters pushBackUnique _litter;
    _litter animateSource ["handles", 1, 3];
    _litter attachTo [_vehicle, _offset];
    // (how an attached thing is turned is set where it is local)
    ["acme_sked_turnAttached", [_litter, [sin _heading, cos _heading, 0], [0, 0, 1]], _litter] call CBA_fnc_targetEvent;
    ["in vehicle", _litter, _actor, [typeOf _vehicle, _index, _offset]] call acme_sked_fnc_traceTransport;
    if (!isNull _patient) then {
        [{[_this select 0, "reattach", _this] call acme_sked_fnc_sendLocal}, [_patient, _litter], 0.4] call CBA_fnc_waitAndExecute;
    };
};
_vehicle = _litter getVariable ["acme_sked_inVehicle", objNull];
// where it is set down: beside the vehicle, on the rescuer's side (to the left when nobody takes it out)
private _at = getPosATL _litter;
private _dir = getDir _litter;
if (!isNull _vehicle) then {
    private _side = if (isNull _actor) then {-1} else {[-1, 1] select (((_vehicle worldToModel (ASLToAGL getPosASL _actor)) select 0) > 0)};
    private _own = _vehicle worldToModel (ASLToAGL getPosASL _litter);
    _at = _vehicle modelToWorld [_side * (missionNamespace getVariable ["acme_sked_vehicleLitterOut", 2.9]), _own select 1, 0];
    _dir = getDir _vehicle;
    private _held = +(_vehicle getVariable ["acme_sked_litters", []]);
    {if (_x isEqualTo _litter) then {_held set [_forEachIndex, objNull];};} forEach _held;
    _vehicle setVariable ["acme_sked_litters", _held, true];
};
_litter setVariable ["acme_sked_inVehicle", nil, true];
acme_sked_vehicleLitters = acme_sked_vehicleLitters - [_litter];
detach _litter;
_litter setPosATL [_at select 0, _at select 1, 0];
["ace_common_setDir", [_litter, _dir], _litter] call CBA_fnc_targetEvent;
["ace_common_fixPosition", _litter, _litter] call CBA_fnc_targetEvent;
_litter animateSource ["handles", 0, 3];
["out of vehicle", _litter, _actor, [typeOf _vehicle, getPosATL _litter]] call acme_sked_fnc_traceTransport;
if (!isNull _patient) then {
    [{[_this select 0, "reattach", _this] call acme_sked_fnc_sendLocal}, [_patient, _litter], 0.4] call CBA_fnc_waitAndExecute;
};
