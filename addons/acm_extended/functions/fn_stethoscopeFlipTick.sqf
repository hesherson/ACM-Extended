// Coordinate a stethoscope front/back flip with the exact chest-seal roll primitives.
disableSerialization;
params ["_args","_handle"];
_args params ["_patient","_provider","_display","_token","_epoch","_rollToken",
    "_side","_rollTime","_rollStarted","_deadline","_physicalDispatched"];

private _current = !isNull _display
    && {(_display getVariable ["ACME_stethFlipToken",""]) == _token}
    && {(findDisplay 81000) isEqualTo _display};

private _finish = {
    [_handle] call CBA_fnc_removePerFrameHandler;
    if (!isNull _display && {(_display getVariable ["ACME_stethFlipPFH",-1]) == _handle}) then {
        _display setVariable ["ACME_stethFlipPFH",-1];
    };

    // Retire exactly the roll provider episode which this click created.
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

    _display setVariable ["ACME_stethFlipToken",""];
    _display setVariable ["ACME_stethFlipActive",false];

    private _button = _display displayCtrl 81006;
    _button ctrlEnable true;
    _button ctrlSetText "Flip Side";

    // Return the provider to the held auscultation pose without closing/reopening the dialog.
    private _newPose = -1;
    if (!isNull _provider && {local _provider} && {alive _provider}
        && {!(_provider getVariable ["ACE_isUnconscious",false])}) then {
        _newPose = [_provider,"stethoscope",-1,_patient] call ACME_fnc_treatmentPoseStart;
        if (_newPose >= 0) then {_display setVariable ["ACME_stethPoseEpoch",_newPose];};
    };

    // Only a physical roll gets a new casualty hold. A view-only flip must never seize an awake/mobile patient.
    if ((_args param [10,false]) && {!isNull _patient} && {[_patient] call ACME_fnc_chestSealCanPhysicalRoll}) then {
        private _hold = if ((_display getVariable ["ACME_stethView","front"]) == "back") then {
            missionNamespace getVariable ["ACME_uncon_faceDown","ace_medical_engine_uncon_anim_1"]
        } else {
            missionNamespace getVariable ["ACME_uncon_faceUp","ACM_LyingState"]
        };
        private _serial = (missionNamespace getVariable ["ACME_stethPatientAnimSerial",0]) + 1;
        missionNamespace setVariable ["ACME_stethPatientAnimSerial",_serial];
        private _leaseToken = format ["steth:%1:%2:%3:%4",clientOwner,netId _provider,netId _patient,_serial];
        private _anim = ["",_hold] select ((toLowerANSI animationState _patient) != (toLowerANSI _hold));
        [_patient,_anim,2,"stethoscope",_provider,1.6,4,_leaseToken] call ACME_fnc_patientAnimRequest;
        _provider setVariable ["ACME_stethPatientAnimLease",[_patient,_leaseToken,CBA_missionTime + 0.65],false];
    };
};

if (!_current || {isNull _patient} || {isNull _provider}
    || {!alive _patient} || {!alive _provider}) exitWith {call _finish;};

if (_rollStarted >= 0) exitWith {
    private _poseNow = _provider getVariable ["ACME_treatmentPoseState",[]];
    private _providerAtHold = (_poseNow param [0,-2]) == _epoch
        && {(_poseNow param [1,""]) == "roll"}
        && {(_poseNow param [3,-2]) >= 3};
    private _providerCompleted = (_provider getVariable ["ACME_rollProviderCompletedEpoch",-1]) == _epoch;
    private _patientDone = diag_tickTime >= (_rollStarted + _rollTime + 0.08);
    // Return to the held stethoscope pose only after medic4 reaches its authored 2.2 s hold.
    if (_patientDone && {_providerAtHold || {_providerCompleted} || {diag_tickTime >= _deadline}}) then {call _finish;};
};

// Match the chest-seal fallback exactly: if physical eligibility disappears before the roll starts, only switch
// the auscultation diagram and leave the patient's animation untouched.
if !([_patient] call ACME_fnc_chestSealCanPhysicalRoll) exitWith {
    [_display,_side] call ACME_fnc_stethoscopeSetView;
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
if ((_pose param [3,-2]) >= 1
    && {_work == "ainvpknlmstpsnonwnondnon_medic4"}
    && {(toLowerANSI animationState _provider) == _work}) then {
    _args set [8,diag_tickTime];
    _args set [10,true];
    [_display,_side] call ACME_fnc_stethoscopeSetView;
    // Preserve head elevation only when auscultation already has it explicitly suspended. If that invariant is
    // absent, chestSealRoll performs its normal head-elevation teardown before rolling.
    private _preserveHead = _patient getVariable ["ACME_headElev_Suspended",false];
    [_patient,_side,false,_provider,_preserveHead] call ACME_fnc_chestSealRoll;
};
