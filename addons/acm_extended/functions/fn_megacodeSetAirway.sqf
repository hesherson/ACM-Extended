// set the airway and breathing state of the megacode dummy, matched to the real systems of ACM.
// the airway obstruction and collapse use the ACM_airway state vars, because they manifest while the patient is
// unconscious, which is when airway patency is clinically assessed. the chest pathologies route through the
// owner-side chest inflictor that calls the breathing functions of ACM. it refreshes the airway page.
// _this is [_key].
params ["_key"];
private _d = uiNamespace getVariable ["ACME_MC_target", objNull];
if (isNull _d) exitWith {};
private _k = toLower _key;
_d setVariable ["ACME_MC_airway", _k, true];

switch (_k) do {
    case "patent": {
        [_d, [["blood", 0], ["vomit", 0], ["collapse", 0]], true] call ACM_airway_fnc_setAirwayState;
        // breathing again after an apnea: the respiratory rate comes back to baseline.
        if ((_d getVariable ["ACME_MC_RRTgt", 14]) <= 0) then {
            _d setVariable ["ACME_MC_RRTgt", 14, true];
            [_d, [["respirationRate", 14]], true] call ACM_core_fnc_setTargetVitalsState;
            [_d, [["respirationRate", 14]], true] call ACM_breathing_fnc_setRuntimeState;
        };
    };
    case "blood":    { [_d, [["blood", 2]], true] call ACM_airway_fnc_setAirwayState; };
    case "vomit":    { [_d, [["vomit", 2]], true] call ACM_airway_fnc_setAirwayState; };
    case "collapse": { [_d, [["collapse", 3]], true] call ACM_airway_fnc_setAirwayState; };
    case "apnea": {
        // the target too: the keeper eases the live value toward it, and a live 0 alone ramped back to the old rate.
        _d setVariable ["ACME_MC_RR", 0, true];
        _d setVariable ["ACME_MC_RRTgt", 0, true];
        [_d, [["respirationRate", 0]], true] call ACM_core_fnc_setTargetVitalsState;
        [_d, [["respirationRate", 0]], true] call ACM_breathing_fnc_setRuntimeState;
    };
    case "pneumo";
    case "tpneumo";
    case "hemothorax";
    case "ncd": { [_d, _k] remoteExec ["ACME_fnc_megacodeChestInjury", _d]; };
};

// the ACM airway obstruction and collapse only manifest while the patient is unconscious, so auto-drop the manikin
// when one of those states is applied, unless it is already unconscious or arrested.
if (_k in ["blood", "vomit", "collapse"]
    && {!(_d getVariable ["ACE_isUnconscious", false])}
    && {!(_d getVariable ["ace_medical_inCardiacArrest", false])}) then {
    [_d, true] remoteExec ["ace_medical_status_fnc_setUnconsciousState", _d];
    ["Megacode set unconscious so the airway obstruction registers.", 2.5] call ace_common_fnc_displayTextStructured;
};
[format ["Megacode airway/chest: %1.", _key], 2] call ace_common_fnc_displayTextStructured;
[[format ["Airway/chest: %1", toUpper _key], "#ffd27a"]] call ACME_fnc_megacodeLog;
[87300, "airway"] call ACME_fnc_megacodeMenu;
