// the tube is through the cords. this does not finish the job: the airway is not secured until the cuff is up,
// which is the whole cost of choosing a tube over a supraglottic. it hands off to the cuff step and leaves the
// tick running. it is guarded by ACME_laryngo_tubePassed so it can only fire once, and the gag branch below is
// recoverable after the reflex problem is addressed.
disableSerialization;
private _dlg = uiNamespace getVariable ["ACME_laryngo_dlg", displayNull];
private _patient = uiNamespace getVariable ["ACME_laryngo_patient", objNull];
private _medic = uiNamespace getVariable ["ACME_laryngo_medic", ACE_player];
if (isNull _patient) exitWith { closeDialog 0; };
private _existingTube = _patient getVariable ["ACME_ETT_Inserted", false];
if !([_medic, "intubation", _existingTube] call ACME_fnc_procedureAllowed) exitWith {};
if (uiNamespace getVariable ["ACME_laryngo_done", false]) exitWith {};
if (uiNamespace getVariable ["ACME_laryngo_tubePassed", false]) exitWith {};
// Reserve before applying any airway consequence. Existing in-patient tubes need no new item.
if (!_existingTube && {([_medic, _patient, "ACME_ETTube"] call ACME_fnc_treatmentSupplyCount) < 1}) exitWith {
    ["No ET tube available.", 2, _medic] call ace_common_fnc_displayTextStructured;
};
private _receipt = if (_existingTube) then {[]} else {[_medic, _patient, ["ACME_ETTube"]] call ACME_fnc_treatmentSupplyTake};
if (!_existingTube && {_receipt isEqualTo []}) exitWith {};
if (!_existingTube) then {[_receipt, false] call ACME_fnc_treatmentSupplyRefund;};
uiNamespace setVariable ["ACME_laryngo_tubePassed", true];

// Sample the live procedural reflex, but do not hard-block passage.  SAI/DSI can work with adequate hypnotic
// effect, RSI can suppress the physical reflex with paralysis, and arrest has no gag response.  An unsedated,
// non-paralyzed, perfusing casualty is guaranteed to react; partial sedation uses the graded reflex model.
private _misses = _patient getVariable ["ACME_laryngo_gagMisses", 0];
private _parts = [_patient] call ACME_fnc_sedationComponents;
private _sedLoad = _parts select 5;
private _arrest = _patient getVariable ["ace_medical_inCardiacArrest", false];
private _paralyzed = _patient getVariable ["ACME_roc_paralyzed", false];
private _gagChance = [_patient, 1 + (_misses max 0) * 0.4] call ACME_fnc_laryngoReflexChance;
private _underSedated = !_arrest && {!_paralyzed} && {_sedLoad < (missionNamespace getVariable ["ACME_laryngo_proceduralSedation", 0.75])};
// A low hypnotic load cannot override the shared helper's absent-reflex/life exclusions.
private _gagged = _gagChance > 0 && {!_arrest} && {!_paralyzed} && {_underSedated || {random 1 < _gagChance}};

