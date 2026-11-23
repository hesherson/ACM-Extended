/*
 * Phase 24 subsystem ownership: Hang Bag/pressure-infuser presentation, line geometry and treatment-pose synchronization.
 *
 * Extracted intact from ACME_fnc_postInit and invoked at the original point so startup
 * sequencing and CBA registration order are preserved.
 */

// hang bag, a gravity-assisted high flow.
// the medic holds a hung iv bag up in the left hand, in the standing or kneeling iv pose. the raised column
// boosts the iv flow, applied in the getIVFlowRate override. the bag model seats in the left hand and a physics
// iv line rope runs to the patient.
ACME_hang_flowMult  = 1.75;  // generic IV/fluid multiplier while the bag is held up
ACME_pressureInfuser_boost = 2.5;  // generic fluid multiplier. Blood uses the explicit tier/cap policy below.
ACME_warmedBlood_mlPerMin  = 200;  // LifeWarmer Quantum, non-cold blood
ACME_coldBlood_mlPerMin    = 100;  // cold-stored blood baseline
ACME_coldBloodHang_mlPerMin = 200; // cold-stored blood while Hang Bag is active
ACME_bloodMax_mlPerMin     = 300;  // absolute cap for every blood/fresh-blood path, including pressure infusion
ACME_hang_leash     = 3;  // m the medic can be from the patient before the bag lowers. this is the 3 m maximum line range.
// B395: the bag arm is a right-arm-only gesture (CfgGesturesMale > ACME_HangBagArmUp/Hold/Down), playing the
// crouch hold's own raise, hold and lower RTMs. The provider stays free to stand, crouch, walk (walking pace, inside
// the line's reach) and look around; only weapon use and going prone are held off. A provider who starts the
// hold lying prone keeps the old full-body prone hold.
ACME_hang_useGesture = true;  // false returns to the old full-body crouch hold
ACME_hang_gestureIn = "ACME_HangBagArmUp";
ACME_hang_gesture = "ACME_HangBagArmHold";  // the held gesture state
ACME_hang_gestureOut = "ACME_HangBagArmDown";
ACME_hang_gestureInTime = 1.0;  // = ACME_HangBagArmUp speed -1.0
ACME_hang_gestureOutTime = 0.45;  // = ACME_HangBagArmDown speed -0.45 (B395: quick, no pause after letting go)
ACME_hang_gestureReassertSec = 1.5;  // re-play the hold if another gesture (a reload, a hand signal) replaced it
// other machines show a provider's arm gesture (fn_hangBagGesture.sqf)
if (isNil "ACME_hang_gestureEH") then {
    ACME_hang_gestureEH = ["ACME_hangBagGesture", {
        params [["_unit", objNull], ["_state", ""]];
        if (isNull _unit || {local _unit} || {_state == ""}) exitWith {};
        if ((toLowerANSI gestureState _unit) != toLowerANSI _state) then {_unit switchGesture [_state, 0, 1, false];};
    }] call CBA_fnc_addEventHandler;
};
ACME_hang_stowWeapon = true;  // sling the rifle to the back smoothly before the hold, which frees the hands so the gesture reads. it re-arms on lower.
ACME_coolerAutoStore = true;  // auto-move received loose blood into a carried cooler that has room, filling empty coolers first. false disables it.
ACME_coolerAutoUse = true;  // surface cooler blood as [cooled] rows in the transfusion add-bag list, and pull from the cooler when a medic hangs one, so it can be used with no manual unload. false disables it.
ACME_hang_raiseTime  = 1.5;  // raise countdown in s when hung from the menu button. the weapon stows during it.
// bag tint by fluid type. the colors are approximated and anchored to the average of ACE's bag textures. they
// apply to hidden selection 0 of the bag model, and do nothing if the model exposes no selection.
ACME_hang_tintBlood  = "#(argb,8,8,3)color(0.46,0.06,0.09,1,co)";  // maroon red (whole blood / packed cells)
ACME_hang_tintPlasma = "#(argb,8,8,3)color(0.94,0.72,0.28,1,co)";  // orange-tinted yellow (plasma)
ACME_hang_tintFluid  = "#(argb,8,8,3)color(0.84,0.90,0.97,1,co)";  // very slightly pale blue (saline / crystalloid)
ACME_hang_bagClass  = "ACME_IVBagObject";  // iv bag model (CfgVehicles)
ACME_hang_handSel   = "RightHand";  // bag is physically parented to the medic's right hand
ACME_hang_handOffset = [-0.186979, -0.0842273, -0.0190512];  // final right-hand placement reported from the live tuner
ACME_hang_bagDir    = [0, 0, -1];  // bag model-space direction vector (hangs downward)
ACME_hang_bagUp     = [0, 1, 0];  // bag model-space up vector
// the iv line is the engine default rope, a plain ropecreate in ACE's fastroping form. it is binarized into
// the engine, always renders, and collides with terrain. it needs no custom segment .p3d, no binarization and
// no Draw3D.
ACME_hang_lineLength    = 3;  // meters of tubing laid out (rope length / max reach)
ACME_hang_lineSagSegs   = 48;  // B395: rope segments (fn_ivLineCreate passes it; engine maximum 63): a smoother hanging line
// ACME_hang_useRope is a CBA addon option, set in XEH_preInit, so it can be toggled in game. do not assign it
// here. postinit runs after preinit and would stomp the user's choice, which is the settings-stomp rule.
// iv line rope class. the thin pale-blue custom line is the default, and it needs the segment .p3d binarized by
// your build, because a raw mlod gives "Cannot open object". the fallbacks that need no binarize are "" for the
// engine rope, or "ACME_IVLine_BlueHose".
// "ACME_IVLine_Rope"     thin pale-blue custom line. the default, and it needs a binarize.
// ""                     engine default rope. thin and model-free.
// "ACME_IVLine_BlueHose" pale-blue, reusing ACE's binarized hose. it always loads and is hose-thick.
// "ace_refuel_fuelHose"  ACE's stock black hose.
ACME_hang_ropeClass = "ACME_IVLine_Rope";
ACME_hang_anchorClass = "ace_fastroping_helper";  // PhysX rope endpoint, used at both the patient anchor and the bag outlet. ropecreate needs rope-capable physics objects, and a plain ThingX or soldier returns objnull.
ACME_hang_autoTuner = true;  // auto-open the placement tuner on raise. f2 also opens it.
// The old cinematic _in state is retained as a compatibility/tuning name but is intentionally not used by
// fn_hangBagStart: its RTM translates the provider root. Entry now blends directly into the stationary hold.
ACME_hang_inAnim  = "ACME_Acts_JetsCrewaidFCrouchThumbup_in";
ACME_hang_outAnim = "ACME_Acts_JetsCrewaidFCrouchThumbup_out";  // authored lower-the-bag motion on cancel
ACME_hang_inTime  = 1.10;  // legacy compatibility knob; Hang Bag entry no longer waits on the cinematic _in RTM
ACME_hang_outTime = 1.00;  // legacy compatibility knob; stop now waits for the actual out state to finish
ACME_hang_handSel = "RightHand";
ACME_hang_handOffset = [-0.186979, -0.0842273, -0.0190512];  // legacy single offset (= 500 ml)
// per-volume right-hand placement, taken from the live tuner. the hung bag picks by the real volume of the
// bag.
ACME_hang_handOffset_250  = [-0.151827, -0.0642273,  0.0109488];
ACME_hang_handOffset_500  = [-0.186979, -0.0842273, -0.0190512];
ACME_hang_handOffset_1000 = [-0.206979, -0.0842273, -0.0390512];
ACME_hang_bagEuler = [-106.246, 70.3435, 179.392];  // shared across all volumes
ACME_hang_poseAnim = "ACME_Acts_JetsCrewaidFCrouchThumbup_loop";
// B31 treatment pose packets carry the exact stethoscope animation phase and episode.
// Every machine applies speed locally; the owner controls entry, hold, and release.
["ACME_treatmentPoseSync", {_this call ACME_fnc_treatmentPoseSync}] call CBA_fnc_addEventHandler;

