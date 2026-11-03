params ["_box"];
if (isNull _box || {ACE_player distance _box>4}) exitWith {};
uiNamespace setVariable ["ACME_CLR_Box",_box];
uiNamespace setVariable ["ACME_CLR_Id","world"];
createDialog "ACME_CoolerManager_Dialog";
[ACE_player,_box,true] remoteExecCall ["ACME_fnc_equipmentCoolerLease",2];
