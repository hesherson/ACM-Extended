#include "\x\ACM\addons\circulation\script_component.hpp"
/*
 * Author: Glowbal
 * Calculates the blood volume change and decreases the IVs given to the unit.
 *
 * Arguments:
 * 0: The Unit <OBJECT>
 * 1: Time since last update <NUMBER>
 * 2: Global Sync Values (fluid bags) <BOOL>
 *
 * Return Value:
 * Blood volume <NUMBER>
 *
 * Example:
 * [player, 1, true] call ACM_circulation_fnc_getBloodVolumeChange
 *
 * Public: No
 */

params ["_unit", "_deltaT", "_syncValues"];
private _acmeBinding = "NA4:getBloodVolumeChange";
private _acmeReconcile = "B106:volumeCanonical";
if (!local _unit) exitWith {_unit getVariable ["ace_medical_bloodVolume", 6]};
_deltaT = (_deltaT max 0) min 5; // explicit stalled-frame cap shared by the owner integration
[_unit] call ACME_fnc_syncPremixedBags;

_unit setVariable ["ACME_infusion_getBloodVolumeChangePatched", CBA_missionTime, false];

// B107: progressive bandage control is time-dependent.  Re-evaluate the wound bleed rate immediately before
// integrating blood loss so the circulation model follows the treatment timer instead of waiting for a later
// wound-state mutation.
private _activeBandageProgress = _unit getVariable [QEGVAR(damage,BandageProgress), createHashMap];
if (_activeBandageProgress isEqualType createHashMap && {count _activeBandageProgress > 0}) then {
    [_unit] call ACEFUNC(medical_status,updateWoundBloodLoss);
};

private _bloodVolume = _unit getVariable [QEGVAR(circulation,Blood_Volume), 6];
private _plasmaVolume = _unit getVariable [QEGVAR(circulation,Plasma_Volume), 0];
private _salineVolume = _unit getVariable [QEGVAR(circulation,Saline_Volume), 0];

private _targetPlateletCount = 3;
private _plateletCount = _unit getVariable [QEGVAR(circulation,Platelet_Count), 3];
private _plateletCountChange = 0;

private _bloodVolumeChange = 0;
private _plasmaVolumeChange = 0;
private _salineVolumeChange = 0;

private _transfusedBloodVolume = _unit getVariable [QEGVAR(circulation,TransfusedBlood_Volume), 0];
private _transfusedBloodVolumeChange = 0;

private _reactionBloodVolume = _unit getVariable [QEGVAR(circulation,HemolyticReaction_Volume), 0];
private _reactionBloodVolumeChange = 0;

private _activeVolumes = 0;

private _bloodLoss = -_deltaT * GET_BLOOD_LOSS(_unit);
private _internalBleeding = -_deltaT * GET_INTERNAL_BLEEDRATE(_unit);
private _capillaryBleeding = -_deltaT * GET_CAPILLARYDAMAGE_BLEEDRATE(_unit);
// B102: junctional hemorrhage publishes a rate instead of writing blood volume in its own PFH. Keep that
// contribution as a separate blood-only change so junctionals retain their tuned severity without a second
// runtime-state update in the same tick.
private _junctionalBloodLoss = -_deltaT * ((_unit getVariable ["ACME_junctionalBleedLPS", 0]) max 0);

// citrate-induced hypocalcemia from a massive transfusion is coagulopathic, because ionized calcium is factor
// iv. circhandle owns ionized ca and publishes a coag multiplier of 1 or more, and it is applied to every
// bleeding channel here. it also enrolls the patient in the circ loop once transfusion crosses the citrate
// threshold, so hypocalcemia computes even for a pure blood transfusion with no medication drip running.
if (_transfusedBloodVolume > (missionNamespace getVariable ["ACME_ca_citrateThreshold", 1.0]) && {!isNil "ACME_circ_activePatients"}) then {
    ACME_circ_activePatients pushBackUnique _unit;
};
private _acmeCoag = _unit getVariable ["ACME_ca_coagMult", 1];
if (_acmeCoag > 1) then {
    _bloodLoss = _bloodLoss * _acmeCoag;
    _internalBleeding = _internalBleeding * _acmeCoag;
    _capillaryBleeding = _capillaryBleeding * _acmeCoag;
};

// permissive hypotension. bleeding scales with the pressure driving it, so resuscitating a casualty with
// uncontrolled hemorrhage up to a normal pressure now costs blood instead of being free. see
// fn_permhypobleedmult for the model. it is MAP over a reference MAP, so at target it is exactly 1.0 and
// nothing about the previous balance moves.
// it is applied to the two arterial channels only. open-wound loss and internal bleeding are both driven by mean
// arterial pressure, and internal bleeding is the one that matters most here, because a truncal bleed you
// cannot reach is the textbook case for accepting a low pressure. capillary oozing is deliberately left alone,
// because it is a surface phenomenon that does not track MAP the same way.
// ACE already returns zero from both channels for a bandaged or tourniqueted wound, so this can only ever act on
// bleeding that is still uncontrolled. a controlled wound multiplies zero and stays zero.
private _acmePermHypo = [_unit] call ACME_fnc_permHypoBleedMult;
if (_acmePermHypo != 1) then {
    _bloodLoss = _bloodLoss * _acmePermHypo;
    _internalBleeding = _internalBleeding * _acmePermHypo;
    _unit setVariable ["ACME_permHypo_bleedMult", _acmePermHypo, false];
};

private _inCardiacArrest = IN_CRDC_ARRST(_unit);
// B116: fluid admission requires forward circulation. Use actual mechanical cardiac output as the native guard,
// with CPR as the only substitute in arrest. The ordinary gauge/site flow curve remains unchanged whenever
// forward output exists; this is a zero-output safety gate, not a new arbitrary resuscitation-rate curve.
private _cprActiveForFlow = [_unit] call EFUNC(core,cprActive);
private _nativeCOForFlow = [_unit] call ACEFUNC(medical_status,getCardiacOutput);
if (!(_nativeCOForFlow isEqualType 0) || {!finite _nativeCOForFlow}) then {_nativeCOForFlow = 0;};
private _fluidPerfusionOpen = _cprActiveForFlow || {!_inCardiacArrest && {_nativeCOForFlow > 0.0001}};
_unit setVariable ["ACME_fluidFlowPerfusionBlocked", !_fluidPerfusionOpen, false];

private _TXAEffect = ([_unit, "TXA_IV", false] call ACEFUNC(medical_status,getMedicationCount));

