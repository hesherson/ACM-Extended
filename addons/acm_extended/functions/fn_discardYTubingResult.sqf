params [["_patient",objNull,[objNull]],["_requestId","",[""]],["_accepted",false,[false]],["_salvage",[],[[]]],["_part","",[""]],["_iv",true,[true]],["_site",-1,[0]],["_reason","",[""]]];
if (!hasInterface || {isNull ACE_player}) exitWith {};
// Replies can settle only a real pending click, and never into a replacement controlled unit.
private _pending=uiNamespace getVariable ["ACME_yDiscardPending",createHashMap];
private _context=_pending getOrDefault [_requestId,[]];
if (count _context != 2 || {!((_context select 1) isEqualTo _patient)}) exitWith {};
private _provider=_context select 0;
if (isNull _provider || {!local _provider}) exitWith {};
_pending deleteAt _requestId;uiNamespace setVariable ["ACME_yDiscardPending",_pending];
private _seen=uiNamespace getVariable ["ACME_yDiscardSeen",createHashMap]; if (_requestId in _seen) exitWith {};
_seen set [_requestId,true]; private _ks=keys _seen; while {count _ks>32} do {_seen deleteAt (_ks deleteAt 0);}; uiNamespace setVariable ["ACME_yDiscardSeen",_seen];
if (!_accepted) exitWith {if (_reason!="") then {[_reason,2.5,ACE_player,13] call ace_common_fnc_displayTextStructured;};};
private _used=_provider getVariable ["ACME_usedBags",[]]; private _labels=[];
{
    _x params ["_type","_remVol","_accessType","_aSite","_aIv","_bloodType","_origVol",["_freshBloodID",-1]];
    private _name=switch true do {
        case (_type in ["Saline","ACME_SalineY"]):{"Saline"}; case (_type=="PlasmaLyte"):{"Plasma-Lyte A"}; case (_type=="Mannitol"):{"Mannitol"}; case (_type=="HTS"):{"Hypertonic Saline"};
        case (_type in ["Blood","FreshBlood","FBTK"]):{private _bt=if (_bloodType>=0 && {!isNil "ACM_circulation_fnc_convertBloodType"}) then {[_bloodType,1] call ACM_circulation_fnc_convertBloodType}else{""}; format ["Blood%1",[" "+_bt,""] select (_bt=="")]};
        default {_type};
    };
    _used pushBack [format ["used_%1_%2",_requestId,_forEachIndex],_type,_remVol,_accessType,_bloodType,_origVol,_name,_freshBloodID];
    _labels pushBack format ["%1 %2 mL",_name,round _remVol];
} forEach _salvage;
_provider setVariable ["ACME_usedBags",_used,true];
private _msg=if (_labels isEqualTo []) then {"Y tubing discarded."} else {format ["Y tubing discarded. Salvaged: %1.",_labels joinString ", "]};
[_msg,3.5,ACE_player] call ace_common_fnc_displayTextStructured;
missionNamespace setVariable ["ACME_pull_selTrueIndex",-1]; missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionTrueIndex",-1]; missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionSelectionIndex",-1];
if (!isNil "ACM_circulation_fnc_TransfusionMenu_UpdateBagList") then {[false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;}; uiNamespace setVariable ["ACME_usedRowSig","__force__"]; uiNamespace setVariable ["ACME_coolerRowSig","__force__"]; call ACME_fnc_updateTransfusionControls;
