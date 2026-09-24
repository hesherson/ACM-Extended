/* Patient-owner aftercare for a completed surgical tract. No inventory writes. */
params ["_patient", "_medic", "_side", "_operation", "_epoch"];
if (isNull _patient || {!local _patient}
    || {isNull _medic} || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}
    || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {!(_side in ["left", "right"])}
    || {!(_operation in ["peel", "burp", "sweep"])}) exitWith {};
if ((_medic distance _patient) > 5) exitWith {};
private _procedure = if (_operation == "sweep") then {"thoracostomy"} else {"thoracostomySeal"};
if !([_medic, _procedure, true] call ACME_fnc_procedureAllowed) exitWith {};
if (count (_patient getVariable [format ["ACME_thora_incision_%1", _side], []]) != 3
    || {_patient getVariable [format ["ACME_thora_tube_%1", _side], false]}) exitWith {};
private _tract = _patient getVariable [format ["ACME_thora_open_%1", _side], ""];
private _sealed = _patient getVariable [format ["ACME_thora_sealed_%1", _side], false];
private _closed = _patient getVariable [format ["ACME_thora_closed_%1", _side], false];
if (_operation == "sweep" && {_tract != "finger" || {_sealed} || {_closed}}) exitWith {};
if (_operation in ["peel", "burp"] && {!_sealed || {!(_tract in ["sealed", "finger"])}}) exitWith {};

if (_operation == "burp" && {!([_patient,true] call ACME_fnc_chestSealBurpReady)}) exitWith {};
if (_operation == "burp") then {
    _patient setVariable ["ACME_CS_lastBurp",CBA_missionTime,true];
};

if (_operation == "peel") then {
    [_patient, _side, "sealed", false] call ACME_fnc_thoraSideStateCommit;
    [_patient, _side, "closed", false] call ACME_fnc_thoraSideStateCommit;
    [_patient, _side, "open", "finger"] call ACME_fnc_thoraSideStateCommit;
    [_patient] call ACME_fnc_thoraBumpVer;
};
// The surgical tract provides direct pleural access, independent of traumatic-wound seals.
// Burping relieves pressure once while retaining the dressing; peeling restores the open tract.
// Preserve any chest tube on the opposite side and ACM's aggregate tube state.
if (alive _patient) then {
    [_patient, "thora"] call ACME_fnc_ptxTreat;
    [_patient] call ACM_breathing_fnc_updateLungState;
};
private _message = switch (_operation) do {
    case "peel": {"%1 removed the chest seal over the %2 thoracostomy"};
    case "burp": {"%1 burped the chest seal over the %2 thoracostomy"};
    default {"%1 repeated the finger sweep of the %2 thoracostomy"};
};
private _logArgs = [[_medic,false,true] call ace_common_fnc_getName,_side];
if (_operation == "burp") then {
    [_patient,"burp",_message,_logArgs,_medic,0] call ACME_fnc_chestSealLogOnce;
} else {
    [_patient,"activity",_message,_logArgs] call ace_medical_treatment_fnc_addToLog;
};
