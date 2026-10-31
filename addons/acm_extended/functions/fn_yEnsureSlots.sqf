/* Owner-only topology repair. Never accept a bag map or fluid volume supplied by a viewer. */
params ["_patient"];
if (isNull _patient || {!local _patient}) exitWith {false};
private _now = diag_tickTime;
if (_now < (_patient getVariable ["ACME_ySlotsNextCheckLocal", -1])) exitWith {false};
_patient setVariable ["ACME_ySlotsNextCheckLocal", _now + 1, false];
private _map = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
private _changed = false;
{
    private _bits = (toLowerANSI _x) splitString "#";
    if (count _bits != 3) then {continue;};
    _bits params ["_part","_ivText","_siteText"];
    if !(_ivText in ["true","false"] && {_siteText in ["0","1","2"]}
        && {_part in ["head","body","leftarm","rightarm","leftleg","rightleg"]}) then {continue;};
    private _iv = _ivText == "true"; private _site = parseNumber _siteText;
    if (!_iv && {_site != 0}) then {continue;};
    if !([_patient,_part,_iv,_site] call ACME_fnc_transfusionAccessValid) then {continue;};
    private _arr = +(_map getOrDefault [_part, []]);
    {
        _x params ["_types","_empty"];
        private _present = (_arr findIf {(_x param [0, ""]) in _types && {(_x param [3,-1]) == _site} && {(_x param [4,true]) isEqualTo _iv}}) >= 0;
        if (!_present) then {_arr pushBack [_empty,0,0,_site,_iv,-1,1000,-1]; _changed = true;};
    } forEach [[["Blood","FreshBlood","ACME_Empty"],"ACME_Empty"],[["Saline","ACME_SalineY","ACME_EmptySaline"],"ACME_EmptySaline"]];
    _map set [_part,_arr];
} forEach (_patient getVariable ["ACME_YLines", []]);
if (_changed) then {[_patient,_map,true] call ACME_fnc_ivBagsCommit;};
_changed
