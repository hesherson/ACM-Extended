// the saline flush into push-dose epi prep, modeled as a guided sequence on the medic, with no fragile
// draw-dialog plunger plumbing. it is faithful to the bedside recipe for 1:100,000 push-dose epi.
// 1. a prefilled 10 ml saline flush.
// 2. waste 1 ml, leaving 9 ml, so the total returns to 10 ml after the epi.
// 3. draw 1 ml of 1:10,000 cardiac epi, which is 100 mcg, giving 10 ml at 10 mcg/ml, which is 1:100,000.
// the result is a push-dose syringe holding n 1 ml, 10 mcg, pushes.
// _this is the ACE callback [_medic, _patient, _bodyPart] plus a bound [_mode].
params ["_medic", "_patient", "_bodyPart", "_args"];
_args params [["_mode", "prep"]];

private _flush = _medic getVariable ["ACME_flush_State", []];  // [volumeml, wastedml, hasepi].

switch (_mode) do {

    case "prep": {
        private _receipt = [_medic,_patient,["ACM_SalineFlush_10"]] call ACME_fnc_treatmentSupplyTake;
        if (_receipt isEqualTo []) exitWith {
            ["No 10 mL saline flush in inventory.", 2, _medic] call ace_common_fnc_displayTextStructured;
        };
        [_receipt,false] call ACME_fnc_treatmentSupplyRefund;
        _medic setVariable ["ACME_flush_State", [10, 0, false], true];
        ["Saline flush ready: 10 mL, plunger full. Waste 1 mL, then draw epi.", 2.5, _medic] call ace_common_fnc_displayTextStructured;
    };

    // a one-shot for the syringe kit: the whole 1:100,000 push-dose prep in a single action, consuming a 10 ml saline
    // flush and an epi vial. it gives the same result as prep, then waste, then drawepi: 1 ml of 1:10,000 cardiac
    // epi, 100 mcg, into a 9 ml flush, giving 10 ml at 10 mcg/ml and 10 pushes.
    case "pushDoseOneShot": {
        if !([_medic] call ACME_fnc_epinephrinePrepare) then {
            ["Need a 10 mL saline flush and 1 mL of epinephrine 1:10,000 (0.1 mg/mL).", 4, _medic] call ace_common_fnc_displayTextStructured;
        };
    };

    case "waste": {
        if (_flush isEqualTo []) exitWith {["Prepare a saline flush first.", 2, _medic] call ace_common_fnc_displayTextStructured;};
        _flush params ["_vol", "_wasted", "_hasEpi"];
        if (_hasEpi) exitWith {["Already push-dose epi - don't waste the mix.", 2, _medic] call ace_common_fnc_displayTextStructured;};
        private _step = 1;
        _vol = (_vol - _step) max 0;
        _wasted = _wasted + _step;
        _medic setVariable ["ACME_flush_State", [_vol, _wasted, false], true];
        [format ["Wasted %1 mL - flush now %2 mL.", _step, _vol], 2, _medic] call ace_common_fnc_displayTextStructured;
    };

    case "drawEpi": {
        if !([_medic, true] call ACME_fnc_epinephrinePrepare) then {
            ["Leave exactly 9 mL saline (waste 1 mL), and carry at least 1 mL of 1:10,000 epinephrine. The 1:1,000 vial cannot be used here.", 5, _medic] call ace_common_fnc_displayTextStructured;
        };
    };

    // a field shortcut: draw an empty flush straight from a hung dirty-epi bag, where 1 mg in 1 l of ns is 1 mcg/ml.
    // 10 ml drawn is 10 mcg, which is exactly one push-dose charge, identical to one push from a prepared 1:100,000
    // syringe. _patient is whoever has the dirty-epi bag hung.
    case "drawDirty": {
        ["Bag-derived push-dose shortcuts are retired. Waste 1 mL from a 10 mL flush and draw 1 mL of 1:10,000 epinephrine.", 5, _medic] call ace_common_fnc_displayTextStructured;
    };

    // pull a push-dose straight from a prepared, not yet hung, push-dose epi bag in the kit of the medic.
    // the clinical rule is that a push-dose pressor can only be pulled from a 1 mg epinephrine in 100 ml ns bag. that
    // mix is 10 mcg/ml, so 1 ml drawn is 10 mcg, which is one push-dose charge. any other epi concentration, such as
    // a dirty 1 mg in 1 l drip or a tighter mix, is not a push-dose source and is rejected. we draw 1 ml and
    // decrement both the volume and the proportional dose, so the remaining bag stays at 10 mcg/ml.
    case "drawDirtyPrep": {
        ["Bag-derived push-dose shortcuts are retired. Waste 1 mL from a 10 mL flush and draw 1 mL of 1:10,000 epinephrine.", 5, _medic] call ace_common_fnc_displayTextStructured;
    };

    // flush the selected iv or io site of the patient. it delivers only the push meds parked in that line and site,
    // meaning adenosine, amiodarone, calcium and push-dose epi. see ACME_flushReqMeds. each parked dose fires the same
    // medicationlocal event a normal push would, so the drug actually circulates. it consumes one 10 ml saline flush
    // even if no med was pending, because a plain post-med or post-site flush is still valid.
    case "flushLine": {
        if (isNull _patient || {!local _medic}) exitWith {};
        if (([_medic,_patient,"ACM_SalineFlush_10"] call ACME_fnc_treatmentSupplyCount) < 1) exitWith {};
        private _site = _args param [1, -2];
        private _present = if (_site >= 0) then {[_patient, _bodyPart, 0, _site] call ACM_circulation_fnc_hasIV} else {
            if (_site == -1) then {[_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIO} else {
                ([_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIV) || {[_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIO}
            }
        };
        if (!_present || {_medic distance _patient > 5 && {isNull objectParent _medic || {objectParent _medic != objectParent _patient}}}) exitWith {};
        private _receipt = [_medic,_patient,["ACM_SalineFlush_10"]] call ACME_fnc_treatmentSupplyTake;
        if (_receipt isEqualTo []) exitWith {};
        [_medic, _patient, _bodyPart, [], "flush", _site, [[],[],[],[_receipt]]] call ACME_fnc_medicationRequest;
        [_patient, "activity", "%1 flushed %2 IV/IO access", [[_medic, false, true] call ace_common_fnc_getName, _bodyPart]] call ace_medical_treatment_fnc_addToLog;
    };
};
