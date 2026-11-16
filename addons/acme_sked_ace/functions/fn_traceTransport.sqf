if !(missionNamespace getVariable ["acme_sked_debug", false]) exitWith {};
params ["_event", "_litter", "_unit", ["_details", []]];
diag_log format ["[ACME Transport] %1 t=%2 server=%3 client=%4 litter=%5:%6 unit=%7 owner=%8 %9",
    _event, CBA_missionTime, isServer, clientOwner, typeOf _litter, netId _litter, netId _unit, owner _unit, _details];
