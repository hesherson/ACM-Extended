/* Legacy Y attachment compatibility. Retag only the named access on its CURRENT owner.
 * Never publish a viewer's snapshot of every bag or search unrelated access sites. */
params ["_patient", "_lineKey", "_iv", ["_epoch", -1]];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {[_patient,"ySalineSetup",_this] call ACME_fnc_ownerDispatch;};
if (_epoch < 0) then {_epoch = [_patient] call ACME_fnc_clinicalEpoch;};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)) exitWith {};
_lineKey = toLowerANSI _lineKey;
private _bits = _lineKey splitString "#";
if (count _bits != 3) exitWith {};
_bits params ["_part","_ivText","_siteText"];
if !(_ivText in ["true","false"] && {_siteText in ["0","1","2"]} && {(_ivText == "true") isEqualTo _iv}) exitWith {};
private _site = parseNumber _siteText;
if (!_iv && {_site != 0}) exitWith {};
if !([_patient,_part,_iv,_site] call ACME_fnc_transfusionAccessValid) exitWith {};
private _yl = +(_patient getVariable ["ACME_YLines", []]);
if !(_lineKey in _yl) then {_yl pushBack _lineKey; [_patient,_yl] call ACME_fnc_yLinesCommit;};
private _tag = {
    params ["_patient","_part","_iv","_site","_lineKey","_epoch"];
    if (isNull _patient || {!local _patient} || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
        || {!(_lineKey in (_patient getVariable ["ACME_YLines", []]))}
        || {!([_patient,_part,_iv,_site] call ACME_fnc_transfusionAccessValid)}) exitWith {true};
    private _bags = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
    private _arr = +(_bags getOrDefault [_part, []]);
    private _i = _arr findIf {(_x param [0, ""]) in ["Saline","ACME_SalineY"] && {(_x param [4,true]) isEqualTo _iv} && {(_x param [3,-1]) == _site}};
    if (_i < 0) exitWith {false};
    private _e = +(_arr select _i); _e set [0,"ACME_SalineY"]; _arr set [_i,_e]; _bags set [_part,_arr];
    [_patient,_bags] call ACME_fnc_ivBagsCommit;
    true
};
private _args = [_patient,_part,_iv,_site,_lineKey,_epoch];
if !(_args call _tag) then {
    [{params ["_args","_h"]; _args params ["_context","_tag","_tries"]; _tries set [0,(_tries select 0)+1];
        if (_context call _tag || {(_tries select 0) >= 12}) then {[_h] call CBA_fnc_removePerFrameHandler;};
    },0.25,[_args,_tag,[0]]] call CBA_fnc_addPerFrameHandler;
};