[_patient, ["success", "awakeTube"] select _gagged] call ACME_fnc_laryngoConsequence;
// Through the cords; cuff and securement still require completion.
// the tube is committed. it is through the cords, so it stops being a thing in your hand and comes off the count,
// because it belongs to the patient now. it keeps drawing seated and is simply not carried any more.
uiNamespace setVariable ["ACME_laryngo_tubeInHand", false];
uiNamespace setVariable ["ACME_laryngo_tubeGrip", false];
uiNamespace setVariable ["ACME_laryngo_tubeAnchored", false];
uiNamespace setVariable ["ACME_laryngo_held", ""];
// freshly through the cords, so it is fully seated. migration measures from here.
private _pt0 = uiNamespace getVariable ["ACME_laryngo_patient", objNull];
if (!isNull _pt0) then {
    [_pt0, "placement", [1]] call ACME_fnc_ettMigrationStateCommit;
    [_pt0, "obstruction", [false]] call ACME_fnc_ettMigrationStateCommit;
};
// where it ended up, and whether that is too deep. past the ideal frame of this casualty the tube is down the right
// main bronchus, so one lung gets the whole tidal volume and the other gets nothing.
// the trap is that the capnograph still looks fine, because the tube is in the trachea and CO2 is coming back. it
// is the saturation and the airway pressure that give it away, and later the chest that sounds wrong on one side.
// that is exactly the diagnostic problem worth training.
private _pt1 = uiNamespace getVariable ["ACME_laryngo_patient", objNull];
private _frameNow = 1 + (round ((uiNamespace getVariable ["ACME_laryngo_tubeDepth", 0]) * 7));
private _idealF = uiNamespace getVariable ["ACME_laryngo_idealFrame", 8];
if (!isNull _pt1) then {
    private _deep = _frameNow > _idealF;
    [_pt1, "placement", ["__KEEP__", _frameNow, _deep]] call ACME_fnc_ettMigrationStateCommit;
    if (_deep) then {
        [_pt1, "airway", "ET tube advanced into the right main bronchus", "R mainstem intubation", []] call ACME_fnc_medLog;
    };
};
uiNamespace setVariable ["ACME_laryngo_state", "seated"];
[] call ACME_fnc_laryngoRefreshSlots;
uiNamespace setVariable ["ACME_laryngo_holding", false];
if (!isNull _dlg) then {
    [_dlg, 1] call ACME_fnc_laryngoTubeFrames;
    // seated. the swing stops and the tube hangs straight, held by the airway rather than by your fingers.
    uiNamespace setVariable ["ACME_laryngo_tubeAng", 0];
    uiNamespace setVariable ["ACME_laryngo_tubeAngVel", 0];
    private _tp = uiNamespace getVariable ["ACME_laryngo_tubeTipPos", []];
    if ((count _tp) >= 2) then {
        [_dlg, _tp select 0, _tp select 1, 0] call ACME_fnc_laryngoTubePose;
        // remember where it ended up, as a fraction of the frame rather than as screen coordinates.
        // fn_laryngoclose clears the screen-space copy, and it has to: those coordinates only mean anything for the
        // layout that produced them, and the next open can be a different resolution or aspect. storing the
        // fraction on the patient keeps the one fact that survives, which is where in the airway the tube sits.
        // the reopen in fn_laryngoinit reads this back, so a secured tube is redrawn exactly where the medic left
        // it rather than at an anchor that only approximates it.
        (uiNamespace getVariable ["ACME_laryngo_frame", [0,0,1,1]]) params ["_ffx","_ffy","_ffw","_ffh"];
        if (_ffw > 0 && {_ffh > 0}) then {
            private _tipFrac = [(((_tp select 0) - _ffx) / _ffw), (((_tp select 1) - _ffy) / _ffh)];
            [_patient, "tip", [_tipFrac]] call ACME_fnc_ettMigrationStateCommit;
        };
    };
};
playSound "ACME_VentClick";

if (_gagged) exitWith {
    if (!isNull _dlg) then {(_dlg displayCtrl 87810) ctrlSetText "Patient gagged and bucked the tube out.";};
    [_patient, "airway", "Intubation attempt: patient gagged and bucked the ET tube", "Gagged/bucked ET tube", []] call ACME_fnc_medLog;
    // The tube did pass the cords, so show the reverse travel rather than rejecting the insertion before it happens.
    ["gag", true] call ACME_fnc_laryngoTubeEject;
};

// B39: if the operator inflated the cuff before seating, crossing the cords now converts that
// mechanical cuff state into a definitive airway without forcing them to repeat the syringe step.
if (uiNamespace getVariable ["ACME_laryngo_cuffDone", false]) then {
    [] call ACME_fnc_laryngoCuffDone;
};
