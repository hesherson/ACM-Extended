/* B213 read-only observation of respiratory rate and the absence-of-breathing rules from Check Breathing.
 * Owner replication remains authoritative. Observing never changes patient physiology or treatment leases.
 */
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!alive _patient}) exitWith {0};
private _ventilated = (missionNamespace getVariable ["ACME_sys_vent", true])
    && {_patient getVariable ["ACME_vent_driving", false]};
// A ventilated, paralyzed casualty can have no spontaneous effort while delivered breaths remain observable.
// Conversely a zero delivered volume is a machine cycle without a visible effective chest rise.
if (_ventilated) exitWith {
    private _delivered = _patient getVariable ["ACME_vent_effectiveRR", 0];
    private _vte = _patient getVariable ["ACME_vent_vte", 0];
    if !(_delivered isEqualType 0 && {finite _delivered} && {_vte isEqualType 0} && {finite _vte}) exitWith {0};
    if (_vte <= 0) exitWith {0};
    (_delivered max 0) min 80
};
if ((_patient getVariable ["ace_medical_heartRate", 80]) < 20
    || {_patient getVariable ["ACM_breathing_TensionPneumothorax_State", false]}
    || {(_patient getVariable ["ACM_breathing_Hemothorax_Fluid", 0]) > 1.4}
    || {([_patient] call ACM_airway_fnc_getAirwayState) <= 0}
    || {([_patient] call ACM_breathing_fnc_getBreathingState) <= 0}) exitWith {0};
// Do not display a stale spontaneous rate in the first frame after arrest/paralysis. Active bagging can
// still deliver visible breaths; its native rate is distinct from spontaneous respiratory effort.
if ((_patient getVariable ["ACME_roc_paralyzed", false]
        || {_patient getVariable ["ace_medical_inCardiacArrest", false]})
    && {!([_patient] call ACM_core_fnc_bvmActive)}) exitWith {0};
private _rate = _patient getVariable ["ACM_breathing_RespirationRate", 0];
if !(_rate isEqualType 0 && {finite _rate}) exitWith {0};
(_rate max 0) min 80
