/* Patient-owner aftercare for a completed surgical tract. No inventory writes. */
params ["_patient", "_medic", "_side", "_operation", "_epoch", ["_request", []], ["_usedKit", false]];
if (isNull _patient || {!local _patient}
    || {isNull _medic} || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}
    || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {!(_side in ["left", "right"])}
    || {!(_operation in ["peel", "burp", "sweep", "widen", "seal"])}) exitWith {false};
if ((_medic distance _patient) > 5) exitWith {false};
private _procedure = if (_operation in ["sweep", "widen"]) then {"thoracostomy"} else {"thoracostomySeal"};
if !([_medic, _procedure, _operation != "widen"] call ACME_fnc_procedureAllowed) exitWith {false};
if (count (_patient getVariable [format ["ACME_thora_incision_%1", _side], []]) != 3
    || {_patient getVariable [format ["ACME_thora_tube_%1", _side], false]}) exitWith {false};
private _tract = _patient getVariable [format ["ACME_thora_open_%1", _side], ""];
private _sealed = _patient getVariable [format ["ACME_thora_sealed_%1", _side], false];
private _closed = _patient getVariable [format ["ACME_thora_closed_%1", _side], false];
if (_operation == "seal") exitWith {
    if (_tract != "finger" || {_sealed} || {_closed}) exitWith {false};
    [_patient, _medic, "thoraSeal", [_side, _epoch]] call ACME_fnc_chestSealEffectLocal
};
if (_operation == "sweep" && {_tract != "finger" || {_sealed} || {_closed}}) exitWith {false};
if (_operation == "widen" && {_tract != "kelly" || {_sealed} || {_closed}}) exitWith {false};
if (_operation in ["peel", "burp"] && {!_sealed || {!(_tract in ["sealed", "finger"])}}) exitWith {false};

if (_operation == "burp" && {!([_patient,true] call ACME_fnc_chestSealBurpReady)}) exitWith {false};
// Measure pressure and debit retained blood BEFORE relieving PTX. One accepted
// click is one debit; a delayed replay cannot drain blood that accumulated later.
private _mode = if (_operation in ["sweep", "widen"]) then {"finger"} else {"seal"};
private _drained = [_patient, _medic, _mode, _epoch, _request] call ACME_fnc_thoraDrainBloodLocal;
if (_drained < 0) exitWith {false};
if (_operation == "burp") then {
    _patient setVariable ["ACME_CS_lastBurp",CBA_missionTime,true];
};
if (_operation == "widen") then {
    // The prior kelly state is checked on the owner. A repeated provider click
    // cannot complete a second incision, replace a tube, or reset its aggregate.
    [_patient, _side, "open", "finger"] call ACME_fnc_thoraSideStateCommit;
    [_patient] call ACME_fnc_thoraBumpVer;
    if ((_patient getVariable ["ACM_breathing_Thoracostomy_State", 0]) < 1) then {
        if (alive _patient) then {
            [_medic, _patient, _usedKit, false] call ACM_breathing_fnc_Thoracostomy_startLocal;
        } else {
            [_patient, [["thoracostomyState", 1], ["thoracostomyUsedKit", _usedKit]], true] call ACM_breathing_fnc_setRuntimeState;
        };
    } else {
        if (_usedKit) then {[_patient, [["thoracostomyUsedKit", true]], true] call ACM_breathing_fnc_setRuntimeState;};
    };
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
    case "widen": {"%1 widened the %2 finger thoracostomy"};
    default {"%1 repeated the finger sweep of the %2 thoracostomy"};
};
private _logArgs = [[_medic,false,true] call ace_common_fnc_getName,_side];
if (_operation == "burp") then {
    // Suppress rapid re-hover logging without suppressing a valid pressure release or blood debit.
    [_patient,format ["thoraBurp:%1",_side],_message,_logArgs,_medic,10] call ACME_fnc_chestSealLogOnce;
} else {
    [_patient,"activity",_message,_logArgs] call ace_medical_treatment_fnc_addToLog;
};

true
