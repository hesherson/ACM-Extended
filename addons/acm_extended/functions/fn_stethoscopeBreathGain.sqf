// Read-only anterior/posterior transmission for the breath and basal-crackle channels.
// Native lung/airway effectiveness grades spontaneous breath depth. A driving ventilator uses
// measured exhaled tidal volume instead: a paralyzed but adequately ventilated patient is not shallow.
// These are listening gains, not additional physiology or a change to either lung's diagnosis.
params ["_patient"];
if (isNull _patient || {!alive _patient}
    || {(_patient getVariable ["ACM_breathing_RespirationRate",18]) < 1}) exitWith {[0,0]};

private _depth = 1;
if ((missionNamespace getVariable ["ACME_sys_vent",true])
    && {_patient getVariable ["ACME_vent_driving",false]}) then {
    _depth = (_patient getVariable ["ACME_vent_vte",0]) / 500;
} else {
    _depth = ([_patient] call ACM_airway_fnc_getAirwayState)
        min ([_patient] call ACM_breathing_fnc_getBreathingState);
};
_depth = (_depth max 0) min 1;
if (_depth <= 0) exitWith {[0,0]};

// Normal transmission at >= 95% effectiveness; strongest shallow attenuation at <= 30%.
// Front falls to 25%, back to 70%. Near-zero airflow fades both to silence rather than adding
// a positive sound floor. Existing unilateral findings and chest-position weights still multiply this.
private _shallow = linearConversion [0.3,0.95,_depth,1,0,true];
private _airflow = linearConversion [0,0.15,_depth,0,1,true];
[_airflow * (1 - 0.75 * _shallow), _airflow * (1 - 0.30 * _shallow)]
