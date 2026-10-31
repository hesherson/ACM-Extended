/* A read-only altitude ceiling; it never owns the native clinical target.
 * Delivered oxygen raises FiO2, rather than making a wearer immune to vacuum.
 * Ventilators supply their measured effective FiO2; a passive mask provides
 * gas only while its existing metered NRB delivery is actually flowing.
 */
params ["_patient", ["_exposure", []], ["_deliveredFiO2", -1]];
// The visible Flight physiology switch is the master altitude switch.
// ACM's legacy optional altitude setting cannot secretly keep it running OFF.
if !(missionNamespace getVariable ["ACME_sys_flight", true]) exitWith {99};
private _flight = missionNamespace getVariable ["ACME_altitude_enable", true];
private _nativeAltitude = missionNamespace getVariable ["ACM_breathing_altitudeAffectOxygen", false];
if (!_flight && {!_nativeAltitude}) exitWith {99};
if (count _exposure != 5) then {_exposure = [_patient] call ACME_fnc_flightExposure;};
if (!_nativeAltitude && {(_exposure select 0) < (missionNamespace getVariable ["ACME_altitude_minMetres", 500])}) exitWith {99};
private _pRatio = _exposure select 2;
private _fio2 = [_patient, _exposure] call ACME_fnc_flightDeliveredFiO2;
if (_deliveredFiO2 isEqualType 0 && {finite _deliveredFiO2} && {_deliveredFiO2 >= 21}) then {
    _fio2 = _deliveredFiO2 min 100;
};
if !(_fio2 isEqualType 0 && {finite _fio2}) then {_fio2 = 21;};
_fio2 = (_fio2 max 21) min 100;
private _alveolarRatio = (_fio2 * _pRatio) / 21;
if (_alveolarRatio >= 1) exitWith {99};
if (_alveolarRatio < 0.55) exitWith {linearConversion [0, 0.55, _alveolarRatio, 0, 78, true]};
linearConversion [0.55, 1.0, _alveolarRatio, 78, 99, true]
