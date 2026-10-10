// Coordinate the pre-auscultation roll and open the scope only after the casualty reaches supine.
params ["_args", "_handle"];
_args params ["_provider", "_patient", "_bodyPart", "_epoch", "_rollToken", "_rollTime", "_rollStarted", "_deadline"];

private _finish = {
    params [["_openScope", false, [false]]];
    [_handle] call CBA_fnc_removePerFrameHandler;

    if (!isNull _provider && {local _provider}
        && {(_provider getVariable ["ACME_rollProviderToken", ""]) == _rollToken}
        && {_rollToken != ""}) then {
        private _pfh = _provider getVariable ["ACME_rollProviderPFH", -1];
        if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
        _provider setVariable ["ACME_rollProviderPFH", -1];
        _provider setVariable ["ACME_rollProviderToken", ""];
        _provider setVariable ["ACME_rollProviderActive", false];
        [_provider, "roll", _epoch] call ACME_fnc_treatmentPoseStop;
    };

    if (_openScope
        && {!isNull _provider} && {!isNull _patient}
        && {alive _provider} && {alive _patient}
        && {local _provider}) exitWith {
        [_provider, _patient, _bodyPart, true] call ACM_breathing_fnc_useStethoscope;
    };

    if (!isNull _provider && {local _provider}) then {
        ["Unable to reposition patient for auscultation.", 2, _provider] call ace_common_fnc_displayTextStructured;
        ["ace_treatmentFailed", [_provider, _patient, _bodyPart, "ACM_ContinuousAction", "", "", false]] call CBA_fnc_localEvent;
        if (!isNull _patient) then {["ACM_core_openMedicalMenu", _patient] call CBA_fnc_localEvent;};
    };
};

if (isNull _provider || {isNull _patient} || {!local _provider}
    || {!alive _provider} || {!alive _patient}) exitWith {[false] call _finish;};

if (_rollStarted >= 0) exitWith {
    private _poseNow = _provider getVariable ["ACME_treatmentPoseState",[]];
    private _providerAtHold = (_poseNow param [0,-2]) == _epoch
        && {(_poseNow param [1,""]) == "roll"}
        && {(_poseNow param [3,-2]) >= 3};
    private _providerCompleted = (_provider getVariable ["ACME_rollProviderCompletedEpoch", -1]) == _epoch;
    private _patientDone = diag_tickTime >= (_rollStarted + _rollTime + 0.08);
    if (_patientDone && {_providerAtHold || {_providerCompleted} || {diag_tickTime >= _deadline}}) then {
        [true] call _finish;
    };
};

// Eligibility can change while the provider is entering the work animation. Never replace that with a teleport.
if !([_patient] call ACME_fnc_chestSealCanPhysicalRoll) exitWith {[false] call _finish;};

private _pose = _provider getVariable ["ACME_treatmentPoseState", []];
if (_epoch < 0 || {_rollToken == ""}
    || {_provider getVariable ["ACE_isUnconscious", false]}
    || {!isNull objectParent _provider}
    || {(_provider distance _patient) > 5}
    || {(_pose param [0, -2]) != _epoch}
    || {(_pose param [1, ""]) != "roll"}
    || {(_provider getVariable ["ACME_rollProviderToken", ""]) != _rollToken}
    || {diag_tickTime >= _deadline}) exitWith {[false] call _finish;};

private _work = toLowerANSI (_pose param [2, ""]);
if ((_pose param [3, -2]) >= 1
    && {_work == "ainvpknlmstpsnonwnondnon_medic4" || {(_pose param [20, false]) && {_work == "acm_pronecontinuous"}}}
    && {(toLowerANSI animationState _provider) == _work}) then {
    _args set [6, diag_tickTime];
    private _preserveHead = _patient getVariable ["ACME_headElev_Suspended", false];
    [_patient, "front", false, _provider, _preserveHead] call ACME_fnc_chestSealRoll;
};