private _internalBleedingSeverity = 0;

if (GET_INTERNAL_BLEEDING(_unit) > 0.3 || (_plateletCount < 0.1 && _TXAEffect < 0.1)) then {
    _internalBleedingSeverity = 1;
};

private _HTXState = _unit getVariable [QEGVAR(breathing,Hemothorax_State), 0];
private _hemothoraxBleeding = 0;

// B135: cardiac arrest must not switch coagulation off. These ratios describe clot/platelet protection of an
// existing hemorrhage source, not forward fluid delivery. CPR can restore enough pressure to make a source bleed
// again, but platelets already at the wound still function and systemically-delivered TXA does not vanish when the
// rhythm becomes pulseless. Keep the normal platelet protection during arrest; flow gating remains separate below.
private _plateletBleedRatio = (0.8 min (linearConversion [2.9, 1.8, _plateletCount, 0.8, 0.5]) max 0);
private _plateletInternalBleedRatio = (0.8 min (linearConversion [2.4, 1.6, _plateletCount, 0.8, 0.5]) max 0);

if (_HTXState > 0) then {
    _hemothoraxBleeding = -_deltaT * GET_HEMOTHORAX_BLEEDRATE(_unit);
    private _thoraxBlood = _unit getVariable [QEGVAR(breathing,Hemothorax_Fluid), 0];
    _thoraxBlood = _thoraxBlood - (_hemothoraxBleeding * (1 - _plateletBleedRatio));
    _unit setVariable [QEGVAR(breathing,Hemothorax_Fluid), (_thoraxBlood min 1.5), _syncValues];
};

private _incisionBleedRate = GET_SURGICAL_AIRWAY_BLEEDRATE(_unit);

if (_incisionBleedRate > 0 && !(_unit getVariable [QEGVAR(airway,SurgicalAirway_IncisionStitched), false])) then {
    _bloodLoss = _bloodLoss + (-_deltaT * _incisionBleedRate);
};

if (_bloodVolume > 0) then {
    _activeVolumes = _activeVolumes + 1;
};

if (_plasmaVolume > 0) then {
    _activeVolumes = _activeVolumes + 1;
};

if (_salineVolume > 0) then {
    _activeVolumes = _activeVolumes + 1;
};

if (_plateletCount > 0.1) then {
    if (_TXAEffect > 0.5) then {
        _bloodLoss = _bloodLoss * (linearConversion [0.5, 2, _TXAEffect, 1, 0.9, true]);
        _internalBleeding = _internalBleeding * (linearConversion [0.5, 2, _TXAEffect, 1, 0.85, true]);
        _hemothoraxBleeding = _hemothoraxBleeding * (linearConversion [0.5, 2, _TXAEffect, 1, 0.8, true]);
        _capillaryBleeding = _capillaryBleeding * (linearConversion [0.5, 2, _TXAEffect, 1, 0.85, true]);
    };

    _plateletCountChange = (_bloodLoss * _plateletBleedRatio) + ((_internalBleeding * 0.6) * _plateletInternalBleedRatio) + (_hemothoraxBleeding * _plateletBleedRatio) + (_capillaryBleeding * _plateletBleedRatio);

    if (_TXAEffect > 0.1) then {
        _plateletCountChange = _plateletCountChange * 0.9;
    };
};

if (_bloodVolume > 0) then {
    _bloodVolumeChange = ((_bloodLoss * (1 - _plateletBleedRatio)) + ((_internalBleeding * _internalBleedingSeverity) * (1 - _plateletInternalBleedRatio)) + (_hemothoraxBleeding * (1 - _plateletBleedRatio)) + (_capillaryBleeding * (1 - _plateletBleedRatio))) / _activeVolumes;
    _bloodVolumeChange = _bloodVolumeChange + _junctionalBloodLoss;
};

if (_plasmaVolume > 0) then {
    _plasmaVolumeChange = ((_bloodLoss * (1 - _plateletBleedRatio)) + ((_internalBleeding * _internalBleedingSeverity) * (1 - _plateletInternalBleedRatio)) + (_hemothoraxBleeding * (1 - _plateletBleedRatio)) + (_capillaryBleeding * (1 - _plateletBleedRatio))) / _activeVolumes;
};

if (_salineVolume > 0) then {
    _salineVolumeChange = ((_bloodLoss * (1 - _plateletBleedRatio)) + ((_internalBleeding * _internalBleedingSeverity) * (1 - _plateletInternalBleedRatio)) + (_hemothoraxBleeding * (1 - _plateletBleedRatio)) + (_capillaryBleeding * (1 - _plateletBleedRatio))) / _activeVolumes;
};

private _transfusionPain = 0;
private _freshBloodEffectiveness = 0;

// the blood warmer, the LifeWarmer quantum. when the blood line of this patient is flagged warmed, every ml of
// blood that actually transfuses this tick adds a little heat toward 37 c. it accumulates across all bags and
// body parts and applies once after the bag loop. _bloodBagsPresent tracks whether any blood bag is still hung,
// so the warmed flag self-clears when the last one is pulled, which prevents a stale flag warming a later
// unwarmed bag.
private _warmedFlag = _unit getVariable ["ACME_warmedBlood", false];
private _coldFlag = _unit getVariable ["ACME_coldBlood", false];
// cold blood rewarms thermally toward ambient over ACME_bloodRewarmTime, which defaults to 20 min, once hung
// outside the cold chain. _coldFrac now scales only the transfusion-hypothermia effect. Throughput is deliberately
// origin-based while the cold unit remains hung: cold-stored blood stays on the 100/200/300 flow ladder instead of
// gradually reverting to the room-temperature flow curve.
private _coldFrac = 0;
if (_coldFlag) then {
    private _hungAt = _unit getVariable ["ACME_coldBloodHungAt", CBA_missionTime];
    private _rewarm = (missionNamespace getVariable ["ACME_bloodRewarmTime", 1200]) max 1;
    _coldFrac = (1 - ((CBA_missionTime - _hungAt) / _rewarm)) max 0 min 1;
};
private _warmerTempPerLiter = missionNamespace getVariable ["ACME_warmer_tempPerLiter", 0.8];
private _warmthAdd = 0;
private _coolDrop = 0;
private _bloodBagsPresent = false;

