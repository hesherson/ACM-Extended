if ([_this,"down"] call ACME_fnc_minigameInputMouse) exitWith {true};
// left mouse down. with no tool held it begins palpating, feeling for the 5th ics and marking on a
// release-while-green. with the scalpel held it begins the incision, and only if the 5th ics has been marked and
// the click lands near it, which is a hard gate.
params ["", "_button"];
// a right-click near the incision pulls a placed tube, revealing the incision, or splits a not-yet-split incision
// open to expose the pink pleura bed, like the surgical cric, before the kelly and finger open the hole inside
// it.
if (_button == 1) exitWith {
    if (call ACME_fnc_thoraSealAt) exitWith {
        private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
        private _medic = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
        private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
        if !([_medic, "thoracostomySeal", true] call ACME_fnc_procedureAllowed) exitWith {false};
        [_patient, "thoraAftercare", [_patient, _medic, _side, "peel",
            [_patient] call ACME_fnc_clinicalEpoch]] call ACME_fnc_ownerDispatch;
        uiNamespace setVariable ["ACME_Thora_Burp", ["", 0, 0, false]];
        [] call ACME_fnc_chestSealSnd;
        [] call ACME_fnc_thoraRender;
        true
    };
    private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
    private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
    if (isNull _patient) exitWith { false };
    private _inc = _patient getVariable [format ["ACME_thora_incision_%1", _side], []];
    if (count _inc != 3) exitWith { false };
    private _uv = [] call ACME_fnc_thoraCursorUV;
    if (count _uv != 2) exitWith { false };
    (_inc select 0) params ["_su", "_sv"];
    _uv params ["_cu", "_cv"];
    if ((sqrt ((((_cu - _su) ^ 2)) + (((_cv - _sv) ^ 2)))) >= 0.15) exitWith { false };
    if (_patient getVariable [format ["ACME_thora_tube_%1", _side], false]) exitWith {
        private _medic = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
        if !([_medic, "chestTube", true] call ACME_fnc_procedureAllowed) exitWith {false};
        if (_patient getVariable [format ["ACME_thora_sealed_%1", _side], false]) then {
            // sutured in place: it does not come off.
            ["The chest tube is sutured in place.", 1.5] call ace_common_fnc_displayTextStructured;
        } else {
            [_patient, _side, "tube", false] call ACME_fnc_thoraSideStateCommit;
            [_patient, _side, "closed", false] call ACME_fnc_thoraSideStateCommit;
            [_patient] call ACME_fnc_thoraBumpVer;
            [] call ACME_fnc_thoraRenderTube;
            [] call ACME_fnc_thoraRender;
        };
        false
    };
    private _medic = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
    if !([_medic, "thoracostomy"] call ACME_fnc_procedureAllowed) exitWith {false};
    if (([_medic, _patient] call ACME_fnc_thoraKitItem) == "") exitWith {false};
    if ((_patient getVariable [format ["ACME_thora_open_%1", _side], ""]) isEqualTo "") then {
        [_patient, _side, "open", "split"] call ACME_fnc_thoraSideStateCommit;
        [_patient] call ACME_fnc_thoraBumpVer;
        [] call ACME_fnc_thoraRenderOpen;
    };
    false
};
if (_button != 0) exitWith { false };
uiNamespace setVariable ["ACME_Thora_LMBDown", true];
private _held = uiNamespace getVariable ["ACME_Thora_Held", ""];
private _operator = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
private _target = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
private _repeatFinger = _held == "finger" && {[_operator, _target,
    uiNamespace getVariable ["ACME_Thora_Side", "right"]] call ACME_fnc_thoraCanSweep};
if (_held in ["scalpel", "kelly", "finger"] && {!_repeatFinger} && {
    !([_operator, "thoracostomy"] call ACME_fnc_procedureAllowed)
    || {([_operator, _target] call ACME_fnc_thoraKitItem) == ""}
}) exitWith {false};
// the kelly sfx: an accepted click plays a random cut, and the matching release plays the close, in
// fn_thoramouseup. clicks inside the cooldown are accepted mechanically and stay silent, so spam-clicking cannot
// machine-gun the sounds. it is tunable through ACME_thora_kellySfxCooldown.
if (_held isEqualTo "kelly") then {
    private _nowSfx = diag_tickTime;
    if (_nowSfx >= (uiNamespace getVariable ["ACME_Thora_KellySfxAt", 0])) then {
        uiNamespace setVariable ["ACME_Thora_KellySfxAt", _nowSfx + (missionNamespace getVariable ["ACME_thora_kellySfxCooldown", 0.8])];
        uiNamespace setVariable ["ACME_Thora_KellyPressSfx", true];
        playSound (selectRandom ["ACME_KellyCut_1", "ACME_KellyCut_2", "ACME_KellyCut_3", "ACME_KellyCut_4"]);
    } else {
        uiNamespace setVariable ["ACME_Thora_KellyPressSfx", false];
    };
};

