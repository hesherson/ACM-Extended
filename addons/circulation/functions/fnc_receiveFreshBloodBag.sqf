#include "..\script_component.hpp"
/* One immutable grant produces one product. ACE already owns ground fallback;
 * its false inventory flag is not permission to add a second ground bag. */
if (canSuspend) exitWith {isNil {_this call FUNC(receiveFreshBloodBag);};};
if !(_this isEqualType [] && {count _this==9}) exitWith {};
params ["_medic","_volume","_id","_entry","_request","_facts","_expectedOwner","_nonce","_attempt"];
if (([0,1,2,3,4,5,6,7,8] findIf {isNil {_this select _x}})>=0) exitWith {};
if !(_medic isEqualType objNull && {_volume isEqualType 0} && {_id isEqualType 0} && {finite _id}
    && {_entry isEqualType []} && {_request isEqualType ""} && {_facts isEqualType []}
    && {_expectedOwner isEqualType 0} && {finite _expectedOwner} && {_nonce isEqualType ""}
    && {_attempt isEqualType 0} && {finite _attempt}) exitWith {};
if (isNull _medic || {_request==""} || {!(_volume in [250,500])}
    || {_id<0} || {_id>512} || {_id!=floor _id} || {count _entry!=5} || {count _facts!=4}) exitWith {};
if ((_entry select [2,3]) isNotEqualTo [_facts select 3,_facts select 1,_facts select 2]) exitWith {};
private _received=_medic getVariable [QGVAR(freshBloodReceived),createHashMap];
private _past=_received getOrDefault [_request,[]];
private _ack={
    [QGVAR(freshBloodGrantAck),[_medic,_request,_id,_facts,clientOwner,_nonce,_attempt]] call CBA_fnc_serverEvent;
};
if (_past isNotEqualTo []) exitWith {if (_past isEqualTo [_volume,_id,_facts,"delivered"]) then {call _ack;};};
if (!local _medic || {clientOwner!=_expectedOwner} || {_nonce==""}
    || {(missionNamespace getVariable ["ACME_syringeDeliveryMachineNonce",""])!=_nonce}) exitWith {};
private _private=missionNamespace getVariable [QGVAR(FreshBloodGrantDecisions),createHashMap];
private _privateKey=format ["%1:%2",_request,_attempt];
private _fingerprint=[_medic,_volume,_id,+_facts,_nonce];
private _decision=_private getOrDefault [_privateKey,[]];
if (_decision isNotEqualTo [] && {(_decision select 0) isNotEqualTo _fingerprint}) exitWith {};
if (_decision isNotEqualTo [] && {(_decision select 1)!="unplaced"}) exitWith {
    if ((_decision select 1)=="delivered") then {call _ack;};
};
_private set [_privateKey,[_fingerprint,"applying"]];missionNamespace setVariable [QGVAR(FreshBloodGrantDecisions),_private];
private _placed=false;
private _uncertain=false;
if (_id==0) then {
    private _used=+(_medic getVariable ["ACME_usedBags",[]]);
    private _uid="used_fbtk:"+_request;
    private _product=[_uid,"FreshBlood",_volume,0,_facts select 3,_volume,"Fresh donor blood",-1,+_facts];
    private _at=_used findIf {(_x param [0,""])==_uid};
    if (_at<0) then {_used pushBack _product;_medic setVariable ["ACME_usedBags",_used,true];};
    _placed=_product in (_medic getVariable ["ACME_usedBags",[]]);
    _uncertain=!_placed;
} else {
    private _freshList=missionNamespace getVariable [QGVAR(FreshBloodList),createHashMap];
    _freshList set [_id,+_entry];missionNamespace setVariable [QGVAR(FreshBloodList),_freshList,false];
    private _className=format ["%1_%2",(["FreshBlood",_volume] call FUNC(formatFluidBagName)),_id];
    private _before={_x==_className} count ((uniformItems _medic)+(vestItems _medic)+(backpackItems _medic));
    private _near=nearestObject [_medic,"WeaponHolder"];
    private _groundBefore=if (isNull _near) then {0} else {{_x==_className} count itemCargo _near};
    private _result=[_medic,_className] call ACEFUNC(common,addToInventory);
    private _after={_x==_className} count ((uniformItems _medic)+(vestItems _medic)+(backpackItems _medic));
    _placed=_after==_before+1;
    private _knownUnplaced=false;
    if (!_placed && {!isNil "_result"} && {_result isEqualType []} && {count _result==2}
        && {(_result select 0) isEqualType true} && {(_result select 1) isEqualType objNull}) then {
        private _holder=_result select 1;_knownUnplaced=_after==_before;
        if (!isNull _holder && {_holder isNotEqualTo _medic}) then {
            private _expected=if (_holder isEqualTo _near) then {_groundBefore+1} else {1};
            private _groundAfter={_x==_className} count itemCargo _holder;
            _placed=_groundAfter==_expected;_knownUnplaced=_knownUnplaced && {_groundAfter==_expected-1};
        };
    };
    _uncertain=!_placed && {!_knownUnplaced};
    if (_placed) then {[QGVAR(updateFreshBloodBagName),[_volume,_id,_entry select 2]] call CBA_fnc_localEvent;};
};
if (!_placed) exitWith {
    _private set [_privateKey,[_fingerprint,["unplaced","uncertain"] select _uncertain]];
    missionNamespace setVariable [QGVAR(FreshBloodGrantDecisions),_private];
    if (_uncertain) then {
        _received set [_request,[_volume,_id,+_facts,"uncertain"]];_medic setVariable [QGVAR(freshBloodReceived),_received,true];
        diag_log "[ACME FRESH BLOOD] Unverifiable native grant; the funded donor product remains reserved for recovery.";
    };
};
_private set [_privateKey,[_fingerprint,"delivered"]];missionNamespace setVariable [QGVAR(FreshBloodGrantDecisions),_private];
_received set [_request,[_volume,_id,+_facts,"delivered"]];_medic setVariable [QGVAR(freshBloodReceived),_received,true];
call _ack;
if (hasInterface && {_medic isEqualTo ACE_player} && {_id==0}) then {
    ["Donor ID space is full. Fresh blood was retained in the used-bag inventory.",3] call ACEFUNC(common,displayTextStructured);
};
