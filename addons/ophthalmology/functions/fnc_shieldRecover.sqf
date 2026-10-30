#include "..\script_component.hpp"
/* Expired orphan scopes retire as spent; guessing a refund could duplicate fitted equipment. */
params ["_patient"];
if (isNull _patient || {!local _patient}) exitWith {};
private _incoming = _patient getVariable [QGVAR(shieldIncoming),createHashMap];
{
    private _request = _incoming get _x;
    if (count _request == 12 && {serverTime > (_request select 7)+30}) then {
        ["retire",_request] call FUNC(shieldCommit);
    };
} forEach +(keys _incoming);
private _terminal = _patient getVariable [QGVAR(shieldTerminal),createHashMap];
{
    private _entry = _terminal get _x;
    if (serverTime > ((_entry select 0) select 7)+30
        && {(_entry select 1) in ["applied","refunded"] || {count _entry == 3 && {_entry select 2}}}) then {_terminal deleteAt _x;};
} forEach +(keys _terminal);
_patient setVariable [QGVAR(shieldTerminal),_terminal,true];
