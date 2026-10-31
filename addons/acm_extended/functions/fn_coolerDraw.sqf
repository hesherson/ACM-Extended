/* Source claims serialize carried and shared-box draws before spiking. */
params ["_owner","_bag",["_continuation",[]]];
private _rows=[_owner] call ACME_fnc_coolerRows;
private _sid="";private _index=-1;private _oldest=-1;
{
    private _state=[_x select 1] call ACME_fnc_coolerAdvance;
    private _key=_x select 0;
    {
        if ((_x select 0)==_bag && {(_x select 1)>_oldest} && {!(missionNamespace getVariable ["ACME_bloodSpoilEnabled",true]) || {(_x select 1)<(missionNamespace getVariable ["ACME_bloodLooseSpoilTime",1800])}}) then {
            _sid=_key;_index=_forEachIndex;_oldest=_x select 1;
        };
    } forEach (_state select 2);
} forEach _rows;
if (_sid!="") exitWith {
    [_owner,_sid,{
        params ["_owner","_sid","_state","_args"];
        _args params ["_bag","_index"];
        private _entries=+(_state select 2);
        if (_index>=count _entries || {((_entries select _index) select 0)!=_bag}) exitWith {[]};
        private _entry=_entries select _index;
        if (missionNamespace getVariable ["ACME_bloodSpoilEnabled",true] && {(_entry select 1)>=(missionNamespace getVariable ["ACME_bloodLooseSpoilTime",1800])}) exitWith {[]};
        if !([_owner,_entry,true] call ACME_fnc_coolerGiveBag) exitWith {[]};
        _entries deleteAt _index;_state set [2,_entries];
        [false,_state]
    },[_bag,_index],_continuation] call ACME_fnc_coolerMutate
};
private _boxes=nearestObjects [_owner,["ACME_BloodCoolerBox_CSWB1U","ACME_BloodCoolerBox_CSWB2U","ACME_BloodCoolerBox_CSWB4U"],4.5];
private _hit=_boxes findIf {!(_x getVariable ["ACME_coolerRetired",false]) && {!(_x getVariable ["ACME_coolerPacking",false])} && {_bag in itemCargo _x}};
if (_hit<0) exitWith {false};
["draw",_owner,_bag,_boxes select _hit,_continuation] call ACME_fnc_coolerBoxRequest
