/* Patient eligibility, not a generic prone/weapon-lowered exemption. */
params [["_unit", objNull, [objNull]]];
if (isNull _unit || {!alive _unit} || {_unit getVariable ["ACME_clinicalRestoring", false]}
    || {_unit getVariable ["ACME_aiProtection_resetPending", false]}) exitWith {false};
if (_unit getVariable ["ACE_isUnconscious", false]) exitWith {true};
if (!isNull objectParent _unit || {_unit getVariable ["ACME_aiProtection_awakeBlocked", false]}) exitWith {false};
private _lying = _unit getVariable ["ACM_core_Lying_State", false];
if !(_lying isEqualType true) then {_lying = _lying isEqualType 0 && {_lying > 0};};
if (!_lying) exitWith {false};
// All entries are patient-only, weapon-disabled states. Ordinary prone, conscious AAJT collapse and upright
// obtundation do not qualify. A stale lying flag cannot hide a soldier who has returned to a combat animation.
private _animation = toLowerANSI animationState _unit;
if (_animation in [
    "acm_lyingstate", "acme_obtundedback", "acm_recoveryposition", "ace_medical_engine_uncon_anim_1",
    "acme_headelevpatientgrab", "acme_headelevpatienthold", "acme_headelevpatientrelease"
]) exitWith {true};
// Only the two native patient transitions used by chest flipping may consult inherited engine configuration.
// Their vanilla definitions are not shipped here; another animation mod may also change them. Preserve
// protection through a roll only when the loaded state explicitly disables weapons and cannot pull a trigger.
if !(_animation in ["ainjppnemstpsnonwrfldnon_rolltofront", "ainjppnemstpsnonwrfldnon_rolltoback"]) exitWith {false};
private _state = configFile >> "CfgMovesMaleSdr" >> "States" >> _animation;
(getNumber (_state >> "disableWeapons") > 0) && {getNumber (_state >> "canPullTrigger") == 0}