// The authoritative bag map decides whether the infusion worker runs. IV_Bags_Active is only a cache.
private _fluidBags = _unit getVariable [QEGVAR(circulation,IV_Bags), createHashMap];
private _hasFluidBags = (_fluidBags isEqualType createHashMap) && {count _fluidBags > 0};
private _activeFlag = _unit getVariable [QEGVAR(circulation,IV_Bags_Active), false];
if (_activeFlag isNotEqualTo _hasFluidBags) then {
    _unit setVariable [QEGVAR(circulation,IV_Bags_Active), _hasFluidBags, true];
};

if (_hasFluidBags) then {
    private _IVFlowMultiplier = 1;
    private _IOFlowMultiplier = 1;

    private _activeBagTypesIV = _unit getVariable [QEGVAR(circulation,ActiveFluidBags_IV), ACM_IV_PLACEMENT_DEFAULT_1];
    private _activeBagTypesIO = _unit getVariable [QEGVAR(circulation,ActiveFluidBags_IO), ACM_IO_PLACEMENT_DEFAULT_1];

    if (!_fluidPerfusionOpen) then {
        _IVFlowMultiplier = 0;
        _IOFlowMultiplier = 0;
    } else {
        if (_inCardiacArrest && {_cprActiveForFlow}) then {
            // Preserve ACM's reduced arrest-flow calibration once CPR is actually producing forward perfusion.
            _IVFlowMultiplier = 0.9;
            _IOFlowMultiplier = 1;
        };
    };

    private _fluidBags = _unit getVariable [QEGVAR(circulation,IV_Bags), createHashMap];

    private _updateCountBodyPartArray = [];

    {
        private _targetBodyPart = _x;
        private _partIndex = GET_BODYPART_INDEX(_targetBodyPart);

        private _fluidBagsBodyPart = _y;

        _fluidBagsBodyPart = _fluidBagsBodyPart apply {
            private _acmeBagIndex = _forEachIndex;
            _x params ["_type", "_bagVolumeRemaining", "_accessType", "_accessSite", "_iv", ["_bloodType", -1], "_originalVolume", ["_freshBloodID", -1], ["_bagUid", ""]];
            // y-line membership at the body-part level, ignoring iv, io and the site. this is the loosest and most robust
            // match. a y reserve saline must never drain on its own, and matching any y line on this body part cannot miss
            // on access-site or iv and io bookkeeping, or on a not-yet-synced or late retag. the "#" guard keeps "body#"
            // from matching a different part. over-clamping a separate same-part saline is the deliberate, safe trade,
            // because the hard requirement is that saline holds until flush line.
            private _bpLC = toLower _targetBodyPart;
            private _onYLine = [_unit, _targetBodyPart, _iv, _accessSite] call ACME_fnc_isYLineAccess;
            if (_bagUid == "") then {_bagUid = [_unit, _targetBodyPart, _acmeBagIndex] call ACME_fnc_bagIdentity;};
            private _acmeOriginalBag = +_x; _acmeOriginalBag set [8, _bagUid];
            // two kinds of entry are returned untouched, with no drain, no blood math and no removal.
            // a persisted [empty bag] marker, which is a y-tubing slot waiting for the next unit.
            // and the y saline limb. a saline bag sitting on a y line is the flush reserve and must never waste a drop on
            // its own, and only the flush line button bleeds it. it is clamped whether or not the post-attach retag has yet
            // swapped its type to ACME_SalineY, because that retag can race the medical tick or be dropped on a menu
            // rebuild, so an untagged "Saline" on a y line is held clamped just the same.
            // this uses if, then and else rather than exitwith, because an exitwith inside apply would abort the whole
            // function rather than this element alone.
            private _isYSaline = _type in ["ACME_SalineY"] || {_onYLine && {_type == "Saline"}};
            private _detached = _unit getVariable ["ACME_detachedBags", []];
            private _heldDetached = _bagUid in _detached;
            if (_heldDetached && {([_unit, _partIndex, _iv, _accessSite, -1] call ACM_circulation_fnc_getIVFlowRate) > 0}) then {
                _heldDetached = false;
                [_unit, "ACME_detachedBags", _detached - [_bagUid]] call ACME_fnc_setVarNet;
            };
            if (_heldDetached || {_type in ["ACME_Empty", "ACME_EmptySaline"]} || {_isYSaline}) then {
                if (_isYSaline && {_type == "Saline"}) then {
                    // self-heal a missed or late menu retag. a plain saline on a y line is the reserve, so it is returned
                    // permanently re-typed as ACME_SalineY. from the next tick the type-based clamp holds it with no dependence on
                    // ylines sync or timing at all. this is what makes the reserve hold for good.
                    ["ACME_SalineY", _bagVolumeRemaining, _accessType, _accessSite, _iv, _bloodType, _originalVolume, _freshBloodID, _bagUid]
                } else { _x };
            } else {

            // warmer lifetime. note that a blood bag is hung here, whatever the flow state, so the warmed flag persists
            // while paused and clears only once the last blood bag is removed.
            if (_type in ["Blood", "FreshBlood"]) then { _bloodBagsPresent = true; };


            if ((!([_unit, _partIndex] call ACME_fnc_aajtOccludes)) && ((!(HAS_TOURNIQUET_APPLIED_ON(_unit,_partIndex)) || (!_iv && (_partIndex in [2,3]))) && (([(GET_IO_FLOW_X(_unit,_partIndex)),(GET_IV_FLOW_X(_unit,_partIndex,_accessSite))] select _iv) > 0) && {_type != "FBTK" || {_type == "FBTK" && (_bagVolumeRemaining <= _originalVolume && _iv)}})) then {
                private _fluidFlowRate = 1;
                private _fluidPassRatio = 1;
                private _uniqueFreshBloodEntry = [];

                switch (_type) do {
                    case "Blood": {
                        _fluidFlowRate = 0.8;
                    };
                    case "FBTK";
                    case "PlasmaLyte";
                    case "Saline": {
                        _fluidFlowRate = 1.2;
                    };
                    case "FreshBlood": {
                        _uniqueFreshBloodEntry = [_freshBloodID] call EFUNC(circulation,getFreshBloodEntry);

                        private _timeEffect = ((0.67 max (900 / ((CBA_missionTime - (_uniqueFreshBloodEntry param [4, CBA_missionTime])) max 0.001))) min 1);

                        _fluidFlowRate = ([0.8, (1.2 * _timeEffect)] select (_uniqueFreshBloodEntry select 3));
                        _freshBloodEffectiveness = _timeEffect;
                    };
                    default {};
                };

                private _activeBagTypesBodyPart = [(_activeBagTypesIO select _partIndex),((_activeBagTypesIV select _partIndex) select _accessSite)] select _iv;

                private _acmeControlledFlow = false;
                private _acmeBagClamp = -1; // Never inherit another bag's site-cache value.
                private _acmeEntries = _unit getVariable ["ACME_infusion_BagMedications", []];
                private _acmeEI = _acmeEntries findIf {(_x param [23, ""]) == _bagUid};
                if (_acmeEI >= 0) then {
                    _acmeControlledFlow = true;
                    _acmeBagClamp = [_unit, _acmeEntries select _acmeEI] call ACME_fnc_infusionFlow;
                };
                private _bagChange = 0;
                if (_acmeControlledFlow) then {
                    _bagChange = (_deltaT * ([_unit, _partIndex, _iv, _accessSite, _acmeBagClamp, _bagUid] call EFUNC(circulation,getIVFlowRate)) * ([_IOFlowMultiplier, _IVFlowMultiplier] select _iv)) min _bagVolumeRemaining;
                } else {
                    _bagChange = ((_deltaT * ACEGVAR(medical,ivFlowRate) * ([_unit, _partIndex, _iv, _accessSite, _acmeBagClamp, _bagUid] call EFUNC(circulation,getIVFlowRate))) * ([_IOFlowMultiplier, _IVFlowMultiplier] select _iv) * _fluidFlowRate);  // the absolute value of the change, in milliliters.

                    if (_type == "FBTK") then {
                        // native ACM fills an FBTK at 1.2 times the saline flow, which is about 5 ml/s on a 16g and about 7.5 on a 14g.
                        // ACME_fbtk_fillMult scales that if the collection feels too slow, and 1 is the stock ACM rate.
                        _bagChange = _bagChange * (missionNamespace getVariable ["ACME_fbtk_fillMult", 1]);
                        _bagChange = _bagChange min (_originalVolume - _bagVolumeRemaining);
                    } else {
                        _bagChange = _bagChange min _bagVolumeRemaining;
                    };



                    if (_bagVolumeRemaining > 1) then {
                        // THIS IS THE NON FINITE BLOOD VOLUME. The divisor was not guarded.
                        // _activeBagTypesBodyPart is ACM's count of active bag types at this access site.
                        // The count is 0 while a bag is present and is not flowing, which is any clamped bag.
                        // The loop still reaches this line for that bag, so the division was a division by zero.
                        // SQF returns a non finite number for that, and _bagChange carries it into
                        // _bloodVolumeChange, _plasmaVolumeChange and _salineVolumeChange a few lines below.
                        // The unit then holds a non finite blood volume for the rest of the mission, because
                        // every later sum of it is also non finite.
                        // ACE then reports "Type Number, Not a Number" from getCardiacOutput on every frame, and
                        // the heart rate, the blood pressure and the cardiac output stop working for that casualty.
                        // ACM stock has no divisor. This division is ours, so this fault is ours.
                        // The divisor is a count of bags to share the flow between. One bag is the minimum,
                        // because this loop is running for a bag.
                        private _divisor = _activeBagTypesBodyPart max 1;
                        // on a y line the paired saline is clamped, so it counts as an active type and is not flowing. do not let it
                        // dilute the flow of the blood, so drop it from the divisor for blood and fresh blood.
                        if ((_type in ["Blood", "FreshBlood"]) && _onYLine) then {
                            _divisor = (_divisor - 1) max 1;
                        };
                        _bagChange = _bagChange / _divisor;
                    };
                };

                // Blood has an explicit device/temperature flow envelope at the FINAL owner-side drainer.
                // This is intentionally after the normal gauge/Hang Bag/pressure calculation so non-blood fluids keep
                // their existing physics, while every blood path shares one authoritative 300 mL/min hard ceiling.
                //
                // Cold-stored blood: 100 mL/min baseline, 200 with Hang Bag.
                // LifeWarmer + non-cold blood: 200 mL/min.
                // An actively pressurized cuff is the universal top blood tier: 300 mL/min for cold, warmed or ordinary
                // room-temperature blood. The cuff's existing bleed-off still determines when it stops being active and
                // needs to be repumped; while it has usable pressure, its blood-flow target is exactly 300 mL/min.
                if (_type in ["Blood", "FreshBlood"]) then {
                    private _bloodCap = (missionNamespace getVariable ["ACME_bloodMax_mlPerMin", 300]) max 1;
                    private _coldBase = (missionNamespace getVariable ["ACME_coldBlood_mlPerMin", 100]) max 0;
                    private _coldHang = (missionNamespace getVariable ["ACME_coldBloodHang_mlPerMin", 200]) max _coldBase;
                    private _warmBase = (missionNamespace getVariable ["ACME_warmedBlood_mlPerMin", 200]) max 0;

                    private _hangActive = (_unit getVariable ["ACME_hang_flowMult", 1]) > 1.001;

                    private _pressureActive = false;
                    private _cuff = (_unit getVariable ["ACME_piCuffs", createHashMap]) getOrDefault [_bagUid, []];
                    if (_bagUid != "" && {!(_cuff isEqualTo [])}) then {
                        _cuff params [["_at", 0], ["_p0", 1]];
                        private _half = (missionNamespace getVariable ["ACME_pi_bleedHalfLifeSec", 150]) max 0.1;
                        private _p = (_p0 * (2 ^ (-((CBA_missionTime - _at) max 0) / _half))) max 0 min 1;
                        _pressureActive = _p >= 0.08;
                    };

                    private _fixedRate = -1;
                    if (_pressureActive) then {
                        // Pressure infusion is the universal top blood tier, including ordinary room-temperature blood.
                        _fixedRate = _bloodCap;
                    } else {
                        if (_coldFlag) then {
                            // Cold-chain origin wins over the warmer flag for FLOW. The LifeWarmer still supplies heat,
                            // but a cold unit remains at 100 mL/min unless Hang Bag raises it to 200.
                            _fixedRate = [_coldBase, _coldHang] select _hangActive;
                        } else {
                            if (_warmedFlag) then {
                                _fixedRate = _warmBase;
                            };
                        };
                    };

                    if (_fixedRate >= 0) then {
                        _bagChange = _deltaT * ((_fixedRate min _bloodCap) / 60);
                    };

                    // Absolute blood-flow cap, including ordinary room-temperature blood whose gauge + Hang Bag +
                    // pressure multiplier would otherwise exceed the rapid-transfusion ceiling.
                    private _capChange = _deltaT * (_bloodCap / 60);
                    _bagChange = ((_bagChange min _capChange) min _bagVolumeRemaining) max 0;
                };

                // Final perfusion gate after every fixed-rate override, including the blood warmer. No CPR means
                // no forward circulation in arrest, therefore no bag volume may be consumed or credited.
                if (!_fluidPerfusionOpen) then {_bagChange = 0;};

                if (_iv && EGVAR(circulation,IVComplications)) then {
                    private _comp = (GET_IV_COMPLICATIONS_FLOW_X(_unit,_partIndex,_accessSite)) max 0 min 2;
                    _bagChange = _bagChange * ([1,0.9,0.85] select _comp);
                    _fluidPassRatio = [1,1,0.8] select _comp;
                };
                _bagChange = _bagChange max 0;
                _fluidPassRatio = [_unit,_targetBodyPart,if (_iv) then {_accessSite} else {-1}] call ACME_fnc_medicationLineFraction;

                // FBTK runs in the opposite direction from an infusion. The line fraction must reduce how much
                // blood is physically collected, not reduce donor loss after the bag has already been credited.
                // The old order could fill a 500 mL FBTK while removing only a fraction of that from a compromised
                // donor IV. Apply the line loss to collection first, then settle bag gain and donor loss 1:1.
                if (_type == "FBTK") then {
                    _bagChange = _bagChange * _fluidPassRatio;
                    _fluidPassRatio = 1;

                    // Never manufacture donor blood at extreme hypovolemia. External/internal bleeding has already
                    // been accumulated into _bloodVolumeChange above, so this is the blood actually available for
                    // collection in this integration step.
                    private _donorAvailableMl = (((_bloodVolume + _bloodVolumeChange) max 0) * 1000);
                    _bagChange = _bagChange min _donorAvailableMl;
                };

                private _admitted = _bagChange * _fluidPassRatio;
                if (_type != "FBTK") then {
                    [_unit, _targetBodyPart, _acmeBagIndex, _acmeOriginalBag, _bagChange, _admitted, _deltaT] call ACME_fnc_fluidCommit;
                };
                if (_type == "FBTK") then {
                    _bagVolumeRemaining = (_bagVolumeRemaining + _bagChange) min _originalVolume;
                } else {
                    _bagVolumeRemaining = _bagVolumeRemaining - _bagChange;
                };

                switch (_type) do {
                    case "Plasma": {
                        _plasmaVolumeChange = _plasmaVolumeChange + (_admitted / 1000);
                        _plateletCountChange = _plateletCountChange + (_admitted / 600);
                    };
                    case "PlasmaLyte": {
                        // balanced crystalloid. it behaves as saline for volume, so it resuscitates the dehydrated and hypovolaemic
                        // patient, and it carries no platelets, protein or clotting factors, so it is not plasma. its acetate and
                        // gluconate buffer reverses metabolic acidosis as it runs.
                        // it reduces the metabolic component only. respiratory acidosis stays ventilation-driven, and fn_circhandle
                        // reapplies the normal-saline hyperchloremic floor.
                        _salineVolumeChange = _salineVolumeChange + (_admitted / 1000);
                        // Acid/base state has one writer: ACME_fnc_circHandle on its one-second acid clock.
                        // Blood-volume admission can occur in the ACE vital tick, so queue the balanced-fluid
                        // buffering credit here instead of mutating metabolic/total acidosis a second time.
                        private _credit = _unit getVariable ["ACME_plasmaLyteAcidCredit", 0];
                        _credit = _credit + (_admitted * (missionNamespace getVariable ["ACME_plasmaLyte_acidosisPerMl", 0.0008]));
                        _unit setVariable ["ACME_plasmaLyteAcidCredit", _credit, false];
                    };
                    case "Saline": {
                        _salineVolumeChange = _salineVolumeChange + (_admitted / 1000);

                        // ACME_fnc_salineAcidosisTrack handles the ns chloride-load accounting. that watcher observes real IV_Bags
                        // volume loss after ACM's final drainer runs, so normal ACM saline bags and ACME medication-carrier saline are
                        // both credited without depending on this override winning compile order.
                    };
                    case "FBTK": {
                        _bloodVolumeChange = _bloodVolumeChange - (_admitted / 1000);
                        _plateletCountChange = _plateletCountChange - (_admitted / 2000);
                    };
                    default {
                        if ((toLowerANSI _type) in keys ACME_infusion_premixedByType) then {
                            _salineVolumeChange = _salineVolumeChange + (_admitted / 1000);
                        } else {
                        if ([GET_BLOODTYPE(_unit), _bloodType] call EFUNC(circulation,isBloodTypeCompatible) && {_type == "Blood" || (_type == "FreshBlood" && {_uniqueFreshBloodEntry select 3})}) then {
                            _bloodVolumeChange = _bloodVolumeChange + (_admitted / 1000);

                            _transfusedBloodVolumeChange = _transfusedBloodVolumeChange + (_admitted / 1000);

                            // warmed blood contributes heat toward 37 c in proportion to the volume passed. cold, cooler-stored, [cooled]
                            // blood instead pulls the core temperature down by the volume passed, which is the transfusion hypothermia the
                            // tag warns about. normal room-temperature blood, with neither flag, is temperature-neutral. run a cold unit
                            // through the LifeWarmer to flip it to the heat-adding path. the toggle and the rate are CBA-tunable.
                            if (_warmedFlag) then {
                                _warmthAdd = _warmthAdd + ((_admitted / 1000) * _warmerTempPerLiter);
                            } else {
                                if (_coldFlag && {_coldFrac > 0} && {missionNamespace getVariable ["ACME_coldBloodHypothermia", true]}) then {
                                    // the cooling effect scales with how cold the unit still is, so a unit left to rewarm chills less.
                                    _coolDrop = _coolDrop + ((_admitted / 1000) * (missionNamespace getVariable ["ACME_cooler_tempDropPerLiter", 1.1]) * _coldFrac);
                                };
                            };
                        } else {
                            _salineVolumeChange = _salineVolumeChange + (_admitted / 1000);

                            _plateletCountChange = _plateletCountChange - (_admitted / 1000);

                            _reactionBloodVolumeChange = _reactionBloodVolumeChange + (_admitted / 1000);

                            _freshBloodEffectiveness = 0;
                        };
                        };
                    };
                };
                // B45: actual admitted IO fluid is the trigger. This is inside the real bag-volume settlement,
                // so an open clamp with no delivered volume cannot knock the casualty out. The helper debounces the
                // three-second syncope while keeping raw pain at maximum for continued IO flow.
                if (_admitted > 0 && {_accessType in [ACM_IO_FAST1_M, ACM_IO_EZ_M]}) then {
                    [_unit, _targetBodyPart, "fluid"] call ACME_fnc_ioPainResponse;
                };
                // flow pain.
                if (_accessType in [ACM_IO_FAST1_M, ACM_IO_EZ_M]) then {  // io.
                    private _IOPain = _bagChange / 3;
                    private _painSuppression = linearConversion [0, 0.24, ([_unit, "Lidocaine_IV", false, _partIndex] call ACEFUNC(medical_status,getMedicationCount)), 0, 0.95, true];  // a 30 mg "flush".
                    _transfusionPain = _transfusionPain + (0 max (_IOPain - _painSuppression));
                } else {  // an iv complication.
                    private _ivComplicationPain = GET_IV_COMPLICATIONS_PAIN_X(_unit,_partIndex,_accessSite);

                    if (_ivComplicationPain > 0) then {
                        private _flowPain = (_bagChange / 1000) * _ivComplicationPain;
                        _transfusionPain = _transfusionPain + _flowPain;
                    };
                };
            };

            if (_bagVolumeRemaining < 0.01 && {_type != "FBTK"}) then {
                [_unit, _bagUid] call ACME_fnc_infusionRetire;
                if (_type in ["Blood", "FreshBlood"]) then {
                    // any blood unit that drains leaves a persistent [empty blood bag] marker in its slot instead of vanishing,
                    // because stock ACM removes spent bags. the medic sees the spent unit, hanging a new unit on this slot drops
                    // the marker, in fn_transfusionspikeoradd, and stop transfusion clears it.
                    // on a y line we tally the blood transfused since the last flush and only flag the line dirty once 2 units or
                    // about 1 l have run, because a real line does not need a saline flush until the second unit. the tally is
                    // keyed at body-part plus iv or io, and not the site, so a set or clear cannot miss on ACM's site
                    // bookkeeping.
                    if (_onYLine) then {
                        private _ck = toLower (format ["%1#%2#%3", _targetBodyPart, _iv, _accessSite]);
                        private _accU = _unit getVariable ["ACME_YLineUnitsSinceFlush", createHashMap];
                        private _accV = _unit getVariable ["ACME_YLineVolSinceFlush", createHashMap];
                        private _u = (_accU getOrDefault [_ck, 0]) + 1;
                        private _v = (_accV getOrDefault [_ck, 0]) + _originalVolume;
                        _accU set [_ck, _u]; _unit setVariable ["ACME_YLineUnitsSinceFlush", _accU, true];
                        _accV set [_ck, _v]; _unit setVariable ["ACME_YLineVolSinceFlush", _accV, true];
                        if (_u >= (missionNamespace getVariable ["ACME_YFlushAfterUnits", 2]) ||
                            {_v >= (missionNamespace getVariable ["ACME_YFlushAfterVolume", 1000])}) then {
                            private _d = _unit getVariable ["ACME_YLineDirty", createHashMap];
                            _d set [_ck, true];
                            _unit setVariable ["ACME_YLineDirty", _d, true];
                        };
                    };
                    ["ACME_Empty", 0, _accessType, _accessSite, _iv, _bloodType, _originalVolume, _freshBloodID, _bagUid]
                } else {
                    // a non-blood bag, saline or crystalloid, that drains is removed, as ACM does.
                    _updateCountBodyPartArray pushBack _targetBodyPart;
                    []
                }
            } else {
                [_type, (_bagVolumeRemaining min _originalVolume), _accessType, _accessSite, _iv, _bloodType, _originalVolume, _freshBloodID, _bagUid]
            }
            };
        };
        _fluidBags set [_targetBodyPart, _fluidBagsBodyPart];
    } forEach _fluidBags;

    if (count _updateCountBodyPartArray > 0) then {
        _updateCountBodyPartArray arrayIntersect _updateCountBodyPartArray;
        {
            private _targetBodyPart = _x;
            private _targetFluidBagsBodyPart = _fluidBags getOrDefault [_targetBodyPart, []];

            {  // remove the empty bag.
                if ((count _x) < 1) then {
                    _targetFluidBagsBodyPart deleteAt _forEachIndex;
                };
            } forEachReversed _targetFluidBagsBodyPart;

            if (count _targetFluidBagsBodyPart < 1) then {
                _fluidBags deleteAt _targetBodyPart;
            };
        } forEach _updateCountBodyPartArray;

        if (count _fluidBags > 0) then {
            {
                [_unit, _x] call EFUNC(circulation,updateActiveFluidBags);
            } forEach _updateCountBodyPartArray;
        };
    };

    if (count _fluidBags < 1) then {
        _unit setVariable [QEGVAR(circulation,IV_Bags), nil, true];  // no bags are left, so clear the variable. always sync this globally.
        _unit setVariable [QEGVAR(circulation,IV_Bags_Active), false, true];
        [_unit, ""] call EFUNC(circulation,updateActiveFluidBags);
        _unit setVariable [QEGVAR(circulation,IV_Bags_FreshBloodEffect), 0, true];
    } else {
        // The casualty owner changes bag volume every medical tick, but ACM's normal whole-patient sync cadence
        // is too sparse for a remote medic who is actively watching the transfusion menu. Keep the exact map local
        // every tick and publish a changed map at no more than 4 Hz. This makes remote bag volume visibly flow
        // without returning to per-frame network spam.
        private _acmeBagUiSig = str _fluidBags;
        private _acmeBagUiLastSig = _unit getVariable ["ACME_transfusionUiBagSig", ""];
        private _acmeBagUiLastAt = _unit getVariable ["ACME_transfusionUiBagSyncAt", -1];
        private _acmeBagUiChanged = _acmeBagUiSig != _acmeBagUiLastSig;
        private _acmeBagUiPublish = _syncValues || {
            _acmeBagUiChanged && {
                _acmeBagUiLastAt < 0 || {(CBA_missionTime - _acmeBagUiLastAt) >= 0.25}
            }
        };

        _unit setVariable [QEGVAR(circulation,IV_Bags), _fluidBags, _acmeBagUiPublish];
        if (_acmeBagUiPublish) then {
            _unit setVariable ["ACME_transfusionUiBagSig", _acmeBagUiSig, false];
            _unit setVariable ["ACME_transfusionUiBagSyncAt", CBA_missionTime, false];
        };
        _unit setVariable [QEGVAR(circulation,IV_Bags_FreshBloodEffect), _freshBloodEffectiveness, _syncValues];
    };
};

