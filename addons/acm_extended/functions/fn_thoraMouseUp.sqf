if ([_this,"up"] call ACME_fnc_minigameInputMouse) exitWith {true};
// left mouse up. it commits whichever action is in progress: an incision, with the scalpel, or a palpation mark.
params ["", "_button"];
if (_button != 0) exitWith { false };
uiNamespace setVariable ["ACME_Thora_LMBDown", false];
private _medic = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
private _target = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
if ((uiNamespace getVariable ["ACME_Thora_Cutting", false]
    || {uiNamespace getVariable ["ACME_Thora_KellyArmed", false]}) && {
    !([_medic, "thoracostomy"] call ACME_fnc_procedureAllowed)
    || {([_medic, _target] call ACME_fnc_thoraKitItem) == ""}
}) exitWith {
    uiNamespace setVariable ["ACME_Thora_Cutting", false];
    uiNamespace setVariable ["ACME_Thora_KellyArmed", false];
    [] call ACME_fnc_thoraRender;
    false
};
// the kelly close sfx, on the release of an accepted, audible, press only, so suppressed spam clicks stay silent.
if (((uiNamespace getVariable ["ACME_Thora_Held", ""]) isEqualTo "kelly") && {uiNamespace getVariable ["ACME_Thora_KellyPressSfx", false]}) then {
    uiNamespace setVariable ["ACME_Thora_KellyPressSfx", false];
    playSound "ACME_KellyClose";
};

// the kelly release: if armed over the split, open the tract now, and the cursor flips to the open clamps through
// the tick.
if (uiNamespace getVariable ["ACME_Thora_KellyArmed", false]) exitWith {
    uiNamespace setVariable ["ACME_Thora_KellyArmed", false];
    private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
    private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
    if (!isNull _patient && {(_patient getVariable [format ["ACME_thora_open_%1", _side], ""]) isEqualTo "split"}) then {
        [_patient, _side, "open", "kelly"] call ACME_fnc_thoraSideStateCommit;
        [_patient] call ACME_fnc_thoraBumpVer;
        [] call ACME_fnc_thoraRenderOpen;
    };
    false
};

// Commit applied prep once on release. The patient owner merges concurrent providers' trails.
if (uiNamespace getVariable ["ACME_Thora_Prepping", false]) exitWith {
    uiNamespace setVariable ["ACME_Thora_Prepping", false];
    private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
    [_side] call ACME_fnc_thoraPrepFlush;
    false
};

// commit an incision.
if (uiNamespace getVariable ["ACME_Thora_Cutting", false]) exitWith {
    uiNamespace setVariable ["ACME_Thora_Cutting", false];
    private _len = uiNamespace getVariable ["ACME_Thora_CutLen", 0];
    private _angle = uiNamespace getVariable ["ACME_Thora_CutAngle", 0];
    private _start = uiNamespace getVariable ["ACME_Thora_CutStart", []];
    if (count _start != 2 || {_len <= 0.001}) exitWith {
        [[0, 0], 0, 0] call ACME_fnc_thoraDrawIncision;
        false
    };
    private _pxPerCm = missionNamespace getVariable ["ACME_thora_pxPerCm", 60];
    private _lenCm = (_len * 2048) / (_pxPerCm max 1);
    private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
    private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
    if (!isNull _patient) then {
        [_patient, _side, "incision", [_start, _angle, _lenCm]] call ACME_fnc_thoraSideStateCommit;
        [_patient] call ACME_fnc_thoraBumpVer;
        // Incision pain is real, but the procedure does not automatically knock a conscious casualty out.
        // Local lidocaine is body-site specific; systemic ketamine is a separate onset-aware analgesic gate.
        if (alive _patient && {!([_patient,"body"] call ACME_fnc_proceduralAnesthetized)}) then {
            private _pc = [_patient,"body"] call ACME_fnc_proceduralAnalgesiaOnBoard;
            private _ket = _pc select 1;
            private _frac = linearConversion [0,(missionNamespace getVariable ["ACME_procKetamineAnalgesiaThreshold",0.08]),_ket,0,0.65,true];
            private _pain = (missionNamespace getVariable ["ACME_thora_incisionPain",0.70]) * (1 - _frac);
            if (_pain > 0.02) then {[_patient,_pain] call ace_medical_fnc_adjustPainLevel;[_patient,"hit"] call ace_medical_feedback_fnc_playInjuredSound;};
        };
    };
    // the score: the angle against the rib-transverse target plus the length band. it is stored for later stages and
    // outcomes, and it is tunable.
    private _ribAngle = missionNamespace getVariable [["ACME_thora_ribAngleRight", "ACME_thora_ribAngleLeft"] select (_side == "left"), 25];
    private _angErr = abs (((((_angle - _ribAngle) + 180) mod 360) - 180));
    if (_angErr > 90) then { _angErr = 180 - _angErr; };
    private _ideal = missionNamespace getVariable ["ACME_thora_incisionIdealCm", [2, 3]];
    private _lenOk = (_lenCm >= (_ideal select 0)) && {_lenCm <= (_ideal select 1)};
    if (!isNull _patient) then {
        [_patient, _side, "incisionScore", [_angErr, _lenCm, _lenOk]] call ACME_fnc_thoraSideStateCommit;
        [_patient] call ACME_fnc_thoraBumpVer;
    };
    // the prep gate: cutting through an un-prepped site seeds infection, which needs antibiotics later.
    private _prepLocal = uiNamespace getVariable ["ACME_Thora_PrepLocal", createHashMap];
    private _prep = if (_prepLocal isEqualType createHashMap && {_side in keys _prepLocal}) then {
        +(_prepLocal get _side)
    } else {
        if (isNull _patient) then {[]} else {+(_patient getVariable [format ["ACME_thora_prep_%1", _side], []])}
    };
    private _near = 0;
    {
        _x params ["_pu", "_pv"];
        if ((sqrt ((((_pu - (_start select 0)) ^ 2)) + (((_pv - (_start select 1)) ^ 2)))) < 0.12) then { _near = _near + 1; };
    } forEach _prep;
    if ((_near < (missionNamespace getVariable ["ACME_thora_prepMinPoints", 8])) && {!isNull _patient}) then {
        [_patient, _side, "infection", true] call ACME_fnc_thoraSideStateCommit;
        [_patient] call ACME_fnc_thoraBumpVer;
    };
    [_start, _angle, _len] call ACME_fnc_thoraDrawIncision;
    false
};

// commit a palpation mark.
uiNamespace setVariable ["ACME_Thora_Palpating", false];
if !(uiNamespace getVariable ["ACME_Thora_OnZone", false]) exitWith { false };
private _uv = uiNamespace getVariable ["ACME_Thora_CurUV", []];
if (count _uv != 2) exitWith { false };
private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
if (!isNull _patient) then {
    [_patient, _side, "site", _uv] call ACME_fnc_thoraSideStateCommit;
    [_patient] call ACME_fnc_thoraBumpVer;
};
uiNamespace setVariable ["ACME_Thora_SiteUV", _uv];
false
