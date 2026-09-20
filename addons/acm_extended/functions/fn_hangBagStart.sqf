// "Hang Bag". the medic holds a hung iv bag in the right hand. the body is locked into the raised-arm crew-aid
// loop while head and camera movement remain free. the iv line is a real PhysX rope, the engine default rope,
// hung between the bag and the patient, and it collides with terrain. there is no Draw3D fallback.
params ["_medic", "_patient", ["_bodyPart", ""], ["_fluidType", ""]];
_bodyPart = toLower _bodyPart;
if (isNull _patient || {isNull _medic} || {!local _medic}) exitWith {};
if (_fluidType == "") then { _fluidType = [_patient, _bodyPart] call ACME_fnc_hangBagFluidType; };

if (_medic getVariable ["ACME_hang_Active", false]) exitWith {
    ["You're already holding a bag up.", 2, _medic] call ace_common_fnc_displayTextStructured;
};
if (!isNull objectParent _medic) exitWith {
    ["Can't hold a bag up from inside a vehicle.", 2, _medic] call ace_common_fnc_displayTextStructured;
};

// Re-check after the raise/progress phase. The action condition is advisory only; another medic may have acquired
// this patient while our animation was running. If so, restore our temporarily removed weapons/DP state and abort.
private _holder = _patient getVariable ["ACME_hang_Medic", objNull];
if (!isNull _holder && {!(_holder isEqualTo _medic)}
    && {alive _holder} && {_holder getVariable ["ACME_hang_Active", false]}) exitWith {
    [_medic] call ACME_fnc_hangBagPrepStop;
    ["That bag is already being held up.", 2, _medic] call ace_common_fnc_displayTextStructured;
};

_medic setVariable ["ACME_hang_Raising", false];
_medic setVariable ["ACME_hang_sawFlow", false];  // the auto-lower latch, only after flow is first seen.
_medic setVariable ["ACME_hang_Active", true, true];
_medic setVariable ["ACME_hang_Patient", _patient, true];
_medic setVariable ["ACME_hang_Part", _bodyPart];
_medic setVariable ["ACME_hang_Start", CBA_missionTime];
_medic setVariable ["ACME_hang_LastPos", getPosASL _medic];
_patient setVariable ["ACME_hang_Medic", _medic, true];
_patient setVariable ["ACME_hang_flowMult", (missionNamespace getVariable ["ACME_hang_flowMult", 1.75]), true];

if (dialog) then { closeDialog 0; };

// the iv bag model, mounted to the calibrated right-hand point. pick the model and texture to match the fluid
// actually being given: the type, blood, plasma or saline, from _fluidType, and the size, 250, 500 or 1000 ml,
// read from the real hung bag of the patient and snapped to the nearest ACE bag model.
private _volume = 500;
private _ivBags = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
if (_ivBags isEqualType createHashMap) then {
    private _bags = [];
    if (_bodyPart != "" && {_bodyPart in keys _ivBags}) then {
        _bags = _ivBags getOrDefault [_bodyPart, []];
    } else {
        { _bags append _x; } forEach (values _ivBags);
    };
    private _b = _bags param [0, []];
    if !(_b isEqualTo []) then { _volume = _b param [1, 500]; };
};
private _vol = if (_volume <= 375) then {250} else { if (_volume <= 750) then {500} else {1000} };

private _texFluid = switch (_fluidType) do {
    case "blood":  {"blood"};
    case "plasma": {"plasma"};
    default        {"saline"};
};
private _bagModelClass = switch (_vol) do {
    case 250:  {"ACME_IVBagObject_250"};
    case 1000: {"ACME_IVBagObject_1000"};
    default    {"ACME_IVBagObject"};
};
// an explicit bagclass override still wins if it is set to a non-default class. it is a tuning hook.
private _override = missionNamespace getVariable ["ACME_hang_bagClass", "ACME_IVBagObject"];
if (_override != "" && {_override != "ACME_IVBagObject"}) then { _bagModelClass = _override; };

// Cosmetic-only local simple object. A networked ThingX hanging from a player's hand can participate in local
// collision/ownership updates and is unnecessary for presentation. Reading the configured model preserves the
// exact ACE bag art while making the hand prop geometry-free and non-physical.
private _bagModel = getText (configFile >> "CfgVehicles" >> _bagModelClass >> "model");
private _bag = if (_bagModel != "") then { createSimpleObject [_bagModel, [0,0,0], true] } else { objNull };
private _bagTexture = format ["\z\ace\addons\medical_treatment\data\IVBag_%1_%2ml_ca.paa", _texFluid, _vol];
if (!isNull _bag) then { _bag setObjectTexture [0, _bagTexture]; };
_medic setVariable ["ACME_hang_FluidType", _fluidType, true];
// the per-volume hand placement, from the live tuner. the bag euler is shared across volumes.
private _handOffset = missionNamespace getVariable [
    format ["ACME_hang_handOffset_%1", _vol],
    [-0.186979, -0.0842273, -0.0190512]  // a 500 ml fallback.
];
_bag attachTo [_medic,
    _handOffset,
    (missionNamespace getVariable ["ACME_hang_handSel", "RightHand"]), true];
