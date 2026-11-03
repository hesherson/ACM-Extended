private _box=uiNamespace getVariable ["ACME_CLR_Box",objNull];
if (!isNull _box) then {[ACE_player,_box,false] remoteExecCall ["ACME_fnc_equipmentCoolerLease",2];};
uiNamespace setVariable ["ACME_CLR_Box",objNull];
