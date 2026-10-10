/* Exactly one assessment generation drives the provider sequence. No replay/recovery loop. */
params ["_args", "_pfh"];
_args params ["_medic", "_epoch"];
if (isNull _medic) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
private _record = _medic getVariable ["ACME_assessment", []];
if (_record isEqualTo [] || {(_record select 0) != _epoch}) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
(_record select 1) params ["_m", "_patient", "_bodyPart", "_classname"];
private _pose = _medic getVariable ["ACME_treatmentPoseState", []];
private _phase = _record select 2;
if (!local _medic || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}
    || {!isNull objectParent _medic} || {isNull _patient}
    || {(_pose param [0, -1]) != _epoch}) exitWith {
    [_medic, _epoch] call ACME_fnc_assessmentStop;
};
if (_phase == 0) exitWith {
    if (CBA_missionTime - (_record select 4) > 5
        || {!((_record select 1) call ace_medical_treatment_fnc_canTreatCached)}
        || {!([_medic, _patient, ["isNotInside", "isNotSwimming", "isNotInZeus"]] call ace_common_fnc_canInteractWith)}
        || {([_medic, _patient] call ACME_fnc_patientInteractionDistance) > ace_medical_gui_maxDistance}) exitWith {
        [_medic, _epoch] call ACME_fnc_assessmentStop;
    };
    if ((_pose param [3, -1]) != 2) exitWith {};
    if ((toLowerANSI animationState _medic) != toLowerANSI (_pose select 2)) exitWith {};
    _record set [2, 1];
    // This clock belongs to the first RTM, not the already-running clinical timer.
    _record set [4, CBA_missionTime];
};
// Prone care uses the shared controller's actual prone equivalent. Never seek a kneeling RTM on a prone provider.
if (_pose param [20, false]) exitWith {};
private _breathing = (toLowerANSI _classname) == "checkbreathing";
if (_phase == 2 || {_breathing && {_phase == 1}}) exitWith {
    private _current = toLowerANSI animationState _medic;
    private _observedStart = _record param [7, -1];
    private _observedDuration = _record param [8, -1];
    if (_current == "ainvpknlmstpsnonwnondr_medic4") then {
        private _elapsed = _medic getUnitMovesInfo 1;
        private _duration = _medic getUnitMovesInfo 2;
        if (_elapsed isEqualType 0 && {finite _elapsed} && {_elapsed >= 0}
            && {_duration isEqualType 0} && {finite _duration} && {_duration > 0}) then {
            if (_observedStart < 0) then {_record set [7, CBA_missionTime - _elapsed];};
            _record set [8, _duration];
            // Track the full remaining authored movement, including any real entry/interpolation delay.
            _record set [12, (CBA_missionTime - (_record select 11)) + ((_duration - _elapsed) max 0)];
            if (_elapsed >= _duration) then {
                _record set [2, 3];
                [_medic, "ACM_GenericContinuous", 1] call ACME_fnc_doAnim;
            };
        };
    } else {
        // Normal finite RTMs can leave their state between owner frames. Only accept that exit once an
        // observed medic4 has had its complete native duration; an interrupted/missing state is not completion.
        if (_observedStart >= 0 && {_observedDuration > 0}
            && {CBA_missionTime >= _observedStart + _observedDuration}) then {
            _record set [2, 3];
        } else {
            // Entry gets a short grace. Once medic4 was actually observed, an early departure is an
            // interruption and must fail on this frame; waiting could later mislabel it a natural exit.
            if (_observedStart >= 0 || {CBA_missionTime - (_record param [9, CBA_missionTime]) > 1.5}) then {
                [_medic, _epoch] call ACME_fnc_assessmentStop;
            };
        };
    };
};
if (_phase != 1 || {_breathing}) exitWith {};
private _main = "AinvPknlMstpSnonWnonDr_medic5";
if ((toLowerANSI animationState _medic) != toLowerANSI _main) exitWith {
    // A sparse owner frame may miss the 1.75 sample and the entire first RTM. Seek that known sample
    // once only if the configured first RTM could have completed. Earlier departure is interruption.
    private _speed = getNumber (configFile >> "CfgMovesMaleSdr" >> "States" >> _main >> "speed");
    private _duration = if (_speed < 0) then {-_speed} else {if (_speed > 0) then {1 / _speed} else {0}};
    if (_duration >= 1.75 && {CBA_missionTime - (_record select 4) >= _duration}) then {
        [_medic, _pose, _record, _duration] call ACME_fnc_assessmentAdvance;
    } else {
        [_medic, _epoch] call ACME_fnc_assessmentStop;
    };
};
private _elapsed = _medic getUnitMovesInfo 1;
if !(_elapsed isEqualType 0 && {finite _elapsed} && {_elapsed >= 1.75}) exitWith {};
private _duration = _medic getUnitMovesInfo 2;
if !(_duration isEqualType 0 && {finite _duration} && {_duration >= 1.75}) exitWith {};
[_medic, _pose, _record, _duration] call ACME_fnc_assessmentAdvance;
