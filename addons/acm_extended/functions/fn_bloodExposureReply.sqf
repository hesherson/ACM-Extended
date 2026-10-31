/* A late/replayed exposure reply cannot consume a new source bag or cooler. */
params ["_owner","_request","_bag","_warm","_sampled"];
if (isNull _owner || {!local _owner}) exitWith {};
private _seeds=_owner getVariable ["ACME_bloodSeedPending",createHashMap];
private _seed=_seeds getOrDefault [str _request,[]];
if (_seed isNotEqualTo []) exitWith {
    if ((_seed select 0)==_bag && {_warm>=0}) then {_seeds deleteAt (str _request);_owner setVariable ["ACME_bloodSeedPending",_seeds,true];};
};
private _pending=missionNamespace getVariable ["ACME_bloodExposurePending",createHashMap];
private _row=_pending getOrDefault [str _request,[]];
if (count _row!=8 || {(_row select 0) isNotEqualTo _owner} || {(_row select 2)!=_bag}) exitWith {};
_pending deleteAt (str _request);missionNamespace setVariable ["ACME_bloodExposurePending",_pending];
if ((_row select 4)!=(_owner getVariable ["ACME_equipmentKitEpoch",0]) || {(_row select 5)!=(_owner getVariable ["ACME_providerLocalityEpoch",0])} || {serverTime-(_row select 3)>30} || {!alive _owner} || {!(_warm isEqualType 0)} || {!finite _warm} || {_warm<0}) exitWith {};
[_owner,_row select 1,{
    params ["_owner","_sid","_state","_args"];
    _args params ["_bag","_warm","_sampled","_kit","_locality"];
    if (!local _owner || {!alive _owner} || {_kit!=(_owner getVariable ["ACME_equipmentKitEpoch",0])} || {_locality!=(_owner getVariable ["ACME_providerLocalityEpoch",0])}) exitWith {[]};
    private _items=(uniformItems _owner)+(vestItems _owner)+(backpackItems _owner);
    private _before={_x==_bag} count _items;
    if (_before<1) exitWith {[]};
    private _capacity=getNumber(configFile >> "CfgWeapons" >> (_state select 0) >> "ACME_coolerCapacityMl");
    private _entries=+(_state select 2);
    private _used=0;{_used=_used+([_x select 0] call ACME_fnc_coolerBagVolume);} forEach _entries;
    if (_used+([_bag] call ACME_fnc_coolerBagVolume)>_capacity) exitWith {[]};
    _warm=_warm+((serverTime-_sampled) max 0);
    if (_warm>=(missionNamespace getVariable ["ACME_bloodLooseSpoilTime",1800]) && {missionNamespace getVariable ["ACME_bloodSpoilEnabled",true]}) exitWith {[]};
    _owner removeItem _bag;
    if (({_x==_bag} count ((uniformItems _owner)+(vestItems _owner)+(backpackItems _owner)))!=_before-1) exitWith {[]};
    _entries pushBack [_bag,_warm];
    _state set [2,_entries];
    [false,_state]
},[_bag,_warm,_sampled,_row select 4,_row select 5]] call ACME_fnc_coolerMutate;