// the blood warmer. fold the accumulated warmth of the tick into the hypothermia temp of the patient, capped at
// 37 c, because a warmer can prevent transfusion-driven cooling and not overheat the patient.
if (_warmthAdd > 0) then {
    private _t = _unit getVariable ["ACME_hypo_temp", 37];
    _unit setVariable ["ACME_hypo_temp", ((_t + _warmthAdd) min 37), _syncValues];
};

// cold, unwarmed, cooler-stored blood. subtract the accumulated cooling of the tick from the hypothermia temp of
// the patient. it is floored at a survivable transfusion-hypothermia bound, so a long unwarmed run drives the
// lethal-triad math and cannot drop the core temp to absurd values on its own.
if (_coolDrop > 0) then {
    private _t = _unit getVariable ["ACME_hypo_temp", 37];
    private _floor = missionNamespace getVariable ["ACME_cooler_tempDropFloor", 30];
    _unit setVariable ["ACME_hypo_temp", ((_t - _coolDrop) max _floor), _syncValues];
};
// self-clear. once no blood bag remains hung, the warmed line is gone, so drop the flag and a later unwarmed bag
// is not silently warmed or colored.
// there is a hold window. ACM's add bag takes time to actually land the bag, and the hang paths assert warmed
// and cold at the button press. without the hold, this clear fired during that window, with the flag true and
// no blood hung yet, and the new unit landed already stripped, so the second bag never showed warmed or cooled.
// the hang paths stamp ACME_tempFlagHoldUntil and the clear waits it out.
if (!_bloodBagsPresent && {CBA_missionTime > (_unit getVariable ["ACME_tempFlagHoldUntil", 0])}) then {
    if (_warmedFlag) then { _unit setVariable ["ACME_warmedBlood", false, true]; };
    if (_coldFlag)   then { _unit setVariable ["ACME_coldBlood", false, true]; };
};

