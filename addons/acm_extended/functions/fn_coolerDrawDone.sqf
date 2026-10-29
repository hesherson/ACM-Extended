/* Resume the exact menu action only while the medic is still on that access. */
params ["_ok","_args"];
if (!_ok) exitWith {};
_args params ["_class","_action","_context"];
private _target=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull];
private _current=[missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull],missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""],missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true],missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1],if (isNull _target) then {-1} else {[_target] call ACME_fnc_clinicalEpoch},missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_Inventory",0]];
private _display=findDisplay 86000;
if (isNull _display || {_current isNotEqualTo (_context select [0,6])} || {uiNamespace getVariable ["ACME_preparedListMode",false]} || {!((missionNamespace getVariable ["ACME_piggybackPending",[]]) isEqualTo [])}) exitWith {};
if (count _context > 6) then {
    private _line = call ACME_fnc_getSelectedIVLineContext;
    if (_line isEqualTo [] || {(_line select 4) != (_context select 6)}) then {_current = [];};
};
if (_current isEqualTo []) exitWith {};
private _right=_display displayCtrl 86005;
private _selection=lbCurSel _right;
if (_selection<0) exitWith {};
private _data=(_right lbData _selection) splitString "|";
if ((_data param [0,""])!=_class || {(_data param [1,""])!=_action} || {!((_data param [2,""]) in ["","COOLER"])}) exitWith {};
[[_class,_action,_context]] call ACME_fnc_transfusionSpikeOrAdd;
