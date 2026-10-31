// ventilator alarms. this computes which alarms are actually active, from real machine and patient state. the
// count beside the bell on the strip is the length of this list, so it means something rather than being
// decoration.
// every alarm here corresponds to something the sim genuinely models, and every one is a condition a real
// transport ventilator would shout about. nothing is invented to pad the list.
// alarms are not popups. consistent with the silent-errors principle of the mod, the machine tells you on its own
// screen and it is your job to look at it. the bell tells you how many and the alarm screen tells you which.
// call it as [_patient] call ACME_fnc_ventAlarmTick.
params ["_patient"];
if !(missionNamespace getVariable ["ACME_sys_vent", true]) exitWith {};  // the system toggle. fully off means this stops.
if (isNull _patient || {!alive _patient} || {!(_patient isKindOf "CAManBase")}) exitWith {};

// not configured or not connected means no machine and no alarms. a vent sitting in a bag is not alarming.
if (!(_patient getVariable ["ACME_vent_configured", false]) || {!(_patient getVariable ["ACME_vent_connected", false])}) exitWith {
    [_patient, "ACME_vent_alarms", []] call ACME_fnc_setVarNet;
};

private _effective = [_patient] call ACME_fnc_ventEffectiveSettings;
private _simple = _effective select 0;
private _mode = _effective select 1;
private _iface   = _patient getVariable ["ACME_vent_iface", ""];
private _driving = _patient getVariable ["ACME_vent_driving", false];
private _ettIn   = _patient getVariable ["ACME_ETT_Inserted", false];
private _igelIn  = ((_patient getVariable ["ACM_airway_AirwayItem_Oral", ""]) isEqualTo "SGA");
private _cricIn  = (_patient getVariable ["ACM_airway_SurgicalAirway_TubeInserted", false]);
// any secured airway, not just an ETT. fn_ventdrivetick has always resolved all three, the ETT, the cric and the
// i-gel, and the machine drives happily through any of them, and this file only ever asked about the tube, so a
// casualty on an i-gel or a cric read as having nothing in their airway at all.
private _securedAirway = _ettIn || _igelIn || _cricIn;

private _vtSet = if (_simple) then {_effective select 3} else {(_patient getVariable ["ACME_vent_vt", 500]) max 1};
private _vte     = _patient getVariable ["ACME_vent_vte", 0];
private _pip     = _patient getVariable ["ACME_vent_pip", 0];
private _bpm = _effective select 2;
private _now     = CBA_missionTime;

private _alarms = [];

// the patient fighting the ventilator.
// a casualty who is paralyzed and not asleep, or whose block is wearing off, breathes against the machine. every
// one of those efforts collides with a delivered breath, and the machine feels it as a pressure spike.
// this is the surfacing that the sedation and paralysis state has never had. the capnograph shows it as a notch
// in the plateau, and the ventilator shows it here, as the alarm that makes somebody look.
// one lung.
// a tube past the carina puts the whole tidal volume into one lung, so the machine is pushing the same breath
// into half the space and the peak pressure climbs. the alarm names it rather than leaving the medic to work out
// why a perfectly good capnograph is sitting next to a falling saturation.
if (_patient getVariable ["ACME_ETT_Mainstem", false]) then {
    _alarms pushBack "ENDOBRONCHIAL TUBE";
};

private _dys = _patient getVariable ["ACME_vent_dyssync", 0];
if (_dys > 0.35) then {
    _alarms pushBack "PATIENT FIGHTING VENT";
};

// circuit disconnect.
// it is set to invasive and connected, and there is no tube in the airway. the machine is ventilating the open
// air.
if (((_simple || {_iface == "INVASIVE"}) && {!_securedAirway})
    || {_simple && {!(_patient getVariable ["ACME_vent_circuit", false])}}
    || {(_patient getVariable ["ACME_vent_nivMask", false]) && {
        !([_patient] call ACME_fnc_ventNivEligible) || {_mode != "CPAP PS HF"}
        || {!(_iface in ["NON-INVASIVE", "NON INVASIVE"])}
        || {!(_patient getVariable ["ACME_vent_circuit", false])}
    }}) then {
    _alarms pushBack "CIRCUIT DISCONNECT";
};

