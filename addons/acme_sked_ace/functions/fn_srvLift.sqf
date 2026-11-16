/*
 * Server: lift the SKED. It is attached to the lead rescuer at carry height, square to them (head end the
 * way they face), with its mass made negligible as ACE does for dragging; the other rescuers are attached
 * to the lead at their handles and follow; the casualty is re-attached to the lead.
 * Arguments: 0: lead rescuer, 1: SKED.
 */
params ["_lead", "_litter"];
if (!isServer || {isNull _litter} || {_litter getVariable ["acme_sked_lifted", false]} || {!isNull attachedTo _litter}
    || {!isNull (_litter getVariable ["ace_common_owner", objNull])}) exitWith {};
private _slots = ["handle_lh", "handle_rh", "handle_lf", "handle_rf"];
private _bearers = _litter getVariable ["acme_sked_bearers", []];
private _i = _bearers find _lead;
if (_i < 0 || {!((attachedTo _lead) isEqualTo _litter)}) exitWith {};
if (({!isNull _x && {alive _x} && {(attachedTo _x) isEqualTo _litter}} count _bearers) < (missionNamespace getVariable ["acme_sked_bearersRequired", 2])) exitWith {};
private _h = _litter selectionPosition (_slots select _i);
private _z = missionNamespace getVariable ["acme_sked_liftHeight", 0.55];
private _mass = getMass _litter;
if (_mass <= 1) then {_mass = _litter getVariable ["ace_dragging_originalMass", 7]};
_litter setVariable ["acme_sked_mass", _mass, true];
detach _lead;
["ace_common_setMass", [_litter, 1e-12]] call CBA_fnc_globalEvent;
_litter attachTo [_lead, [-(_h select 0), -(_h select 1), _z]];
["ace_common_setDir", [_litter, 0], _litter] call CBA_fnc_targetEvent;
_litter setVariable ["acme_sked_lifted", true, true];
_litter setVariable ["acme_sked_lead", _lead, true];
[_lead, "bearerLocal", [_lead, _litter, "lead", objNull, []]] call acme_sked_fnc_sendLocal;
{
    if (!isNull _x && {!(_x isEqualTo _lead)}) then {
        private _hi = _litter selectionPosition (_slots select _forEachIndex);
        [_x, "bearerLocal", [_x, _litter, "follow", _lead, [(_hi select 0) - (_h select 0), (_hi select 1) - (_h select 1), 0]]] call acme_sked_fnc_sendLocal;
    };
} forEach _bearers;
private _patient = _litter getVariable ["acme_sked_patient", objNull];
if (!isNull _patient) then {
    [{[_this select 0, "reattach", _this] call acme_sked_fnc_sendLocal}, [_patient, _litter], 0.4] call CBA_fnc_waitAndExecute;
};
