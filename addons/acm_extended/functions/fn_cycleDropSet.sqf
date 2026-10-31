// The displayed valve state includes the latest input awaiting its owner.
call ACME_fnc_updateClampDialog;
private _dropSets = missionNamespace getVariable ["ACME_infusion_dropSets", [10,15,20,60]];
if (_dropSets isEqualTo []) exitWith {false};
private _dropSet = uiNamespace getVariable ["ACME_RollerClamp_DropSet", missionNamespace getVariable ["ACME_infusion_defaultDropSet",20]];
private _index = _dropSets find _dropSet;
_index = if (_index < 0) then {0} else {(_index + 1) mod count _dropSets};
private _next = _dropSets select _index;
uiNamespace setVariable ["ACME_RollerClamp_DropSet",_next];
uiNamespace setVariable ["ACME_RollerClamp_Flash",[format ["Drop set: %1 gtt/mL",round _next],CBA_missionTime + 1.25]];
[uiNamespace getVariable ["ACME_RollerClamp_Position",1],true,_next] call ACME_fnc_setClampPosition;