[_bag, missionNamespace getVariable ["ACME_hang_bagEuler", [-106.246,70.3435,179.392]]] call BIS_fnc_setObjectRotation;
_medic setVariable ["ACME_hang_Bag", _bag];

// the weapon was already stowed by fn_hangbagprep. do not issue another asynchronous SwitchWeapon here, because
// that second command was completing after the pose started and knocking the raised arm animation back out.
private _pose = missionNamespace getVariable ["ACME_hang_poseAnim", "ACME_Acts_JetsCrewaidFCrouchThumbup_loop"];
// The stock Acts_* _in RTM contains cinematic root translation. That movement was being applied to the live
// provider and is the source of the ground slide. The progress-bar/prep sequence already supplies the visible
// crouch entry, so blend directly from that in-place crouch into the stationary raised-bag hold. Keep the local
// variable name for the existing animation contract test: the Hang Bag "in" request is now deliberately the hold.
private _inAnim = _pose;
private _inTime = 0.45;
_medic setVariable ["ACME_hang_Pose", _pose];
_medic setVariable ["ACME_hang_PoseRetryAt", CBA_missionTime + _inTime + 0.5];
[_medic, _inAnim, 1.4, 1] call ACME_fnc_doAnimHeld;
// One failsafe only. There is no position correction, setPos/setDir loop, or repeated pose wrestling.
[{
    params ["_medic", "_pose"];
    if (!isNull _medic && {_medic getVariable ["ACME_hang_Active", false]} && {(toLower animationState _medic) find "jetscrewaidfcrouchthumbup" < 0}) then {
        [_medic, _pose, 1] call ACME_fnc_doAnim;
    };
}, [_medic, _pose], _inTime] call CBA_fnc_waitAndExecute;
[_medic, true] call ACME_fnc_hangBagInputLock;

// the patient-side rope helper, including the calibrated position and orientation.
private _anchorClass = missionNamespace getVariable ["ACME_hang_anchorClass", "ace_fastroping_helper"];
private _anchor = _anchorClass createVehicleLocal [0, 0, 0];
private _lineEnd = if (_vol == 250) then {
    missionNamespace getVariable ["ACME_hang_linePatientOffset_250", [0.35404,-0.0718271,0.12404]]
} else {
    missionNamespace getVariable ["ACME_hang_linePatientOffset", [0.399215,-0.0718271,0.12404]]
};
private _lineRot = if (_vol == 250) then {
    missionNamespace getVariable ["ACME_hang_linePatientEuler_250", [-173.23,-84.1472,180]]
} else {
    missionNamespace getVariable ["ACME_hang_linePatientEuler", [-186.934,-84.1472,180]]
};
private _lineTip = missionNamespace getVariable ["ACME_hang_lineTipOffset", [0, 0.04, 0.06]];
if (!isNull _anchor) then {
    _anchor allowDamage false;
    _anchor hideObject true;
    _anchor attachTo [_patient, _lineEnd];
    [_anchor, _lineRot] call BIS_fnc_setObjectRotation;
    _anchor disableCollisionWith _patient;
    _anchor disableCollisionWith _bag;
};
_medic setVariable ["ACME_hang_LineAnchor", _anchor];

// the bag-side rope endpoint. ropecreate needs rope-capable physics objects at both ends, and the iv bag is a plain
// ThingX, so exactly like ACE fastroping ropes helper-to-helper, we hang a hidden fastroping helper at the outlet
// of the bag and rope between the two helpers. this is what makes the line actually spawn and render, and the bag
// stays purely visual in the hand.
private _bagHelperClass = missionNamespace getVariable ["ACME_hang_anchorClass", "ace_fastroping_helper"];
private _bagHelper = _bagHelperClass createVehicleLocal [0, 0, 0];
private _bagOut = missionNamespace getVariable ["ACME_hang_lineBagOffset", [0,0,0.12]];
if (!isNull _bagHelper) then {
    _bagHelper allowDamage false;
    _bagHelper hideObject true;
    _bagHelper attachTo [_bag, _bagOut];
    _bagHelper disableCollisionWith _bag;
    _bagHelper disableCollisionWith _medic;
    if (!isNull _anchor) then { _bagHelper disableCollisionWith _anchor; };
};
_medic setVariable ["ACME_hang_BagHelper", _bagHelper];

