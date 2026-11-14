/* The blood Y-set supplies its own downstream warmer. Keep it on the set
 * through priming, unit changes and saline flushing until the Y-set is removed. */
params ["_patient","_part","_iv","_site",["_remember",false]];
if !([_patient,_part,_iv,_site] call ACME_fnc_isYLineAccess) exitWith {false};
private _key = toLowerANSI format ["%1#%2#%3",_part,_iv,_site];
private _warmers = _patient getVariable ["ACME_yAutoWarmers",createHashMap];
if (_warmers getOrDefault [_key,false]) exitWith {true};
private _partKey = toLowerANSI _part;
private _bagMap = _patient getVariable ["ACM_circulation_IV_Bags",createHashMap];
private _bags = _bagMap getOrDefault [_partKey,[]];
private _blood = (_bags findIf {
    (_x param [0,""]) in ["Blood","FreshBlood"] && {(_x param [1,0]) > 0.01}
        && {(_x param [3,-1]) == _site} && {(_x param [4,true]) isEqualTo _iv}
        && {!([_x,"native","expired"] call ACME_fnc_bloodUseRow)}
}) >= 0;
if (_blood && {_remember} && {local _patient}) then {
    _warmers set [_key,true];
    [_patient,"ACME_yAutoWarmers",_warmers] call ACME_fnc_setVarNet;
};
_blood
