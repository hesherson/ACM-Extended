// Head-only debug action: induce one full ACME generalized seizure episode.
//
// This is not an animation-only test. It enters the same active seizure state used by lidocaine toxicity,
// TBI and nerve-agent seizures: loss of consciousness, apnea drive, seizure HR response, GestureSpasm0/4/5/6,
// then the normal postictal phase. A short-lived debug cause keeps the shared state machine from immediately
// resolving simply because the patient has no toxicologic/TBI trigger.
//
// The menu action itself is gated by ACME_fnc_debugEnabled on the provider client. Do not re-check that setting
// here because debug visibility is intentionally a client-local preference and the patient may be owned by
// another machine whose local debug setting is off.
params [["_medic",objNull,[objNull]],["_patient",objNull,[objNull]]];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {
    ["ACME_ownerCommand",[_patient,"debugSeizure",[_medic,_patient]],_patient] call CBA_fnc_targetEvent;
};

if (!alive _patient) exitWith {
    if (!isNull _medic) then {["[ACME debug] Cannot induce a seizure on a dead casualty.",2,_medic] call ACME_fnc_netNotice;};
};
if (_patient getVariable ["ace_medical_inCardiacArrest",false]) exitWith {
    if (!isNull _medic) then {["[ACME debug] Cannot induce a seizure during cardiac arrest.",2,_medic] call ACME_fnc_netNotice;};
};

private _now = CBA_missionTime;
private _duration = missionNamespace getVariable ["ACME_debug_seizureDuration",30];
if !(_duration isEqualType 0 && {finite _duration}) then {_duration = 30;};
_duration = (_duration max 5) min 120;

private _until = _now + _duration;
_patient setVariable ["ACME_debugSeizureUntil",_until,true];

// Keep the casualty in the circulation/seizure driver even when there is no medication/TBI trigger.
if (isNil "ACME_circ_activePatients") then {ACME_circ_activePatients = [];};
ACME_circ_activePatients pushBackUnique _patient;

private _state = _patient getVariable ["ACME_lido_seizureState",""];
if (_state != "active") then {
    private _maxSec = missionNamespace getVariable ["ACME_lido_seizureMaxSec",120];
    if !(_maxSec isEqualType 0 && {finite _maxSec}) then {_maxSec = 120;};
    private _phaseEnd = _now + (_maxSec max _duration);

    [_patient,"ACME_lido_seizureState","active"] call ACME_fnc_setVarNet;
    [_patient,"ACME_lido_seizurePhaseEnd",_phaseEnd] call ACME_fnc_setVarNet;
    [_patient,"ACME_seizure_rrDrive",missionNamespace getVariable ["ACME_lido_seizureApneaRR",0]] call ACME_fnc_setVarNet;
    // Publish the clinical state before collapse: delayed animation/settle handlers must see its owner.
    [_patient] call ACME_fnc_seizureCollapse;
    [_patient,true] call ACME_fnc_seizureMotion;
} else {
    // Extend the cause and recover an interrupted visual driver without repeating the collapse.
    private _phaseEnd = _patient getVariable ["ACME_lido_seizurePhaseEnd",_until];
    if (_phaseEnd < _until) then {
        [_patient,"ACME_lido_seizurePhaseEnd",_until] call ACME_fnc_setVarNet;
    };
    [_patient,true] call ACME_fnc_seizureMotion;
};

if (!isNull _medic) then {
    [format ["[ACME debug] Generalized seizure induced for %1 s.",round _duration],2.5,_medic] call ACME_fnc_netNotice;
};
