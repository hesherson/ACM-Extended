/*
 * Server: set the SKED down where it is, flat on the ground (ACE fixPosition), mass back; the rescuers
 * stay on their handles at the SKED; the casualty goes back onto it. The follow-up waits 0.4 s for the SKED
 * to settle, and does nothing if it has been lifted or dragged again in between.
 * Arguments: 0: SKED.
 */
params ["_litter"];
if (!isServer || {isNull _litter} || {!(_litter getVariable ["acme_sked_lifted", false])}) exitWith {};
private _pos = getPosATL _litter;
private _dir = getDir _litter;
detach _litter;
_litter setPosATL [_pos select 0, _pos select 1, 0];
["ace_common_setDir", [_litter, _dir], _litter] call CBA_fnc_targetEvent;
["ace_common_fixPosition", _litter, _litter] call CBA_fnc_targetEvent;
["ace_common_setMass", [_litter, _litter getVariable ["acme_sked_mass", 7]]] call CBA_fnc_globalEvent;
_litter setVariable ["acme_sked_lifted", false, true];
_litter setVariable ["acme_sked_lead", nil, true];
[{
    params ["_litter"];
    if (isNull _litter || {_litter getVariable ["acme_sked_lifted", false]} || {!isNull attachedTo _litter}) exitWith {};
    private _slots = ["handle_lh", "handle_rh", "handle_lf", "handle_rf"];
    {
        if (!isNull _x) then {
            private _h = _litter selectionPosition (_slots select _forEachIndex);
            [_x, "bearerLocal", [_x, _litter, "hold", _litter, [_h select 0, _h select 1, 0]]] call acme_sked_fnc_sendLocal;
        };
    } forEach (_litter getVariable ["acme_sked_bearers", []]);
    private _patient = _litter getVariable ["acme_sked_patient", objNull];
    if (!isNull _patient) then {
        [_patient, "reattach", [_patient, _litter]] call acme_sked_fnc_sendLocal;
    };
}, [_litter], 0.4] call CBA_fnc_waitAndExecute;