if (_transfusionPain > 0) then {
    [_unit, (_transfusionPain min 0.8)] call ACEFUNC(medical_status,adjustPainLevel);
};

// Native ACM compartment conversion. This is deliberately slow and is NOT the patient's
// hemodynamic volume gain. Plasma/saline already count immediately in the total circulating
// volume returned at the end of this function. The conversion only migrates volume between
// ACM's product compartments over time.
if (_bloodVolume < 6) then {
    private _conversionRateModifier = ([1,2] select (_freshBloodEffectiveness > 0.83));
    if (_plasmaVolume + _plasmaVolumeChange > 0) then {
        private _leftToConvert = _plasmaVolume + _plasmaVolumeChange;
        private _conversionRate = (_deltaT * (0.003 * _conversionRateModifier)) min _leftToConvert;

        _plasmaVolumeChange = _plasmaVolumeChange - _conversionRate;
        _bloodVolumeChange = _bloodVolumeChange + _conversionRate;
    };

    if (_salineVolume + _salineVolumeChange > 0) then {
        private _leftToConvert = _salineVolume + _salineVolumeChange;
        private _conversionRate = (_deltaT * (0.0007 * _conversionRateModifier)) min _leftToConvert;

        _salineVolumeChange = _salineVolumeChange - _conversionRate;
        _bloodVolumeChange = _bloodVolumeChange + _conversionRate;
    };
};

