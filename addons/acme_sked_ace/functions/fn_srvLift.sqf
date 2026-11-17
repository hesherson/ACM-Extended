/*
 * Server: lift the SKED. It is attached to the lead rescuer at carry height, square to them (head end the
 * way they face), with its mass made negligible as ACE does for dragging; the other rescuers are attached
 * to the lead at their handles and follow; the casualty is re-attached to the lead.
 * Arguments: 0: lead rescuer, 1: SKED.
 */
params ["_lead", "_litter"];
if (!isServer || {isNull _litter} || {_litter getVariable ["acme_sked_lifted", false]} || {!isNull attachedTo _litter}
    || {!isNull (_litter getVariable ["ace_common_owner", objNull])}) exitWith {};
private _slots = getArray (configOf _litter >> "acmeLitterHandles");
private _bearers = _litter getVariable ["acme_sked_bearers", []];
private _i = _bearers find _lead;
if (_i < 0 || {!([_lead] call acme_sked_fnc_canLift)}) exitWith {};
private _h = _litter selectionPosition [_slots select _i, "Memory"];
private _hold = _lead vectorWorldToModel (_litter vectorModelToWorld _h);
private _facing = _lead vectorWorldToModel (vectorDir _litter);
_facing set [2, 0];
private _z = missionNamespace getVariable ["acme_sked_liftHeight", 0.55];
private _mass = getMass _litter;
if (_mass <= 1) then {_mass = _litter getVariable ["ace_dragging_originalMass", 7]};
_litter setVariable ["acme_sked_mass", _mass, true];
["ace_common_setMass", [_litter, 1e-12]] call CBA_fnc_globalEvent;
_litter attachTo [_lead, [-(_hold select 0), -(_hold select 1), _z]];
_litter setVectorDirAndUp [vectorNormalized _facing, [0, 0, 1]];
_litter setVariable ["acme_sked_lifted", true, true];
_litter setVariable ["acme_sked_lead", _lead, true];
["lifted", _litter, _lead, _bearers] call acme_sked_fnc_traceTransport;
[_lead, "bearerLocal", [_lead, _litter, "lead"]] call acme_sked_fnc_sendLocal;
private _patient = _litter getVariable ["acme_sked_patient", objNull];
if (!isNull _patient) then {
    [{[_this select 0, "reattach", _this] call acme_sked_fnc_sendLocal}, [_patient, _litter], 0.4] call CBA_fnc_waitAndExecute;
};
