/* Dispatch only from the authoritative server, on the unit's current owner. */
params [["_unit", objNull, [objNull]], ["_action", "", [""]], ["_args", [], [[]]]];
if (if (isRemoteExecuted) then {remoteExecutedOwner != 2} else {!isServer}) exitWith {};
if (isNull _unit || {!local _unit} || {(_args param [0, objNull]) isNotEqualTo _unit}) exitWith {};
switch (_action) do {
    case "attachLocal": {_args call acme_sked_fnc_attachLocal;};
    case "reattach": {_args call acme_sked_fnc_reattach;};
    case "releaseLocal": {_args call acme_sked_fnc_releaseLocal;};
    case "hpmkSwap": {_args call acme_sked_fnc_hpmkSwap;};
    case "bearerLocal": {_args call acme_sked_fnc_bearerLocal;};
    case "bearerRelease": {_args call acme_sked_fnc_bearerRelease;};
    case "loadLocal": {_args call acme_sked_fnc_loadLocal;};
};