// snapshot the raw, pre-clamp total fluid for the conversion-invariant overload model below. the saline to blood
// conversion above preserves the total volume, because saline goes down and blood goes up by the same amount,
// so this total, and therefore the excess over capacity, is unaffected by conversion. ACM's per-clamp
// _fluidOverloadChange term is not, because conversion keeps it positive forever, which is why overload never
// tapered.
private _acmeRawTotal = (_bloodVolume + _bloodVolumeChange) + (_plasmaVolume + _plasmaVolumeChange) + (_salineVolume + _salineVolumeChange);

private _fluidOverload = _unit getVariable [QEGVAR(circulation,Overload_Volume), 0];
private _fluidOverloadChange = 0;

private _plasmaSpaceRemaining = DEFAULT_BLOOD_VOLUME;
private _salineSpaceRemaining = DEFAULT_BLOOD_VOLUME;

_bloodVolume = 0 max _bloodVolume + _bloodVolumeChange min DEFAULT_BLOOD_VOLUME;
_fluidOverloadChange = _fluidOverloadChange + ((_bloodVolume + _bloodVolumeChange) - DEFAULT_BLOOD_VOLUME);

_plasmaSpaceRemaining = _plasmaSpaceRemaining - _bloodVolume;
_salineSpaceRemaining = _salineSpaceRemaining - _bloodVolume;