// Use the original custom IV-line rope art. This path is intentionally retained because the bundled
// iv_line_segment.p3d has proven reliable in the actual mod build and gives the intended thin, fluid-colored line.
// Keep the class choice local to this Hang Bag session so two providers cannot overwrite each other's rope style.
private _ropeClass = switch (_fluidType) do {
    case "blood":  { "ACME_IVLine_Rope_Blood" };
    case "plasma": { "ACME_IVLine_Rope_Plasma" };
    default        { missionNamespace getVariable ["ACME_hang_ropeClass", "ACME_IVLine_Rope"] };
};
private _rope = objNull;
if ((missionNamespace getVariable ["ACME_hang_useRope", true]) && {!isNull _anchor} && {!isNull _bagHelper}) then {
    _rope = [
        _anchor,
        _lineTip,
        _bagHelper,
        [0, 0, 0],
        (missionNamespace getVariable ["ACME_hang_lineLength", 3]),
        (missionNamespace getVariable ["ACME_hang_lineSagSegs", 24]),
        _ropeClass
    ] call ACME_fnc_ivLineCreate;
};
_medic setVariable ["ACME_hang_Rope", _rope];
_medic setVariable ["ACME_hang_RopeShown", !isNull _rope, true];

// Replicate the visual description, never the IDs of local props. Each observing client builds its own
// matching hand bag, endpoints and custom rope, including clients which join during this hold.
private _visualEpoch = (_medic getVariable ["ACME_hang_VisualEpoch", 0]) + 1;
_medic setVariable ["ACME_hang_VisualEpoch", _visualEpoch, true];
_medic setVariable ["ACME_hang_VisualEpisode", [_visualEpoch, true], true];
private _visualJip = format ["ACME_hangVisual_%1_%2", netId _medic, _visualEpoch];
_medic setVariable ["ACME_hang_VisualJip", _visualJip];
private _visualData = [_patient, _bagModel, _bagTexture, _handOffset,
    missionNamespace getVariable ["ACME_hang_handSel", "RightHand"],
    missionNamespace getVariable ["ACME_hang_bagEuler", [-106.246,70.3435,179.392]],
    _anchorClass, _lineEnd, _lineRot, _lineTip, _bagOut, _ropeClass,
    missionNamespace getVariable ["ACME_hang_lineLength", 3],
    missionNamespace getVariable ["ACME_hang_lineSagSegs", 24],
    missionNamespace getVariable ["ACME_hang_useRope", true]];
["ACME_hangBagVisualSync", [_medic, _visualEpoch, "show", _visualData, clientOwner], _visualJip] call CBA_fnc_globalEventJIP;
[_visualJip, _medic] call CBA_fnc_removeGlobalEventJIP;

// the manual release and the placement tuner.
private _ids = [];
_ids pushBack ([0x01, [false,false,false], { [false] call ACME_fnc_hangBagStop; }, "keydown", "", false, 0] call CBA_fnc_addKeyHandler);
_ids pushBack ([0xF1, [false,false,false], { [false] call ACME_fnc_hangBagStop; }, "keydown", "", false, 0] call CBA_fnc_addKeyHandler);
// the placement tuner, with sliders, is a debug dev tool. only bind f2 to it when debug features are enabled.
if (missionNamespace getVariable ["ACME_debug_enabled", false]) then {
    _ids pushBack ([0x3C, [false,false,false], { [] call ACME_fnc_hangBagTuneOpen; }, "keydown", "", false, 0] call CBA_fnc_addKeyHandler);
};
_medic setVariable ["ACME_hang_KeyIDs", _ids];

// a persistent on-screen cancel prompt, up for the whole hold.
[true] call ACME_fnc_hangBagHint;

private _debugOn = missionNamespace getVariable ["ACME_debug_enabled", false];
[format ["Bag up. Flow boosted x%1. Stay within %2 m of patient.%3",
    (_patient getVariable ["ACME_hang_flowMult", 1.75]) toFixed 2,
    (missionNamespace getVariable ["ACME_hang_leash", 3]),
    (if (_debugOn) then { " F2 opens placement tuning." } else { "" })], 5, _medic] call ace_common_fnc_displayTextStructured;
if (!isNil "ace_medical_treatment_fnc_addToLog") then {
    [_patient, "activity",
 "%1 raised the IV bag (gravity-assisted high flow)",
 "IV bag elevated, gravity high flow, %1",
 [[_medic, false, true] call ace_common_fnc_getName]] call ACME_fnc_medLog;
};

// the placement tuner is a debug dev tool, so only auto-open it when debug features are enabled and the toggle is
// on. in normal play, hanging a bag must not pop the slider dialog.
if (_debugOn && {missionNamespace getVariable ["ACME_hang_autoTuner", true]}) then {
    [{ if (ACE_player getVariable ["ACME_hang_Active", false]) then { [] call ACME_fnc_hangBagTuneOpen; }; }, [], 0.8] call CBA_fnc_waitAndExecute;
};

private _pfh = [ACME_fnc_hangBagTick, 0.05, [_medic, _patient]] call CBA_fnc_addPerFrameHandler;
_medic setVariable ["ACME_hang_PFH", _pfh];
