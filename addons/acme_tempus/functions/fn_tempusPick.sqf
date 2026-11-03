params ["_device"];
private _actor=call ACME_fnc_controlledProvider;
[_actor,_device getVariable ["acme_tempus_pat",objNull],"pro","pickup",false,[],_device] remoteExecCall ["ACME_fnc_equipmentRequest",2];
