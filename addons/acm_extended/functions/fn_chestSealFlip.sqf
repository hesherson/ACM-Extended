// B48 chest-seal Flip: the casualty's ACTUAL visual orientation owns the front/back view.
// A Flip does not pre-emptively swap the diagram and then hope the body catches up.  The requested opposite side
// becomes visible as the casualty physically rolls; fn_chestSealTick continuously reclassifies the body.
private _patient = uiNamespace getVariable ["ACME_CS_Patient", objNull];
private _now = diag_tickTime;
private _lockedUntil = uiNamespace getVariable ["ACME_CS_FlipLockedUntil", 0];
if ((_lockedUntil isEqualType 0) && {_lockedUntil > _now}) exitWith {};
if ((uiNamespace getVariable ["ACME_CS_ApplyGestureUntil",0]) > _now) exitWith {};
if (isNull _patient) exitWith {};

private _uiCurrent = uiNamespace getVariable ["ACME_CS_Side", "front"];
private _newSide = if (_uiCurrent == "front") then {"back"} else {"front"};

uiNamespace setVariable ["ACME_CS_Dragging", false];
uiNamespace setVariable ["ACME_CS_DragPt", []];
uiNamespace setVariable ["ACME_CS_DragLast", -1];
uiNamespace setVariable ["ACME_CS_ArchBlend", 0];
uiNamespace setVariable ["ACME_CS_FingerGlow", []];

private _dead = (!alive _patient) || {(lifeState _patient) isEqualTo "DEAD"};
private _self = _patient isEqualTo (uiNamespace getVariable ["ACME_CS_Medic", objNull]);
// Physical control belongs only to a genuinely unconscious casualty or an awake casualty that
// is still inside ACM's authored Lying State. Ordinary prone/obtunded/mobile players are view-only.
private _willAnimate = (!_dead) && {!_self} && {[_patient] call ACME_fnc_chestSealCanPhysicalRoll};

// When the body cannot be physically controlled (including ANY ordinary conscious prone/mobile state),
// Flip remains only a procedural view change. It never forces the casualty into a new animation.
if (!_willAnimate) exitWith {
    uiNamespace setVariable ["ACME_CS_Side", _newSide];
    uiNamespace setVariable ["ACME_CS_FlipTarget", ""];
    uiNamespace setVariable ["ACME_CS_FlipLockedUntil", 0];
    uiNamespace setVariable ["ACME_CS_VirtualFlip", true];
    [] call ACME_fnc_chestSealRender;
};

// Keep the current side until the provider actually enters the roll RTM.
private _provider = uiNamespace getVariable ["ACME_CS_Medic", objNull];
private _display = uiNamespace getVariable ["ACME_CS_DLG", displayNull];
if (isNull _provider || {!local _provider} || {isNull _display}) exitWith {};
private _session = uiNamespace getVariable ["ACME_CS_SessionToken", ""];
private _token = format ["flip:%1:%2:%3",clientOwner,_session,diag_tickTime];
uiNamespace setVariable ["ACME_CS_FlipPendingToken",_token];
uiNamespace setVariable ["ACME_CS_VirtualFlip",false];
uiNamespace setVariable ["ACME_CS_FlipLockedUntil",_now + 7];
private _button = _display displayCtrl 86426;
_button ctrlEnable false;
_button ctrlSetText "Flipping...";

if ((_provider getVariable ["ACME_DP_Active",false])
    && {(_provider getVariable ["ACME_DP_Patient",objNull]) isEqualTo _patient}) then {
    _provider setVariable ["ACME_DP_Paused",true];
    _provider setVariable ["ACME_DP_PauseTreatmentClass","chestsealflip"];
    _provider setVariable ["ACME_DP_TreatmentBusy",true];
    _provider setVariable ["ACME_DP_PoseToken",(_provider getVariable ["ACME_DP_PoseToken",0]) + 1];
    _provider setVariable ["ACME_dah_gen",(_provider getVariable ["ACME_dah_gen",0]) + 1];
    _provider setVariable ["ACME_DP_InPose",false];
    _provider setVariable ["ACME_DP_LastPoseAssert",0];
};
// Leave the persistent hands-on-chest pose as a direct animation handoff into medic4.
private _holdEpoch = _provider getVariable ["ACME_CS_providerHoldEpoch",-1];
private _holdPose = _provider getVariable ["ACME_treatmentPoseState",[]];
if ((_holdPose param [1,""]) == "chestSealWorkspace") then {
    [_provider,"chestSealWorkspace",_holdEpoch,true] call ACME_fnc_treatmentPoseStop;
};
_provider setVariable ["ACME_CS_providerHoldEpoch",-1,false];
uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch",-1];

private _started = [_provider,"chestSealFlip",_patient] call ACME_fnc_rollProviderStart;
private _pose = _provider getVariable ["ACME_treatmentPoseState",[]];
private _epoch = if (_started) then {_pose param [0,-1]} else {-1};
private _rollToken = if (_started) then {_provider getVariable ["ACME_rollProviderToken",""]} else {""};
private _rollTime = missionNamespace getVariable ["ACME_CS_rollTime",1.85];
if !(_rollTime isEqualType 0 && {finite _rollTime}) then {_rollTime = 1.85;};
_rollTime = (_rollTime max 0.1) min 5;

// A physical Flip is staged: provider medic4 must acquire first, and chestSealFlipTick dispatches the patient
// roll only after the requested work state is actually observed. If provider theatre cannot acquire, abort the
// click cleanly instead of rolling the casualty from the button/prep state.
if (!_started) exitWith {
    uiNamespace setVariable ["ACME_CS_FlipPendingToken",""];
    uiNamespace setVariable ["ACME_CS_FlipLockedUntil",0];
    uiNamespace setVariable ["ACME_CS_FlipTarget",""];
    uiNamespace setVariable ["ACME_CS_VirtualFlip",false];

    if (!isNull _display) then {
        private _b = _display displayCtrl 86426;
        _b ctrlEnable true;
        _b ctrlSetText "Flip";
    };

    if (!isNull _provider && {local _provider}) then {
        private _holdEpoch = [_provider,_patient] call ACME_fnc_chestSealProviderHoldStart;
        _provider setVariable ["ACME_CS_providerHoldEpoch",_holdEpoch,false];
        uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch",_holdEpoch];

        if ((_provider getVariable ["ACME_DP_PauseTreatmentClass",""]) == "chestsealflip") then {
            _provider setVariable ["ACME_DP_Paused",false];
            _provider setVariable ["ACME_DP_PauseTreatmentClass",""];
            _provider setVariable ["ACME_DP_TreatmentBusy",false];
            _provider setVariable ["ACME_DP_IdleStart",CBA_missionTime];
        };
    };
};

private _args = [_patient,_provider,_display,_session,_token,_epoch,_rollToken,_newSide,_rollTime,-1,_now + 5.5];
private _flipPFH = [{_this call ACME_fnc_chestSealFlipTick;},0,_args] call CBA_fnc_addPerFrameHandler;
uiNamespace setVariable ["ACME_CS_FlipPFH", _flipPFH];
