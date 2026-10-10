/* B233 patient-owner teardown of the external tubing, preserving the IV and
   exact remaining bag/dose custody. Disconnected bags require explicit rehang;
   a later native flow tick must not silently reconnect them to an intact IV. */
params ["_patient","_part","_site"];
if (isNull _patient || {!local _patient}) exitWith {false};
private _map=_patient getVariable ["ACM_circulation_IV_Bags",createHashMap];
private _bags=_map getOrDefault [_part,[]];
private _physical=+(_patient getVariable ["ACME_IV_DisconnectedBagUIDs",[]]);
private _liveIDs=[];{{_liveIDs pushBack (_x param [8, ""]);} forEach (_map get _x);} forEach (keys _map);
_physical=_physical select {_x in _liveIDs};
private _detached=+(_patient getVariable ["ACME_detachedBags",[]]);
private _entries=_patient getVariable ["ACME_infusion_BagMedications",[]];
{
    if ((_x param [3,-1])==_site && {_x param [4,true]}) then {
        private _uid=[_patient,_part,_forEachIndex] call ACME_fnc_bagIdentity;
        if (_uid!="") then {
            {if ((_x param [23,""])==_uid) then {[_patient,_x,true] call ACME_fnc_infusionDeliver;};} forEach _entries;
            _physical pushBackUnique _uid;_detached pushBackUnique _uid;
        };
    };
} forEach _bags;
[_patient,"ACME_IV_DisconnectedBagUIDs",_physical] call ACME_fnc_setVarNet;
[_patient,_detached] call ACME_fnc_detachedBagsCommit;
private _key=toLowerANSI format ["%1#%2#%3",_part,true,_site];
private _lines=(_patient getVariable ["ACME_YLines",[]]) select {toLowerANSI _x!=_key};
[_patient,_lines] call ACME_fnc_yLinesCommit;
private _jobs=_patient getVariable ["ACME_yFlushJobs",createHashMap];_jobs deleteAt _key;
[_patient,"ACME_yFlushJobs",_jobs] call ACME_fnc_setVarNet;
private _pi=ACME_infusion_bodyParts find _part;
if (_pi>=0) then {_patient setVariable [format ["ACME_clampRate_%1_%2_%3",_pi,true,_site],-1,false];};
[_patient,_part] call ACM_circulation_fnc_updateActiveFluidBags;
true
