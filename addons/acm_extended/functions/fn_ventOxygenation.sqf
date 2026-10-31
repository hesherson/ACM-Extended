// Ventilator oxygenation/shunt model.  Aspiration is an additional recruitable shunt: PEEP can improve some
// collapsed/flooded units but suctioning visible airway contents does not erase established aspiration injury.
params ["_patient", "_comp", "_peep", "_fio2", "_recruit"];
private _aspiration = [_patient] call ACME_fnc_aspirationState;
// Do not publish a new shunt/target from half of an incoming clinical packet.
// The caller continues delivering breaths and gas while this model defers.
if (_aspiration isEqualTo []) exitWith {nil};

private _overload = _patient getVariable ["ACM_circulation_Overload_Volume", 0];
private _ptx      = _patient getVariable ["ACM_breathing_Pneumothorax_State", 0];
private _htxFluid = _patient getVariable ["ACM_breathing_Hemothorax_Fluid", 0];
private _blast    = _patient getVariable ["ACME_blastLung_State", 0];
private _asp      = (_aspiration select 2) max 0 min 1;
private _aspEdema = (_aspiration select 3) max 0 min 1;
private _aspInjury = _asp max (0.85 * _aspEdema);

private _edemaN = linearConversion [0.2, 1.6, _overload, 0, 1, true];
private _blastN = _blast;
private _ptxN   = linearConversion [0, 3, _ptx, 0, 1, true];
private _htxN   = linearConversion [0, 1500, _htxFluid, 0, 1, true];

// Recruitable shunt: edema, blast-lung alveolar collapse, and the recruitable component of aspiration pneumonitis.
private _shuntRecruitable = (0.38 * _edemaN) + (0.42 * _blastN) + (0.30 * _aspInjury);
// Fixed shunt: pleural air/blood compressing the lung; PEEP cannot correct it.
private _shuntFixed = (0.40 * _ptxN) + (0.30 * _htxN);

private _peepRecruit = linearConversion [4, 15, _peep, 0, 1, true];
private _overdistend = linearConversion [16, 24, _peep, 0, 1, true];
private _openFrac = ((_peepRecruit * 0.85) + (_recruit * 0.30)) min 1;

private _shunt = _shuntFixed
    + (_shuntRecruitable * (1 - _openFrac))
    + (0.22 * _overdistend);
_shunt = (_shunt max 0) min 0.80;
[_patient, _shunt, true, false] call ACME_fnc_ventShuntCommit;

private _ceiling = 99 - (_shunt * 52);
private _exposure = [_patient] call ACME_fnc_flightExposure;
private _pRatio = if ((missionNamespace getVariable ["ACME_sys_flight", true])
    && {(missionNamespace getVariable ["ACME_altitude_enable", true])
        || {missionNamespace getVariable ["ACM_breathing_altitudeAffectOxygen", false]}}) then {_exposure select 2} else {1};
private _fio2Eff = ((_fio2 / 100) * _pRatio) max 0.21;
private _fio2Lift = linearConversion [0.21, 1.0, _fio2Eff, 0, 1, true];
private _targetSat = _ceiling - ((1 - _fio2Lift) * (_shunt * 30));

if (_comp < 0.35) then {
    _targetSat = _targetSat - (linearConversion [0.35, 0.20, _comp, 0, 8, true]);
};

// Established aspiration also makes the lung less compliant. Keep this modest so PEEP/pressure strategy matters
// without turning every small aspiration into blast-lung-level stiffness.
_targetSat = _targetSat - (3 * _aspInjury);

// Retain shunt/recruitment/PEEP response, then constrain it by the same actual
// cabin pressure and delivered oxygen used by the native saturation writer.
((_targetSat max 55) min 99) min ([_patient, _exposure, _fio2] call ACME_fnc_altitudeOxygenCeiling)
