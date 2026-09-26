// oxygen delivery, DO2. it is the number hemorrhage actually degrades, as distinct from saturation.
// SpO2 is the saturation of the hemoglobin a casualty still has. it says nothing about how much of it there is,
// or whether any of it is reaching tissue. a casualty who has lost 40 percent of their blood volume with a clear
// airway and good ventilation saturates near 100 percent while their oxygen delivery is catastrophic, which is
// precisely why a pulse oximeter is falsely reassuring in hemorrhage and why you treat the bleeding rather than
// the number.
// delivery is the product of content and flow.
// DO2 is cardiac output times arterial oxygen content.
// cao2 is the hemoglobin concentration times the saturation.
// co is stroke volume, from preload, times heart rate.
// this returns DO2 as a fraction of normal, so 1.0 is a healthy casualty and the numbers below are readable with
// no units to carry around.
// three things fall out of doing it this way, and each is a real clinical behavior we could not previously show.
// 1. dilution is visible. the hemoglobin concentration is the red cell volume over the total intravascular
// volume, so filling a casualty with crystalloid drops their oxygen content without touching their saturation or
// their blood pressure. acute hemorrhage alone does not drop the concentration, because you lose cells and
// plasma together, which is why a hematocrit is misleading early, and it shows up in the flow term instead.
// that split is the physiologically honest one.
// 2. vasoconstriction cannot hide. cardiac output is computed from preload and rate, and deliberately not from
// blood pressure. MAP is cardiac output times systemic resistance, so a clamped-down casualty holds a
// respectable pressure on a terrible output. deriving delivery from MAP would have reproduced exactly the trap
// this system exists to expose.
// 3. tachycardia compensates, up to a point, which is what compensated shock is.
// call it as [_unit] call ACME_fnc_oxygenDelivery, which returns DO2 as a fraction of normal, and 1.0 when the
// system is off.

params ["_unit"];
if (isNil "_unit" || {isNull _unit}) exitWith { 1 };
if !(missionNamespace getVariable ["ACME_sys_do2", true]) exitWith { 1 };

private _blood  = _unit getVariable ["ACM_circulation_Blood_Volume", 6];
private _saline = _unit getVariable ["ACM_circulation_Saline_Volume", 0];
private _plasma = _unit getVariable ["ACM_circulation_Plasma_Volume", 0];
private _normal = (missionNamespace getVariable ["ACME_do2_normalVolume", 6]) max 0.1;

private _total = (_blood + _saline + _plasma) max 0.1;

// An analytic anchor makes decay independent of read frequency and client ownership.
// Publish only initial state or an actual saline-volume change; unchanged saline decays locally.
private _now = CBA_missionTime;
private _anchor = _unit getVariable ["ACME_do2_dilution", []];
private _missingAnchor = !(_anchor isEqualType [] && {count _anchor == 3});
if (_missingAnchor) then {_anchor = [_saline, _saline, _now];};
_anchor params ["_previousEffective", "_previousActual", "_at"];
private _half = (missionNamespace getVariable ["ACME_do2_crystalloidHalfLife", 1200]) max 1;
private _dilEff = (_previousEffective max 0) * (2 ^ (-((_now - _at) max 0) / _half));
if (_saline < _previousActual && {_previousActual > 0}) then {
    _dilEff = _dilEff * (_saline / _previousActual);
};
_dilEff = (_dilEff + ((_saline - _previousActual) max 0)) max 0 min (_saline max 0);
if (local _unit && {(_missingAnchor && {_saline > 0}) || {_saline != _previousActual}}) then {
    _unit setVariable ["ACME_do2_dilution", [_dilEff, _saline, _now], true];
};
private _effTotal = (_blood + _dilEff + _plasma) max 0.1;
private _hbConc = (_blood / _effTotal) min 1;
private _sao2   = ((_unit getVariable ["ace_medical_spo2", 97]) / 100) max 0 min 1;

// flow. the preload comes from the total circulating volume and the rate from the actual heart rate. never from
// blood pressure.
// stroke volume falls faster than volume does. a linear preload term is wrong and produced a nonsense result on
// the first pass: a class ii hemorrhage came out with higher delivery than a healthy casualty, because the
// tachycardia multiplied through faster than the volume loss divided. real ventricles do not work that way.
// losing preload costs stroke volume super-linearly, because the frank-starling curve is steep in that region,
// so the exponent below is what stops compensation outrunning the injury.
private _volFrac = (_total / _normal) min (missionNamespace getVariable ["ACME_do2_preloadCeiling", 1.1]);
private _svFrac = _volFrac ^ (missionNamespace getVariable ["ACME_do2_preloadExponent", 1.6]);
// Septic capillary leak/relative hypovolemia is a preload effect, not a fake loss of red-cell mass.
_svFrac = _svFrac * ((_unit getVariable ["ACM_infection_Preload_Mult", 1]) max 0.55 min 1);

