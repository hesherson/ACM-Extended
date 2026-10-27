/* Materialize one unit only after native readback proves placement. */
params ["_owner","_entry",["_manual",true]];
_entry params ["_class","_warm"];
if (isNull _owner || {!local _owner}) exitWith {false};
if (_warm >= (missionNamespace getVariable ["ACME_bloodLooseSpoilTime",1800]) && {missionNamespace getVariable ["ACME_bloodSpoilEnabled",true]}) then {_class="ACME_SpoiledBlood";};
if (_class!="ACME_SpoiledBlood" && {count (_owner getVariable ["ACME_bloodSeedPending",createHashMap])>=128}) exitWith {false};
private _before = { _x == _class } count ((uniformItems _owner)+(vestItems _owner)+(backpackItems _owner));
if !(_owner canAdd _class) exitWith {false};
missionNamespace setVariable ["ACME_coolerAutoStoreSuppressUntil",diag_tickTime+5];
missionNamespace setVariable ["ACME_coolerAutoStoreBusy",true];
_owner addItem _class;
missionNamespace setVariable ["ACME_coolerAutoStoreBusy",false];
private _after = { _x == _class } count ((uniformItems _owner)+(vestItems _owner)+(backpackItems _owner));
if (_after != _before+1) exitWith {false};
if (_class != "ACME_SpoiledBlood") then {
    private _serial=(missionNamespace getVariable ["ACME_bloodExposureSerial",0])+1;
    missionNamespace setVariable ["ACME_bloodExposureSerial",_serial];
    private _request=[clientOwner,_serial];
    private _seeds=_owner getVariable ["ACME_bloodSeedPending",createHashMap];
    _seeds set [str _request,[_class,_request,_warm,serverTime,serverTime,_after]];
    _owner setVariable ["ACME_bloodSeedPending",_seeds,true];
    ["ACME_bloodExposureRequest",["seed",_owner,_class,_request,_warm,serverTime,_after]] call CBA_fnc_serverEvent;
};
if (_manual) then {missionNamespace setVariable ["ACME_coolerManualOut",(missionNamespace getVariable ["ACME_coolerManualOut",0])+1];};
true
