// Roll a junctional hemorrhage from one ACE woundReceived event.
//
// Supported/native path:
//   [_unit, _allDamages, _ammo] call ACME_fnc_junctionalRollSpawn
// where _allDamages is ACE's woundReceived array. ACME registers this handler after ACE's own wound handler, so
// GET_OPEN_WOUNDS already contains the wound produced by the hit. Only parts named by this event are inspected;
// old wounds on unrelated limbs are never re-rolled.
//
// Legacy/internal path:
//   [_unit, _newWoundsHashMap] call ACME_fnc_junctionalRollSpawn
// remains accepted for scripted/tests that already provide the exact new-wound map.
//
// Eligible native wounds are medium/large VelocityWound and large Avulsion. The configured appearance-frequency
// multiplier still controls the same velocity/avulsion probabilities.
params ["_unit", ["_woundData", []], ["_ammo", ""]];
if (isNull _unit || {!local _unit} || {!alive _unit}) exitWith {};
if !(missionNamespace getVariable ["ACME_sys_junc", true]) exitWith {};

private _prioritySpawn = (_unit getVariable ["ACME_spawnSeverity", -1]) == 2
    && {_unit getVariable ["ACME_trainingSpawnInProgress", false]};
if (_prioritySpawn && {!(_unit getVariable ["ACME_trainingSpawnFinalize", false])}) exitWith {};
private _isolated = [];
if (_prioritySpawn) then {
    _isolated = [_unit getVariable ["ace_medical_openWounds", createHashMap],
        _unit getVariable ["ACM_damage_InternalWounds", createHashMap],
        (_unit getVariable ["ACM_breathing_Hemothorax_Fluid", 0]) max (_unit getVariable ["ACM_breathing_Hemothorax_State", 0])] call ACME_fnc_priorityJunctionalCandidate;
};
if (_prioritySpawn && {_isolated isEqualTo []}) exitWith {};
private _names = missionNamespace getVariable ["ace_medical_damage_woundClassNames", []];
if (_names isEqualTo []) exitWith {};

private _openWounds = createHashMap;
private _candidateParts = [];
if (_woundData isEqualType createHashMap) then {
    _openWounds = _woundData;
    _candidateParts = ["leftarm", "rightarm", "leftleg", "rightleg"] select {
        !((_openWounds getOrDefault [_x, []]) isEqualTo [])
    };
} else {
    // ACE woundReceived body-part names are case-insensitive. Ignore head/body here; penetrating chest trauma has
    // its own chest-seal/pneumothorax path and junctionals are limb anchored.
    {
        if (_x isEqualType [] && {count _x >= 2}) then {
            private _part = toLower (_x param [1, ""]);
            if (_part in ["leftarm", "rightarm", "leftleg", "rightleg"]) then {
                _candidateParts pushBackUnique _part;
            };
        };
    } forEach _woundData;
    private _allOpen = _unit getVariable ["ace_medical_openWounds", createHashMap];
    { _openWounds set [_x, +(_allOpen getOrDefault [_x, []])]; } forEach _candidateParts;
};
if (_candidateParts isEqualTo []) exitWith {};

private _pVel = missionNamespace getVariable ["ACME_junctionalChanceVelocity", 0.6];  // high.
private _pAvl = missionNamespace getVariable ["ACME_junctionalChanceAvulsion", 0.15];  // low.

// Ordinary training tiers retain the legacy two-site cap, Expectant permits four.
// Priority generation is stricter: only one isolated source wound may be junctional,
// evaluated once after the full spawn injury batch. Later combat damage is not sanitized.
private _allParts = ["leftarm", "rightarm", "leftleg", "rightleg"];
private _cap = -1;
if ((group _unit) in [
    missionNamespace getVariable ["ACM_mission_TrainingCasualtyGroup", grpNull],
    missionNamespace getVariable ["ACM_mission_TrainingBluforGroup", grpNull]
]) then {
    private _sev = _unit getVariable ["ACME_spawnSeverity", (missionNamespace getVariable ["ACME_pendingSpawnSeverity", -1])];
    _cap = [2, 4] select (_sev >= 4);
};
if (_prioritySpawn) then {_cap = 1; _candidateParts = [_isolated select 0];};
private _curJunc = { (_unit getVariable [format ["ACME_Junc_%1", _x], ""]) != "" } count _allParts;

{
    private _part = _x;
    if (_cap >= 0 && {_curJunc >= _cap}) then { continue };  // at the cap of the casualty, so no more junctionals.
    if ((_unit getVariable [format ["ACME_Junc_%1", _part], ""]) != "") then { continue };  // already junctional.

    private _chance = 0;
    private _sourceWoundId = -1;
    private _sourceScore = -1;
    {
        _x params ["_id", "_amountOf", ["_bleeding", 0]];
        if (_amountOf <= 0) then { continue };
        private _classIndex = floor (_id / 10);
        private _size = _id % 10;  // 0 small, 1 medium, 2 large.
        private _cn = if (_classIndex >= 0 && _classIndex < count _names) then { _names select _classIndex } else { "" };
        private _candidateChance = 0;
        if (_cn == "VelocityWound" && _size >= 1) then { _candidateChance = _pVel; };  // a medium or large velocity wound.
        if (_cn == "Avulsion"     && _size >= 2) then { _candidateChance = _pAvl; };  // a large avulsion.
        if (_candidateChance > 0) then {
            _chance = _chance max _candidateChance;
            // Bind the junctional device state to the native wound that most plausibly created it. This lets later
            // packing/XStat/wrapping control the same native source rather than only ACME's additional arterial channel.
            private _score = (_amountOf max 0) * ((_bleeding max 0.001)) * (1 + _size);
            if (_score > _sourceScore) then {_sourceScore = _score; _sourceWoundId = _id;};
        };
    } forEach (_openWounds getOrDefault [_part, []]);

    if (_chance > 0 && {random 1 < _chance}) then {
        [_unit, _part, true, -1, _sourceWoundId] call ACME_fnc_junctionalInflict;
        _curJunc = _curJunc + 1;
    };
} forEach _candidateParts;
