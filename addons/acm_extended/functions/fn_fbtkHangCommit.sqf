/* One owner-local non-suspending transaction. Never guess an existing carrier
   by its volume, and never charge a second administration set for an FBTK. */
params ["_p","_m","_part","_site","_class","_token","_epoch","_deadline"];
if (isNull _p || {!local _p} || {isNull _m}) exitWith {false};
if !(_token isEqualType "" && {_token!=""} && {count _token<=128}
    && {_deadline isEqualType 0} && {finite _deadline}
    && {_epoch isEqualType 0} && {_part isEqualType ""} && {_site in [0,1,2]}
    && {_class in ["ACM_FieldBloodTransfusionKit_250","ACM_FieldBloodTransfusionKit_500"]}) exitWith {false};
private _fingerprint=[_m,_part,_site,_class,_epoch,_deadline];
private _cache=+(_p getVariable ["ACME_fbtkReceipts",[]]);
_cache=_cache select {(_x param [4,0])>=serverTime};
private _found=_cache findIf {(_x select 0)==_token};
if (_found>=0) exitWith {
    private _old=_cache select _found;
    if ((_old select 1) isEqualTo _fingerprint) then {[_m,"fbtkHangReply",[_m,_p,_token,_old select 2,_old select 3]] call ACME_fnc_ownerDispatch;};
    _old select 2
};
if (count _cache>=128 || {_deadline>serverTime+12}) exitWith {
    [_m,"fbtkHangReply",[_m,_p,_token,false,"Please retry the collection request."]] call ACME_fnc_ownerDispatch;false
};
private _ok=false;private _message="The request expired.";
if (count _cache<128 && {_deadline>=serverTime} && {_deadline<=serverTime+12}
    && {_epoch==([_p] call ACME_fnc_clinicalEpoch)} && {alive _m}
    && {!(_m getVariable ["ACE_isUnconscious",false])}
    && {([_m,_p] call ACME_fnc_patientInteractionDistance)<=3}
    && {(objectParent _m) isEqualTo (objectParent _p)}) then {
    private _reason=[_p,_part,true,_site] call ACME_fnc_preparedAttachBlockReason;
    _message=if (_reason=="line-occupied") then {"There is already a bag on this line."} else {"Select a free IV line."};
    if (_reason=="") then {isNil {
        private _before=+(_p getVariable ["ACM_circulation_IV_Bags",createHashMap]);
        private _oldBags=+(_before getOrDefault [_part,[]]);
        private _uids=_oldBags apply {_x param [8,""]};
        private _capacity=if (_class=="ACM_FieldBloodTransfusionKit_250") then {250} else {500};
        private _pi=ACME_infusion_bodyParts find _part;
        private _type=[_p,true,_pi,_site] call ACM_circulation_fnc_getAccessType;
        [_p,_part,format ["FieldBloodTransfusionKit_%1",_capacity],_type,true,_site,false,true] call ace_medical_treatment_fnc_ivBagLocal;
        private _after=_p getVariable ["ACM_circulation_IV_Bags",createHashMap];
        private _rows=_after getOrDefault [_part,[]];
        private _new=_rows select {!((_x param [8,""]) in _uids)};
        _ok=count _new==1 && {((_new select 0) param [0,""])=="FBTK"}
            && {((_new select 0) param [1,-1])==0} && {((_new select 0) param [6,0])==_capacity}
            && {((_new select 0) param [3,-1])==_site} && {(_new select 0) param [4,false]}
            && {((_new select 0) param [8,""])!=""} && {count _rows==count _oldBags+1};
        if (_ok) then {
            [_p,_after,true] call ACME_fnc_ivBagsCommit;
            [_p,_part,true,_site] call ACME_fnc_resumeSiteFlow;
            [_p,_part] call ACM_circulation_fnc_updateActiveFluidBags;
            if ((_p getVariable ["ACM_circulation_BloodType",-1])<0) then {[_p] call ACM_circulation_fnc_generateBloodType;};
            [_p,"activity","%1 attached a field blood transfusion kit",[[_m,false,true] call ace_common_fnc_getName]] call ace_medical_treatment_fnc_addToLog;
            _message="";
        } else {
            _after set [_part,_oldBags];[_p,_after,true] call ACME_fnc_ivBagsCommit;
            _message="The collection bag could not be attached.";
        };
        true
    };};
};
_cache pushBack [_token,_fingerprint,_ok,_message,_deadline+30];
[_p,"ACME_fbtkReceipts",_cache] call ACME_fnc_setVarNet;
[_m,"fbtkHangReply",[_m,_p,_token,_ok,_message]] call ACME_fnc_ownerDispatch;
_ok