_plasmaVolume = 0 max _plasmaVolume + _plasmaVolumeChange min DEFAULT_BLOOD_VOLUME;
_fluidOverloadChange = _fluidOverloadChange + ((_plasmaVolume + _plasmaVolumeChange) - _plasmaSpaceRemaining);

_plasmaVolume = 0 max (_plasmaVolume min _plasmaSpaceRemaining);
_salineSpaceRemaining = _salineSpaceRemaining - _plasmaVolume;

_salineVolume = 0 max _salineVolume + _salineVolumeChange min DEFAULT_BLOOD_VOLUME;
_fluidOverloadChange = _fluidOverloadChange + ((_salineVolume + _salineVolumeChange) - _salineSpaceRemaining);

_salineVolume = 0 max (_salineVolume min _salineSpaceRemaining);

// the fluid-overload model. it replaces ACM's unbounded per-tick integrator, which skyrocketed past 4.0 and
// never tapered, because the saline to blood conversion keeps the per-clamp over-capacity term positive
// forever. this model keys off the conversion-invariant total excess over capacity and behaves exactly as
// specified.
// dead-band: nothing accrues until you are more than 200 ml over the capacity of the body, so you can top a
// patient off safely.
// rise: while you are actively pushing past the dead-band, overload rises in proportion to the over-fill rate.
// plateau: the accumulated overload is hard-capped, so over-resuscitation edema does not run away.
// taper: the instant you stop pushing past the dead-band, overload always bleeds back toward 0, even if the
// patient is still technically over capacity. that models redistribution and diuresis clearing the excess.
private _excess   = (_acmeRawTotal - DEFAULT_BLOOD_VOLUME) max 0;  // liters over capacity.
private _deadband = missionNamespace getVariable ["ACME_edema_deadband", 0.2];  // 200 ml of grace before edema.
private _overCap  = missionNamespace getVariable ["ACME_edema_overloadCap", 1.5];  // the plateau ceiling, in liters.
private _accrue   = missionNamespace getVariable ["ACME_edema_accrueScale", 1.0];  // the over-fill into edema gain.
private _taperPS  = missionNamespace getVariable ["ACME_edema_taperPerSec", 0.01];  // the clear rate, in liters per second.
private _prevExc  = _unit getVariable ["ACME_edema_prevExcess", _excess];
_unit setVariable ["ACME_edema_prevExcess", _excess, false];