ACME_CS_zoneHorizontalInsetFrac = 0.04;  // restore the original thorax height and shape. pull the left and right edges inward only.
ACME_hang_lineBagOffset = [0, 0, 0.12];  // outlet and spike side of the bag, where the bag-side rope helper sits.
ACME_hang_linePatientOffset = [0.399215, -0.0718271, 0.12404];  // patient-side line endpoint (500/1000 ml)
ACME_hang_linePatientEuler = [-186.934, -84.1472, 180];  // patient-side endpoint rotation (500/1000 ml)
// the 250 ml bag sits higher on the line, so its patient-side end and its rotation differ.
ACME_hang_linePatientOffset_250 = [0.35404, -0.0718271, 0.12404];
ACME_hang_linePatientEuler_250  = [-173.23, -84.1472, 180];
ACME_hang_lineTipOffset = [0, 0.04, 0.06];  // oriented local tip. it gives the line-end rotation a visible, live effect.

// Register on every client; dedicated servers do not create presentation objects.
["ACME_hangBagVisualSync", {_this call ACME_fnc_hangBagVisualSync}] call CBA_fnc_addEventHandler;
["ACME_hangClaimAck", {_this call ACME_fnc_hangBagClaimAck}] call CBA_fnc_addEventHandler;
// One-shot owner-routed gear recovery. This is deliberately valid for dead units and non-player local owners.
["ACME_hangRestoreWeapons", {
    params [["_medic", objNull, [objNull]], ["_episodeStart", -1, [0]]];
    if (!isNull _medic && {local _medic}) then {
        [_medic, _episodeStart] call ACME_fnc_hangBagRestoreWeapons;
    };
}] call CBA_fnc_addEventHandler;
if (hasInterface) then {
    ["unit", {
        params ["_unit", "_previous"];
        if (!isNull _previous && {_previous getVariable ["ACME_hang_Active", false]}) then {
            [true, _previous] call ACME_fnc_hangBagStop;
        };
    }] call CBA_fnc_addPlayerEventHandler;
};
if (isServer) then {
    addMissionEventHandler ["HandleDisconnect", {
        params ["_unit"];
        private _epoch = _unit getVariable ["ACME_hang_VisualEpoch", -1];
        if (_epoch >= 0) then {
            _unit setVariable ["ACME_hang_VisualEpisode", [_epoch, false], true];
            [format ["ACME_hangVisual_%1_%2", netId _unit, _epoch]] call CBA_fnc_removeGlobalEventJIP;
            ["ACME_hangBagVisualSync", [_unit, _epoch, "hide"]] call CBA_fnc_globalEvent;
        };
        private _patient = _unit getVariable ["ACME_hang_Patient", objNull];
        private _episodeStart = _unit getVariable ["ACME_hang_Start", -1];
        if (!isNull _patient) then {
            [_patient, "hangBagRelease", [_unit, _episodeStart]] call ACME_fnc_ownerDispatch;
        };
        _unit setVariable ["ACME_hang_Active", false, true];

        // The two weapon slots were published at prep time. Ownership normally transfers to the server immediately
        // after disconnect; wait for that handoff, then restore the exact loadout. If another owner receives the unit,
        // fall back to an object-targeted event instead of dropping the gear snapshot.
        if !((_unit getVariable ["ACME_hang_savedWeaponSlots", []]) isEqualTo []) then {
            [{
                params ["_u"];
                isNull _u || {local _u}
            }, {
                params ["_u", "_ep"];
                if (!isNull _u) then {[_u, _ep] call ACME_fnc_hangBagRestoreWeapons;};
            }, [_unit, _episodeStart], 2, {
                params ["_u", "_ep"];
                if (!isNull _u) then {
                    ["ACME_hangRestoreWeapons", [_u, _ep], _u] call CBA_fnc_targetEvent;
                };
            }] call CBA_fnc_waitUntilAndExecute;
        };
        false
    }];
};
