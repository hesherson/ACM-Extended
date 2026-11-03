params ["_device"];
private _actor=call ACME_fnc_controlledProvider;
[_actor,_device getVariable ["acme_tempusls_pat",objNull],"ls","pickup",false,[],_device] remoteExecCall ["ACME_fnc_equipmentRequest",2];