// high airway pressure.
// the pressure it is taking to deliver the set breath has crossed the barotrauma threshold. this is the alarm
// that precedes lung injury, and it is the one that matters most.
// the threshold is the PRESS ALERT setting of the operator, from ALERTS page 1 of 2, rather than a hardcoded
// number. set it high and the machine will quietly barotraumatise the patient without ever complaining, which is
// a real thing people do.
private _pipHigh = _patient getVariable ["ACME_vent_alertPAlert", 40];
if (_driving && {_pip >= _pipHigh}) then {
    _alarms pushBack "HIGH AIRWAY PRESSURE";
};

// an rr outside the set bounds.
// LOW rr and HIGH rr come from the ALERTS screen. HIGH rr is the one that catches a patient triggering rapidly,
// because they are fighting the vent or air-hungry, and the set rate of the machine is not what they are
// actually breathing at.
private _rrLo = _patient getVariable ["ACME_vent_alertRRLow", 6];
private _rrHi = _patient getVariable ["ACME_vent_alertRRHigh", 25];
private _rrMeasured = _patient getVariable ["ACM_breathing_RespirationRate", 0];
if (_rrMeasured > 0) then {
    if (_rrMeasured < _rrLo) then { _alarms pushBack "LOW RESP RATE"; };
    if (_rrMeasured > _rrHi) then { _alarms pushBack "HIGH RESP RATE"; };

    // battery. it reads straight off the published percentage rather than a flag, so the alarm clears by itself the
    // moment the vent goes on vehicle power and starts recharging.
    private _batt = _patient getVariable ["ACME_vent_battery", 100];
    if !(_patient getVariable ["ACME_vent_battExternal", false]) then {
        if (_batt <= (missionNamespace getVariable ["ACME_vent_batteryCritPct", 10])) then {
            _alarms pushBack "BATTERY CRITICAL";
        } else {
            if (_batt <= (missionNamespace getVariable ["ACME_vent_batteryLowPct", 25])) then {
                _alarms pushBack "LOW BATTERY";
            };
        };
    };
};

// low exhaled tidal volume.
// the breath went in and did not come back: a leak, an open chest, a draining tube, or a pressure-controlled
// breath that a stiff lung refused to accept. real machines alarm on VTe rather than VTi for exactly this
// reason.
private _vteFrac = missionNamespace getVariable ["ACME_vent_alarmLowVteFrac", 0.70];
private _vtRef = (_patient getVariable ["ACME_vent_vtReference", _vtSet]) max 1;
if (_driving && {_vte > 0} && {_vte < (_vtRef * _vteFrac)}) then {
    _alarms pushBack "LOW EXHALED VOLUME";
};

// auto-PEEP, or gas trapping.
// the expiratory time is too short for this lung to empty, so gas is stacking breath on breath. this is the alarm
// that catches an inverse i:e ratio, or simply too high a rate, quietly strangling the patient.
private _autoP = _patient getVariable ["ACME_vent_autoPEEP", 0];
if (_driving && {_autoP >= (missionNamespace getVariable ["ACME_vent_alarmAutoPeep", 4])}) then {
    _alarms pushBack "GAS TRAPPING";
};

// apnea.
// nobody is breathing this patient. it is either a spontaneous mode, CPAP, with a casualty who has no drive, or a
// mandatory mode that is not actually delivering. this is the alarm that should get someone killed if ignored,
// and it is precisely the case the manual breath button exists for.
private _rrNow = _patient getVariable ["ACM_breathing_RespirationRate", 0];
private _manualLast = _patient getVariable ["ACME_vent_manualBreathServer", -999];
private _manualWindow = missionNamespace getVariable ["ACME_vent_manualBreathWindow", 12];
private _handBreathing = ((serverTime - _manualLast) max 0) <= _manualWindow;
if (_rrNow < 4 && {!_handBreathing}) then {
    _alarms pushBack "APNEA";
};