if (_excess > _deadband && {_excess > (_prevExc + 0.00001)}) then {
    // actively over-filling past the dead-band. accrue in proportion to how fast we are going over, then plateau.
    private _rise = ((_excess - (_prevExc max _deadband)) max 0) * _accrue;
    _fluidOverload = ((_fluidOverload + _rise) max 0) min _overCap;
} else {
    // not actively over-filling, or under the dead-band. always taper toward 0.
    _fluidOverload = (_fluidOverload - (_deltaT * _taperPS)) max 0;
};

// the debug over-resuscitation pins the overload, so the edema state holds whatever the actual fluid balance of
// the patient is. the toggle clears it.
if (_unit getVariable ["ACME_edema_debugForce", false]) then {
    _fluidOverload = missionNamespace getVariable ["ACME_edema_debugInduceVolume", 2.0];
};

_unit setVariable [QEGVAR(circulation,Overload_Volume), _fluidOverload, _syncValues];

private _calciumCount = _unit getVariable [QEGVAR(circulation,Calcium_Count), 0];
private _calciumCountChange = 0;

if (_transfusedBloodVolume > 0) then {
    if (_calciumCount > 0) then {
        _transfusedBloodVolumeChange = _transfusedBloodVolumeChange - ((_deltaT * 0.005) min _transfusedBloodVolume);
        _calciumCountChange = _calciumCountChange - ((_deltaT * 0.005) min _calciumCount);
        _plateletCountChange = _plateletCountChange + ((_deltaT * 0.005) min _calciumCount);
    };

    _targetPlateletCount = 3 - (_transfusedBloodVolume / 400);
};

_calciumCount = 0 max _calciumCount + _calciumCountChange min 3;
_unit setVariable [QEGVAR(circulation,Calcium_Count), _calciumCount, _syncValues];

_transfusedBloodVolume = 0 max _transfusedBloodVolume + _transfusedBloodVolumeChange min DEFAULT_BLOOD_VOLUME;
_unit setVariable [QEGVAR(circulation,TransfusedBlood_Volume), _transfusedBloodVolume, _syncValues];

if (_reactionBloodVolume > 0 && {_reactionBloodVolumeChange == 0}) then {
    _reactionBloodVolumeChange = _reactionBloodVolumeChange - ((_deltaT * 0.00125) min _reactionBloodVolume);
};

_reactionBloodVolume = 0 max _reactionBloodVolume + _reactionBloodVolumeChange min DEFAULT_BLOOD_VOLUME;
_unit setVariable [QEGVAR(circulation,HemolyticReaction_Volume), _reactionBloodVolume, _syncValues];

// target already computed above; preserve it here.

if (_plateletCount != _targetPlateletCount) then {
    private _adjustSpeed = linearConversion [3, 6, _bloodVolume, 10000, 1000, true];
    if (_TXAEffect > 0.1) then {
        _adjustSpeed = _adjustSpeed / 2;
    };
    if ((_bloodVolumeChange >= 0) && _plateletCount > _targetPlateletCount) then {
        _adjustSpeed = 100;
    };
    _plateletCountChange = _plateletCountChange + ((_targetPlateletCount - _plateletCount) / _adjustSpeed) * _deltaT;
};

_plateletCount = 0 max (_plateletCount + _plateletCountChange) min DEFAULT_BLOOD_VOLUME;

// GUARD: NO NON FINITE VALUE LEAVES THIS FUNCTION.
// ACE writes the return of this function straight into ace_medical_bloodVolume.
// One non finite value stays on the unit for the rest of the mission, because every later sum of it is also
// non finite. ACE then reports "Type Number, Not a Number" from getCardiacOutput on every frame.
// The heart rate, the blood pressure and the cardiac output all stop working for that casualty.
// This is the one place the four values leave the function, so the check belongs here.
// A bad value is replaced without emitting an RPT message.
// A unit that already holds a non finite blood volume is repaired by the same check.
// COST: four tests of a number. There is no new variable write and no broadcast on a good value.
private _fnc_finite = {
    params ["_v", "_fallback", "_label"];
    if (_v isEqualType 0 && {finite _v}) exitWith { _v };
    _fallback
};

// The fallback for the blood volume is the value ACE currently holds, when that value is still good.
private _lastBlood = _unit getVariable ["ace_medical_bloodVolume", DEFAULT_BLOOD_VOLUME];
if (!(_lastBlood isEqualType 0) || {!finite _lastBlood}) then { _lastBlood = DEFAULT_BLOOD_VOLUME; };

_bloodVolume    = [_bloodVolume, _lastBlood, "blood volume"] call _fnc_finite;
_plasmaVolume   = [_plasmaVolume, 0, "plasma volume"] call _fnc_finite;
_salineVolume   = [_salineVolume, 0, "saline volume"] call _fnc_finite;
_plateletCount  = [_plateletCount, DEFAULT_BLOOD_VOLUME, "platelet count"] call _fnc_finite;

_unit setVariable [QEGVAR(circulation,Platelet_Count), _plateletCount, _syncValues];

_unit setVariable [QEGVAR(circulation,Blood_Volume), _bloodVolume, _syncValues];
_unit setVariable [QEGVAR(circulation,Plasma_Volume), _plasmaVolume, _syncValues];
_unit setVariable [QEGVAR(circulation,Saline_Volume), _salineVolume, _syncValues];

// B103: make the ACE-facing circulating volume explicit. Every admitted milliliter of
// compatible blood, plasma or crystalloid is represented here immediately. Do not use the
// slow compartment-conversion rates above as a proxy for resuscitation volume.
private _circulatingVolume = ((_bloodVolume + _plasmaVolume + _salineVolume) min DEFAULT_BLOOD_VOLUME) max 0;
_unit setVariable ["ACME_circulatingVolume", _circulatingVolume, _syncValues];

// B156: new fluid/platelet changes enter the 5 Hz coagulation set on this owner immediately.
// Recompute after all compartments commit so no discovery sweep delays treatment response.
if (!isNil "ACME_fnc_coagulationTick") then {[[_unit]] call ACME_fnc_coagulationTick;};

_circulatingVolume;
