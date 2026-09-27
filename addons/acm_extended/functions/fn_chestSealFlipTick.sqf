// Coordinate the chest-seal Flip with the same exact medic4 provider theatre used by the other chest flips.
// The click already pre-empts the old chest pose. This PFH waits only until Arma reports the requested medic4
// work state, then dispatches the casualty roll immediately. There is no full-animation wait before the roll starts.
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

    // Retire only this Flip's provider roll. A stale completion can never touch a newer provider episode.
    if (!isNull _provider && {local _provider}
        && {(_provider getVariable ["ACME_rollProviderToken",""]) == _rollToken}
        && {_rollToken != ""}) then {
        private _pfh = _provider getVariable ["ACME_rollProviderPFH",-1];
        if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
        _provider setVariable ["ACME_rollProviderPFH",-1];
        _provider setVariable ["ACME_rollProviderToken",""];
        _provider setVariable ["ACME_rollProviderActive",false];
        [_provider,"roll",_epoch] call ACME_fnc_treatmentPoseStop;
    };
    if (!_current) exitWith {};

    // Exit medic4 through the normal interpolated roll teardown, then return to the hands-on-chest workspace.
    // This matches the other chest flip sequences and never restores/reselects the provider's weapon.
    private _after = if (isNull _provider) then {[]} else {_provider getVariable ["ACME_treatmentPoseState",[]]};
    if (_after isEqualTo [] && {!isNull _provider} && {local _provider}) then {
        private _holdEpoch = [_provider,_patient] call ACME_fnc_chestSealProviderHoldStart;
        _provider setVariable ["ACME_CS_providerHoldEpoch",_holdEpoch,false];
        uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch",_holdEpoch];
    };

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
    private _patientDone = diag_tickTime >= (_rollStarted + _rollTime);
    private _poseNow = _provider getVariable ["ACME_treatmentPoseState",[]];
    private _providerStillRoll = (_poseNow param [0,-2]) == _epoch
        && {(_poseNow param [1,""]) == "roll"}
        && {(_provider getVariable ["ACME_rollProviderToken",""]) == _rollToken};
    private _providerCompleted = (_provider getVariable ["ACME_rollProviderCompletedEpoch",-1]) == _epoch;
    private _providerDone = _providerCompleted || {!_providerStillRoll} || {diag_tickTime >= _deadline};

    // Both accelerated motions are bounded. The provider never has to finish some unrelated prior animation first.
    if (_patientDone && {_providerDone}) then {call _finish;};
};

// If physical control becomes invalid before medic4 actually starts, keep the panel usable and perform only the
// procedural view change. Never animate a now-mobile/conscious casualty from a stale click.
if !([_patient] call ACME_fnc_chestSealCanPhysicalRoll) exitWith {
    uiNamespace setVariable ["ACME_CS_Side",_side];
    uiNamespace setVariable ["ACME_CS_FlipTarget",""];
    uiNamespace setVariable ["ACME_CS_VirtualFlip",true];
    [] call ACME_fnc_chestSealRender;
    call _finish;
};

private _pose = _provider getVariable ["ACME_treatmentPoseState",[]];
if (_epoch < 0 || {_rollToken == ""}
    || {!local _provider}
    || {_provider getVariable ["ACE_isUnconscious",false]}
    || {!isNull objectParent _provider}
    || {(_provider distance _patient) > 5}
    || {(_pose param [0,-2]) != _epoch}
    || {(_pose param [1,""]) != "roll"}
    || {(_provider getVariable ["ACME_rollProviderToken",""]) != _rollToken}
    || {diag_tickTime >= _deadline}) exitWith {call _finish;};

// Exactly the same chest-flip provider state used by auscultation and entry normalization.
private _work = toLowerANSI (_pose param [2,""]);
if ((_pose param [3,-2]) >= 1
    && {_work == "ainvpknlmstpsnonwnondnon_medic4"}
    && {(toLowerANSI animationState _provider) == _work}) then {
    _args set [9,diag_tickTime];
    uiNamespace setVariable ["ACME_CS_Side",_side];
    uiNamespace setVariable ["ACME_CS_FlipTarget",_side];
    uiNamespace setVariable ["ACME_CS_FlipLockedUntil",diag_tickTime + _rollTime];

    // Once medic4 is actually on screen, use the normal patient roll path: priority-1 interpolation first,
    // with the existing guarded fallback only if Arma swallows that transition. Do not hard-snap the roll.
    [_patient,_side,false,_provider,false] call ACME_fnc_chestSealRoll;
    [] call ACME_fnc_chestSealRender;
};