// minute ventilation alarms.
// there is a settle window. both minute-volume alarms are held off for a few seconds after the machine starts
// driving. a ventilator that has just been connected has not completed a breath cycle yet, so its measured
// minute volume is not yet a real number, and alarming on it means every startup on perfectly good settings
// opens with a warning the medic has to dismiss. real devices do the same, because they do not alarm on a volume
// they have not measured. this delays only the alarm, never the physiology.
private _mvLpm = [_patient] call ACME_fnc_ventMinuteVolume;
private _driveT0 = _patient getVariable ["ACME_vent_driveT0", -1];
private _settle = missionNamespace getVariable ["ACME_vent_alarmSettleSec", 12];
private _settled = (_driveT0 >= 0) && {(CBA_missionTime - _driveT0) >= _settle};
([_patient] call ACME_fnc_ventMVLimits) params ["_mvLow", "_mvHigh"];
// The same exhaled L/min value is shown on the live panel. Keep the startup delay.
if (_driving && {_settled}) then {
    if (_mvLpm < _mvLow) then {_alarms pushBack "LOW MINUTE VOLUME";};
    if (_mvLpm >= _mvHigh) then {_alarms pushBack "HIGH MINUTE VOLUME";};
};

// cannot ventilate in this mode.
// CPAP is a spontaneous mode: it supports a patient who is breathing and cannot breathe for one who is not. if
// the casualty has no drive, the machine is doing nothing for them and the operator needs to know why.
if (_mode == "CPAP PS HF" && {_rrNow < 4} && {!_handBreathing}) then {
    _alarms pushBack "NO SPONT. EFFORT";
};

[_patient, "ACME_vent_alarms", _alarms] call ACME_fnc_setVarNet;

// priority.
// a real ventilator does not shout equally about everything, and neither should this one. the priority decides
// the audible pattern, in fn_ventalarmsound: HIGH is 5 beeps every 2 s, medium is 3 beeps every 5 s, and LOW is
// one beep, once. the whole point is that a medic can tell without looking whether they have seconds or minutes.
// HIGH means the patient is not being ventilated, or is being actively injured, right now.
// medium means ventilation is inadequate or going wrong. it is dangerous and not instantly fatal.
// LOW is informational. it says its piece once and stops.
private _high = missionNamespace getVariable ["ACME_vent_alarmHigh", ["CIRCUIT DISCONNECT", "APNEA", "HIGH AIRWAY PRESSURE", "GAS TRAPPING", "NO SPONT. EFFORT"]];
private _med  = missionNamespace getVariable ["ACME_vent_alarmMed", ["LOW MINUTE VOLUME", "HIGH MINUTE VOLUME", "LOW EXHALED VOLUME", "HIGH RESP RATE", "LOW RESP RATE"]];
private _prio = switch (true) do {
    case (_alarms findIf {_x in _high} >= 0): { 3 };  // HIGH.
    case (_alarms findIf {_x in _med}  >= 0): { 2 };  // medium.
    case !(_alarms isEqualTo []):             { 1 };  // LOW.
    default { 0 };
};
[_patient, "ACME_vent_alarmPrio", _prio] call ACME_fnc_setVarNet;

// a new alarm un-silences the machine. silencing an alarm acknowledges the alarm you have seen, and it must not
// deafen you to the next one, which may be the one that kills them.
private _prev = _patient getVariable ["ACME_vent_alarmsPrev", []];
private _fresh = _alarms select {!(_x in _prev)};
if !(_fresh isEqualTo []) then {
    [_patient, "ACME_vent_alarmSilencedUntil", 0] call ACME_fnc_setVarNet;
    // tell the clients about the freshly raised alarms, so the operating medic can write them into their device
    // logbook. the log lives on the operator, and only they should record the alarms of their own machine. each
    // client filters to the patient their device is actually on.
    private _operator = _patient getVariable ["ACME_vent_operator", objNull];
    if (!isNull _operator) then {
        ["ACME_ventAlarmLog", [_patient, _fresh], _operator] call CBA_fnc_targetEvent;
    };
};
[_patient, "ACME_vent_alarmsPrev", _alarms] call ACME_fnc_setVarNet;
