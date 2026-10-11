/* Read-only advisory gate, repeated with the physical primary UID by the patient owner. */
params ["_patient", "_part", "_iv", "_site", ["_candidateType", ""], ["_infusion", false]];
if (isNull _patient || {!([_patient, _part, _iv, _site] call ACME_fnc_transfusionAccessValid)}
    || {[_patient, _part, _iv, _site] call ACME_fnc_isYLineAccess}) exitWith {false};
private _key = toLowerANSI format ["%1#%2#%3", _part, _iv, _site];
if (_key in (_patient getVariable ["ACME_yFlushJobs", createHashMap])
    || {_key in (_patient getVariable ["ACME_PiggybackLines", createHashMap])}) exitWith {false};
private _bags = ((_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [toLowerANSI _part, []]) select {
    (_x param [3, -1]) == _site && {(_x param [4, true]) == _iv}
        && {!((_x param [0, ""]) in ["ACME_Empty", "ACME_EmptySaline"])}
};
if (count _bags != 1) exitWith {false};
private _primary = _bags select 0;
private _type = _primary param [0, ""];
private _uid = _primary param [8, ""];
if (_uid == "" || {(_primary param [1, 0]) <= 0.01}
    || {_type in ["Blood", "FreshBlood", "FBTK", "ACME_Propofol", "ACME_SalineY"]}
    || {((_patient getVariable ["ACME_infusion_BagMedications", []]) findIf {(_x param [23, ""]) == _uid}) >= 0}
    || {_uid in (_patient getVariable ["ACME_detachedBags", []])}
    || {_uid in (_patient getVariable ["ACME_IV_DisconnectedBagUIDs", []])}) exitWith {false};
private _pi = ACME_infusion_bodyParts find toLowerANSI _part;
private _siteFlow = if (_iv) then {((_patient getVariable ["ACM_circulation_FluidBagsFlow_IV",[]]) param [_pi,[]]) param [_site,0]} else {(_patient getVariable ["ACM_circulation_FluidBagsFlow_IO",[]]) param [_pi,0]};
if (_pi < 0 || {_siteFlow <= 0} || {([_patient, _pi, _iv, _site, -1, _uid] call ACM_circulation_fnc_getIVFlowRate) <= 0}) exitWith {false};
if (_candidateType == "") exitWith {true};
if (_candidateType in ["Blood", "FreshBlood", "FBTK", "ACME_Propofol", "ACME_SalineY"]) exitWith {false};
if (_infusion) exitWith {_type == "Saline" && {_candidateType == "Saline"}};
_type == _candidateType
