// Coordinate the physical roll with the provider's work state, never the prep transitions.
disableSerialization;
params ["_args","_handle"];
_args params ["_patient","_provider","_display","_session","_token","_epoch","_rollToken",
    "_side","_rollTime","_rollStarted","_deadline"];
private _current = (uiNamespace getVariable ["ACME_CS_FlipPendingToken",""]) == _token;
private _finish = {
    [_handle] call CBA_fnc_removePerFrameHandler;
    if ((uiNamespace getVariable ["ACME_CS_FlipPFH",-1]) == _handle) then {
        uiNamespace setVariable ["ACME_CS_FlipPFH",-1];
    };
    // Retire only our provider animation and DP handoff; a later action owns its own state.
    if (!isNull _provider && {local _provider}
        && {(_provider getVariable ["ACME_rollProviderToken",""]) == _rollToken}
        && {_rollToken != ""}) then {
        private _pfh = _provider getVariable ["ACME_rollProviderPFH",-1];
        if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
        _provider setVariable ["ACME_rollProviderPFH",-1];
        _provider setVariable ["ACME_rollProviderToken",""];
        _provider setVariable ["ACME_rollProviderActive",false];
        // Same live workspace: suppress the neutral crouch and hand directly back to hands-on-chest.
        [_provider,"roll",_epoch,_current] call ACME_fnc_treatmentPoseStop;
    };
    if (!_current) exitWith {};

    private _holdEpoch = [_provider,_patient] call ACME_fnc_chestSealProviderHoldStart;
    _provider setVariable ["ACME_CS_providerHoldEpoch",_holdEpoch,false];
    uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch",_holdEpoch];

    uiNamespace setVariable ["ACME_CS_FlipPendingToken",""];
    uiNamespace setVariable ["ACME_CS_FlipLockedUntil",0];
    uiNamespace setVariable ["ACME_CS_FlipTarget",""];
    if (!isNull _display) then {
        private _button = _display displayCtrl 86426;
        _button ctrlEnable true;
        _button ctrlSetText "Flip";
    };
    if (!isNull _provider
        && {(_provider getVariable ["ACME_DP_PauseTreatmentClass",""]) == "chestsealflip"}) then {
        _provider setVariable ["ACME_DP_Paused",false];
        _provider setVariable ["ACME_DP_PauseTreatmentClass",""];
        _provider setVariable ["ACME_DP_TreatmentBusy",false];
        _provider setVariable ["ACME_DP_IdleStart",CBA_missionTime];
    };
};
if (!_current || {isNull _display} || {isNull _patient} || {isNull _provider}
    || {!alive _patient} || {!alive _provider}
    || {(uiNamespace getVariable ["ACME_CS_SessionToken",""]) != _session}
    || {!((uiNamespace getVariable ["ACME_CS_Patient",objNull]) isEqualTo _patient)}) exitWith {call _finish;};
if (_rollStarted >= 0) exitWith {
    private _poseNow = _provider getVariable ["ACME_treatmentPoseState",[]];
    private _providerAtHold = (_poseNow param [0,-2]) == _epoch
        && {(_poseNow param [1,""]) == "roll"}
        && {(_poseNow param [3,-2]) >= 3};
    private _providerCompleted = (_provider getVariable ["ACME_rollProviderCompletedEpoch",-1]) == _epoch;
    private _patientDone = diag_tickTime >= (_rollStarted + _rollTime);
    // Patient roll and provider medic4 both complete their authored portions before the handoff back to the
    // hands-on-chest workspace. The deadline remains the presentation fail-safe.
    if (_patientDone && {_providerAtHold || {_providerCompleted} || {diag_tickTime >= _deadline}}) then {call _finish;};
};

// The click may have started while the casualty was unconscious and completed after they woke or got up.
// Never dispatch a physical roll from a stale eligibility snapshot. Fall back to a virtual view change.
if !([_patient] call ACME_fnc_chestSealCanPhysicalRoll) exitWith {
    uiNamespace setVariable ["ACME_CS_Side", _side];
    uiNamespace setVariable ["ACME_CS_FlipTarget", ""];
    uiNamespace setVariable ["ACME_CS_VirtualFlip", true];
    [] call ACME_fnc_chestSealRender;
    call _finish;
};

private _pose = _provider getVariable ["ACME_treatmentPoseState",[]];
if (_epoch < 0 || {_rollToken == ""}
    || {!local _provider} || {_provider getVariable ["ACE_isUnconscious",false]}
    || {!isNull objectParent _provider}
    || {(_provider distance _patient) > 5}
    || {(_pose param [0,-2]) != _epoch}
    || {(_pose param [1,""]) != "roll"}
    || {(_provider getVariable ["ACME_rollProviderToken",""]) != _rollToken}
    || {diag_tickTime >= _deadline}) exitWith {call _finish;};
private _work = toLowerANSI (_pose param [2,""]);
// Stage 1 means the work state was requested; its exact animationState must also be observed.
// Stages -2/-1 are crouch/weapon preparation and can never move the patient.
if ((_pose param [3,-2]) >= 1
    && {_work == "ainvpknlmstpsnonwnondnon_medic4"}
    && {(toLowerANSI animationState _provider) == _work}) then {
    _args set [9,diag_tickTime]; // Mark before dispatch; at most one patient roll per click.
    uiNamespace setVariable ["ACME_CS_Side",_side];
    uiNamespace setVariable ["ACME_CS_FlipTarget",_side];
    uiNamespace setVariable ["ACME_CS_FlipLockedUntil",diag_tickTime + _rollTime];
    [_patient,_side,false,_provider] call ACME_fnc_chestSealRoll;
    [] call ACME_fnc_chestSealRender;
};
