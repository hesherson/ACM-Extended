/* B48: classify which anatomical surface is ACTUALLY facing the provider/camera.

   "front" means the casualty is supine / anterior chest up.
   "back"  means the casualty is prone / posterior chest up.

   Do not trust ACME_CS_facing as the primary signal: that is cached UI/roll bookkeeping and can be stale after
   ACE, ACM, Zeus, ragdoll or another provider changes the casualty's pose.  ACE's current unconscious animation
   classification is preferred; animated shoulder/head/pelvis geometry is the fallback and also works for many
   corpse/prone poses.  The stored side is used only when the body is essentially vertical/side-on or geometry is
   unavailable.
*/
params [
    ["_patient", objNull, [objNull]],
    ["_fallback", "front", [""]]
];
if !(_fallback in ["front", "back"]) then {_fallback = "front";};
if (isNull _patient) exitWith {_fallback};
// Without body animation, the timed procedural roll updates only its logical side. Engine geometry remains
// unchanged and cannot be used to undo that accepted endpoint or force entry normalization into a retry loop.
if !(missionNamespace getVariable ["ACME_interventionAnimations", true]) exitWith {
    _patient getVariable ["ACME_CS_facing", _fallback]
};

private _as = toLowerANSI animationState _patient;
private _faceUpState = toLowerANSI (missionNamespace getVariable ["ACME_uncon_faceUp", "ACM_LyingState"]);
private _faceDownState = toLowerANSI (missionNamespace getVariable ["ACME_uncon_faceDown", "ace_medical_engine_uncon_anim_1"]);
if (_as == _faceUpState) exitWith {"front"};
if (_as == _faceDownState) exitWith {"back"};

private _animMap = missionNamespace getVariable ["ace_medical_engine_animations", createHashMap];
private _up = (_animMap getOrDefault ["ace_medical_engine_uncon_anim_faceup", []]) apply {toLowerANSI _x};
private _down = (_animMap getOrDefault ["ace_medical_engine_uncon_anim_facedown", []]) apply {toLowerANSI _x};
if (_as in _up) exitWith {"front"};
if (_as in _down) exitWith {"back"};

// The geometry is based on animated selections, so it follows the visual body instead of a remembered flag.
private _pel = _patient modelToWorldVisual (_patient selectionPosition "pelvis");
private _hed = _patient modelToWorldVisual (_patient selectionPosition "head");
private _ls = _patient modelToWorldVisual (_patient selectionPosition "leftshoulder");
private _rs = _patient modelToWorldVisual (_patient selectionPosition "rightshoulder");
private _normal = (_hed vectorDiff _pel) vectorCrossProduct (_rs vectorDiff _ls);
private _nz = _normal param [2, 0];
private _mag = vectorMagnitude _normal;

// Near vertical/side-on the z sign is not a meaningful supine/prone classifier. Keep the last meaningful side.
if (_mag > 0.0001 && {abs _nz > (_mag * 0.08)}) exitWith {
    if (_nz < 0) then {"front"} else {"back"}
};

_patient getVariable ["ACME_CS_facing", _fallback]
