/* Read-only enrollment for the independent flight worker. Historical pressure
 * samples are not activity: a healthy patient on the ground must retire after
 * the final descent/disable cleanup. Existing PTX still observes pressure
 * changes below the hypoxia threshold. */
params ["_patient", ["_includeExit", true]];
if (isNull _patient || {!local _patient} || {!alive _patient}
    || {!(_patient isKindOf "CAManBase")}
    || {_patient getVariable ["ACME_clinicalRestoring", false]}) exitWith {false};
private _customAltitude = missionNamespace getVariable ["ACME_altitude_enable", true];
private _nativeAltitude = missionNamespace getVariable ["ACM_breathing_altitudeAffectOxygen", false];
private _enabled = (missionNamespace getVariable ["ACME_sys_flight", true])
    && {_customAltitude || {_nativeAltitude}};
private _exposed = _enabled && {
    private _height = [_patient] call ACME_fnc_altitudeTrue;
    (_customAltitude && {_height >= (missionNamespace getVariable ["ACME_altitude_minMetres", 500])})
    // Native ACM's optional altitude model has no 500 m cutoff. Its healthy AI
    // require the same enrollment at every positive altitude, while sea level
    // remains neutral and does not acquire a native medical worker.
    || {_nativeAltitude && {_height > 0}}
    || {_customAltitude && {(_patient getVariable ["ACM_breathing_Pneumothorax_State", 0]) > 0}}
    || {_customAltitude && {_patient getVariable ["ACM_breathing_TensionPneumothorax_State", false]}}
    || {_customAltitude && {
        // Native seated occupancy is cheap. Supported walking interiors below
        // the hypoxia cutoff only need geometry when maneuver stress could
        // affect blood pressure, or an enrolled flight still needs its exit.
        private _parent = objectParent _patient;
        (!isNull _parent && {_parent isKindOf "Air"})
        || {((_patient getVariable ["ACM_circulation_Blood_Volume", 6])
            < ((missionNamespace getVariable ["ACME_hypo_bloodNormal", 6]) - 0.5)
            || {_patient getVariable ["ACME_flight_tickActive", false]})
            && {!isNull ([_patient] call ACME_fnc_flightAirframe)}}
    }}
};
_exposed
    || {_includeExit && {_patient getVariable ["ACME_flight_tickActive", false]}}
    || {abs (_patient getVariable ["ACME_alt_hypoxia", 0]) > 0.001}
    || {_patient getVariable ["ACME_alt_expanding", false]}
    || {abs (_patient getVariable ["ACME_flightG_stress", 0]) > 0.001}
    || {abs (_patient getVariable ["ACME_flightG_resistAdd", 0]) > 0.001}