// positive pressure ventilation against preload.
// spontaneous breathing draws air in by making the chest negative relative to atmosphere, and that same negative
// pressure pulls venous blood back to the heart. positive pressure ventilation inverts it: every breath pushes
// intrathoracic pressure up, which opposes venous return. in someone with a full tank that costs almost nothing,
// because there is plenty of pressure in the venous system to overcome it. in someone who is empty it can be
// enough to stop filling the right heart altogether, which is why peri-intubation arrest kills hypovolaemic
// patients. the tube goes in, the bagging starts, and the preload they were only just maintaining disappears.
// so the penalty is gated on emptiness rather than applied flat. a euvolaemic casualty on the vent loses
// essentially nothing, and a class iii casualty loses a real fraction of what stroke volume they had left. that
// makes filling them before you tube them a thing the model rewards rather than a slogan.
// ACM core/fnc_bvmActive.sqf reads the active provider. BVM_Medic includes paused bagging.
private _ventDriving = (_unit getVariable ["ACME_vent_connected", false])
    && {_unit getVariable ["ACME_vent_driving", false]};
private _ppvOn = _ventDriving || {[_unit] call ACM_core_fnc_bvmActive};
if (_ppvOn) then {
    // 1 when full, rising toward 0 as the tank empties.
    private _emptiness = 1 - ((_volFrac / (missionNamespace getVariable ["ACME_do2_preloadCeiling", 1.1])) min 1);
    private _maxPen = missionNamespace getVariable ["ACME_ppv_maxPreloadPenalty", 0.35];
    private _onset  = missionNamespace getVariable ["ACME_ppv_onsetEmptiness", 0.12];
    private _pen = linearConversion [_onset, 1, _emptiness, 0, _maxPen, true];
    // PEEP and a high mean airway pressure make it worse. read the set PEEP if the vent is driving.
    private _peep = 5;
    if (_ventDriving) then {
        private _effective = [_unit] call ACME_fnc_ventEffectiveSettings;
        _peep = if (_effective select 0) then {_effective select 5} else {_unit getVariable ["ACME_vent_peep", 5]};
    };
    _pen = _pen * (linearConversion [5, 15, _peep, 1, (missionNamespace getVariable ["ACME_ppv_peepMaxMult", 1.5]), true]);
    _svFrac = _svFrac * ((1 - _pen) max 0.25);
};

// tachycardia compensates only partly, which is what compensated shock actually is: the rate buys you time and
// does not restore output. it is damped to roughly 40 percent efficiency and capped, so a fast heart can never
// paper over a volume deficit entirely. this is the term that makes a normal blood pressure, normal sats and a
// heart rate of 140 read as the dangerous state it is rather than as a patient who is fine.
private _hr     = _unit getVariable ["ace_medical_heartRate", 75];
private _hrRef  = (missionNamespace getVariable ["ACME_do2_refHR", 75]) max 20;
private _comp   = missionNamespace getVariable ["ACME_do2_hrCompEfficiency", 0.4];
private _hrFrac = 1 + (((_hr / _hrRef) - 1) * _comp);
_hrFrac = (_hrFrac max 0.3) min (missionNamespace getVariable ["ACME_do2_hrCompCeiling", 1.35]);

// very fast rates stop filling. past the knee, diastole is too short to load the ventricle and the output falls
// again. it is scaled by the preload deficit, because that is why it happens: a full ventricle fills fine at 160
// and an empty one does not. applying it flat penalised a euvolemic casualty who was simply tachycardic from
// pain or adrenaline, which is not a delivery problem and is not something a medic should be punished for.
private _tachyKnee = missionNamespace getVariable ["ACME_do2_tachyKneeHR", 150];
if (_hr > _tachyKnee) then {
    private _rawKnee = linearConversion [_tachyKnee, 220, _hr, 1, 0.45, true];
    private _emptiness = 1 - (_volFrac min 1);  // 0 when full and 1 when empty.
    _hrFrac = _hrFrac * (1 - ((1 - _rawKnee) * _emptiness));  // a full ventricle takes no penalty at all.
};

private _co = _svFrac * _hrFrac;

// normalized so a healthy casualty reads 1.0 rather than 0.97.
private _ref = (missionNamespace getVariable ["ACME_do2_refSaO2", 0.97]) max 0.01;
private _do2 = (_hbConc * _sao2 * _co) / _ref;

_do2 max 0