if (_held isEqualTo "") exitWith {
    uiNamespace setVariable ["ACME_Thora_Palpating", true];
    false
};

if (_held isEqualTo "chlorhexidine") exitWith {
    uiNamespace setVariable ["ACME_Thora_Prepping", true];
    uiNamespace setVariable ["ACME_Thora_PrepLast", []];
    false
};

if (_held isEqualTo "kelly") exitWith {
    private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
    private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
    if (isNull _patient) exitWith { false };
    private _inc = _patient getVariable [format ["ACME_thora_incision_%1", _side], []];
    if (count _inc != 3) exitWith { false };
    // opening is permanent and one-way: the kelly only works on a not-yet-opened tract and never resets or shrinks
    // it.
    if !((_patient getVariable [format ["ACME_thora_open_%1", _side], ""]) isEqualTo "split") exitWith { false };
    private _uv = [] call ACME_fnc_thoraCursorUV;
    if (count _uv != 2) exitWith { false };
    _uv params ["_cu", "_cv"];
    (_inc select 0) params ["_su", "_sv"];
    if ((sqrt ((((_cu - _su) ^ 2)) + (((_cv - _sv) ^ 2)))) > 0.12) exitWith { false };
    // arm the kelly: the hole is opened on release, at mouse up, with the closed clamps shrinking while held.
    uiNamespace setVariable ["ACME_Thora_KellyArmed", true];
    false
};

if (_held isEqualTo "finger") exitWith {
    private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
    private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
    if (isNull _patient) exitWith { false };
    private _inc = _patient getVariable [format ["ACME_thora_incision_%1", _side], []];
    if (count _inc != 3) exitWith { false };
    private _tract = _patient getVariable [format ["ACME_thora_open_%1", _side], ""];
    if !(_tract in ["kelly", "finger"]) exitWith {false};
    if (_patient getVariable [format ["ACME_thora_tube_%1", _side], false]
        || {_patient getVariable [format ["ACME_thora_sealed_%1", _side], false]}
        || {_patient getVariable [format ["ACME_thora_closed_%1", _side], false]}) exitWith {false};
    private _uv = [] call ACME_fnc_thoraCursorUV;
    if (count _uv != 2) exitWith { false };
    _uv params ["_cu", "_cv"];
    (_inc select 0) params ["_su", "_sv"];
    if ((sqrt ((((_cu - _su) ^ 2)) + (((_cv - _sv) ^ 2)))) > 0.12) exitWith { false };
    private _medic = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
    if (_tract == "finger") exitWith {
        [_patient, "thoraAftercare", [_patient, _medic, _side, "sweep",
            [_patient] call ACME_fnc_clinicalEpoch]] call ACME_fnc_ownerDispatch;
        false
    };
    private _kit = [_medic, _patient] call ACME_fnc_thoraKitItem;
    if (_kit == "") exitWith {false};
    private _usedKit = _kit == "ACM_ThoracostomyKit";
    if (_usedKit) then {
        // Respect ACE shared equipment and fail before creating a completed tract.
        private _used = [_medic, _patient, [_kit]] call ACME_fnc_treatmentSupplyTake;
        if (_used isEqualTo []) then {_kit = "";} else {[_used, false] call ACME_fnc_treatmentSupplyRefund;};
    };
    if (_kit == "") exitWith {false};
    [_patient, _side, "open", "finger"] call ACME_fnc_thoraSideStateCommit;
    [_patient, _side, "closed", false] call ACME_fnc_thoraSideStateCommit;
    [_patient, _side, "sealed", false] call ACME_fnc_thoraSideStateCommit;
    [_patient] call ACME_fnc_thoraBumpVer;
    [] call ACME_fnc_thoraRenderOpen;
    if (!isNull _medic) then {
        if ((_patient getVariable ["ACM_breathing_Thoracostomy_State", 0]) < 1) then {
            [_medic, _patient, _usedKit] call ACM_breathing_fnc_Thoracostomy_start;
        } else {
            // The second side must not reset an existing tube's aggregate state.
            if (_usedKit) then {[_patient, [["thoracostomyUsedKit", true]], true] call ACM_breathing_fnc_setRuntimeState;};
        };
    };
    false
};

