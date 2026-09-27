// Chest-seal Flip uses the same provider medic4 theatre as every other chest flip.
// It immediately retires the current chest pose, then enters the normal empty-hands roll animation path.
private _patient = uiNamespace getVariable ["ACME_CS_Patient", objNull];
private _now = diag_tickTime;
private _lockedUntil = uiNamespace getVariable ["ACME_CS_FlipLockedUntil", 0];
if ((_lockedUntil isEqualType 0) && {_lockedUntil > _now}) exitWith {};
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

private _provider = uiNamespace getVariable ["ACME_CS_Medic", objNull];
private _display = uiNamespace getVariable ["ACME_CS_DLG", displayNull];
if (isNull _provider || {!local _provider} || {isNull _display}) exitWith {};
private _session = uiNamespace getVariable ["ACME_CS_SessionToken", ""];
private _token = format ["flip:%1:%2:%3", clientOwner, _session, diag_tickTime];
uiNamespace setVariable ["ACME_CS_FlipPendingToken", _token];
uiNamespace setVariable ["ACME_CS_VirtualFlip", false];
uiNamespace setVariable ["ACME_CS_FlipLockedUntil", _now + 3];
private _button = _display displayCtrl 86426;
_button ctrlEnable false;
_button ctrlSetText "Flipping...";

if ((_provider getVariable ["ACME_DP_Active", false])
    && {(_provider getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient}) then {
    _provider setVariable ["ACME_DP_Paused", true];
    _provider setVariable ["ACME_DP_PauseTreatmentClass", "chestsealflip"];
    _provider setVariable ["ACME_DP_TreatmentBusy", true];
    _provider setVariable ["ACME_DP_PoseToken", (_provider getVariable ["ACME_DP_PoseToken", 0]) + 1];
    _provider setVariable ["ACME_dah_gen", (_provider getVariable ["ACME_dah_gen", 0]) + 1];
    _provider setVariable ["ACME_DP_InPose", false];
    _provider setVariable ["ACME_DP_LastPoseAssert", 0];
};

// Flip has absolute precedence inside the live chest procedure. Invalidate the seal-placement worker BEFORE
// touching provider animation so its old 2.65 s callback can never wake up and restore medic3/workspace over Flip.
private _applyPFH = uiNamespace getVariable ["ACME_CS_ApplyPFH", -1];
if (_applyPFH isEqualType 0 && {_applyPFH >= 0}) then {[_applyPFH] call CBA_fnc_removePerFrameHandler;};
uiNamespace setVariable ["ACME_CS_ApplyPFH", -1];
uiNamespace setVariable ["ACME_CS_ApplyAnimSerial", (uiNamespace getVariable ["ACME_CS_ApplyAnimSerial", 0]) + 1];
uiNamespace setVariable ["ACME_CS_ApplyGestureUntil", 0];

// Retire ANY ACME-owned provider pose as a handoff. This includes seal medic3 and NCD medic1. Keep the old
// visible chest pose in place for the handoff; do not play an intermediate neutral/weapon-restoring exit.
private _oldPose = _provider getVariable ["ACME_treatmentPoseState", []];
private _oldMode = _oldPose param [1, ""];
private _oldEpoch = _oldPose param [0, -1];
if (_oldEpoch >= 0 && {_oldMode != ""}) then {
    [_provider, _oldMode, _oldEpoch, true] call ACME_fnc_treatmentPoseStop;
};
_provider setVariable ["ACME_CS_providerHoldEpoch", -1, false];
uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch", -1];

private _rollTime = missionNamespace getVariable ["ACME_CS_rollTime", 1.85 / (call ACME_fnc_choreographyRate)];
if !(_rollTime isEqualType 0 && {finite _rollTime}) then {_rollTime = 1.85 / (call ACME_fnc_choreographyRate);};
_rollTime = (_rollTime max 0.1) min 5;

// Use the exact same provider entry path as the other chest flips. Do not manipulate weapon selection here:
 // rollProviderStart/treatmentPoseStart own the normal empty-hands preflight and medic4 interpolation.
private _started = [_provider, "chestSealFlip", _patient] call ACME_fnc_rollProviderStart;
private _pose = _provider getVariable ["ACME_treatmentPoseState", []];
private _epoch = if (_started) then {_pose param [0, -1]} else {-1};
private _rollToken = if (_started) then {_provider getVariable ["ACME_rollProviderToken", ""]} else {""};

if (!_started) exitWith {
    uiNamespace setVariable ["ACME_CS_FlipPendingToken", ""];
    uiNamespace setVariable ["ACME_CS_FlipLockedUntil", 0];
    uiNamespace setVariable ["ACME_CS_FlipTarget", ""];
    uiNamespace setVariable ["ACME_CS_VirtualFlip", false];

    if (!isNull _display) then {
        private _b = _display displayCtrl 86426;
        _b ctrlEnable true;
        _b ctrlSetText "Flip";
    };

    if (!isNull _provider && {local _provider}) then {
        private _holdEpoch = [_provider, _patient] call ACME_fnc_chestSealProviderHoldStart;
        _provider setVariable ["ACME_CS_providerHoldEpoch", _holdEpoch, false];
        uiNamespace setVariable ["ACME_CS_ProviderHoldEpoch", _holdEpoch];

        if ((_provider getVariable ["ACME_DP_PauseTreatmentClass", ""]) == "chestsealflip") then {
            _provider setVariable ["ACME_DP_Paused", false];
            _provider setVariable ["ACME_DP_PauseTreatmentClass", ""];
            _provider setVariable ["ACME_DP_TreatmentBusy", false];
            _provider setVariable ["ACME_DP_IdleStart", CBA_missionTime];
        };
    };
};

// Patient motion is dispatched by chestSealFlipTick on the first frame the exact medic4 work state is observed.
// That is the same sequencing used by auscultation and chest-entry flips, but because the old pose is already
// handed off and logical weapon selection is cleared above there is no extra holster or crouch delay.
private _providerNative = missionNamespace getVariable ["ACME_rollProviderDuration", 2.2];
if !(_providerNative isEqualType 0 && {finite _providerNative} && {_providerNative > 0}) then {_providerNative = 2.2;};
private _providerWall = (_providerNative / (call ACME_fnc_choreographyRate)) + 0.55;
private _deadline = _now + ((_providerWall max (_rollTime + 0.35)) min 3.0);

private _args = [_patient, _provider, _display, _session, _token, _epoch, _rollToken,
    _newSide, _rollTime, -1, _deadline];
private _flipPFH = [{_this call ACME_fnc_chestSealFlipTick;}, 0, _args] call CBA_fnc_addPerFrameHandler;
uiNamespace setVariable ["ACME_CS_FlipPFH", _flipPFH];