if (_held in ["seal", "tube"]) exitWith {
    if !(uiNamespace getVariable ["ACME_Thora_TubeSnap", false]) exitWith { false };
    private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
    private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
    if (isNull _patient) exitWith { false };
    // Seal only this surgical tract. External entry/exit wounds retain their own
    // coverage, and no chest tube is registered by using the seal tool.
    // Use the selected tool identity, not a tray mode that inventory can change.
    if (_patient getVariable [format ["ACME_thora_tube_%1", _side], false]) exitWith {false};
    if (_held == "seal") exitWith {
        if (_patient getVariable [format ["ACME_thora_sealed_%1", _side], false]) exitWith {false};
        private _medS = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
        if !([_medS, "thoracostomySeal", true] call ACME_fnc_procedureAllowed) exitWith {false};
        private _receipt = [_medS, _patient, ["ACM_ChestSeal"]] call ACME_fnc_treatmentSupplyTake;
        if (_receipt isEqualTo []) exitWith {
            ["No chest seal available.", 2] call ace_common_fnc_displayTextStructured;
            false
        };
        [_receipt, false] call ACME_fnc_treatmentSupplyRefund;
        [_patient, _side, "sealed", true] call ACME_fnc_thoraSideStateCommit;
        [_patient, _side, "closed", true] call ACME_fnc_thoraSideStateCommit;
        [_patient] call ACME_fnc_thoraBumpVer;
        // This operation is deliberately distinct from native whole-chest sealing.
        // The owner validates the captured clinical epoch before changing physiology.
        ["ACME_ownerCommand", [_patient, "chestEffect", [_patient, _medS, "thoraSeal",
            [_side, [_patient] call ACME_fnc_clinicalEpoch], "", CBA_missionTime]], _patient] call CBA_fnc_targetEvent;
        [] call ACME_fnc_thoraRenderTube;
        ["tube"] call ACME_fnc_thoraSelectTool;
        false
    };

    private _tubeMedic = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
    if (_patient getVariable [format ["ACME_thora_closed_%1", _side], false]) exitWith {false};
    if (!(([_tubeMedic] call ACME_fnc_thoraClosureMode) select 2)) exitWith {false};
    private _tubeReceipt = [_tubeMedic, _patient, ["ACM_ChestTubeKit"]] call ACME_fnc_treatmentSupplyTake;
    if (_tubeReceipt isEqualTo []) exitWith {false};
    [_tubeReceipt, false] call ACME_fnc_treatmentSupplyRefund;
    [_patient, _side, "sealed", false] call ACME_fnc_thoraSideStateCommit;
    [_patient, _side, "closed", false] call ACME_fnc_thoraSideStateCommit;
    [_patient, _side, "tube", true] call ACME_fnc_thoraSideStateCommit;
    [_patient] call ACME_fnc_thoraBumpVer;
    // register the chest tube with ACM, so the procedure counts it as in. that enables drain fluid and shows on
    // exit.
    private _medic = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
    // ACM owns one aggregate tube state. A second-side tube must not call its
    // duplicate-insertion branch, which would refund the newly consumed kit.
    if (!isNull _medic && {(_patient getVariable ["ACM_breathing_Thoracostomy_State", 0]) != 2}) then {
        [_medic, _patient] call ACM_breathing_fnc_Thoracostomy_insertChestTube;
    };
    // start the passive heimlich drainage, and flag a surgical casualty once both sides have a tube, meaning
    // bilateral.
    [_patient] call ACME_fnc_thoraPassiveDrain;
    if ((_patient getVariable ["ACME_thora_tube_left", false]) && {_patient getVariable ["ACME_thora_tube_right", false]}) then {
        [_patient, true] call ACME_fnc_surgicalCasualtyCommit;
    };
    [] call ACME_fnc_thoraRenderTube;
    ["tube"] call ACME_fnc_thoraSelectTool;
    false
};

if (_held isEqualTo "scalpel") exitWith {
    private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
    private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
    private _site = if (isNull _patient) then { [] } else { _patient getVariable [format ["ACME_thora_site_%1", _side], []] };
    if (count _site != 2) exitWith { false };
    if ((count (_patient getVariable [format ["ACME_thora_incision_%1", _side], []])) == 3) exitWith { false };
    private _uv = [] call ACME_fnc_thoraCursorUV;
    if (count _uv != 2) exitWith { false };
    _uv params ["_cu", "_cv"];
    _site params ["_su", "_sv"];
    private _r = missionNamespace getVariable ["ACME_thora_incisionStartRadius", 0.06];
    if (sqrt (((_cu - _su) ^ 2) + ((_cv - _sv) ^ 2)) > _r) exitWith { false };
    uiNamespace setVariable ["ACME_Thora_Cutting", true];
    uiNamespace setVariable ["ACME_Thora_CutStart", _uv];
    uiNamespace setVariable ["ACME_Thora_CutLocked", false];
    uiNamespace setVariable ["ACME_Thora_CutAngle", 0];
    uiNamespace setVariable ["ACME_Thora_CutLen", 0];
    false
};
false
