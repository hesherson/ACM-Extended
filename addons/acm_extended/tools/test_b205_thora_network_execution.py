"""Execute owner prep merging and input-boundary flushes with delayed delivery.

Production SQF runs in SQF-VM. Objects/UI/locality are engine fixtures; finite
uses finite numeric samples because this VM lacks that engine command.
"""
from source_scan import lex, matching
from test_menu_death_lifecycle import adapt, execute, read


def block(source, marker):
    start = source.index("{", source.index(marker))
    tokens = lex(source)
    pairs = matching(tokens)
    opening = next(i for i, token in enumerate(tokens) if token.offset == start)
    return source[start + 1:tokens[pairs[opening]].offset]


def adapted(source):
    source = source.replace("finite (_x select 0)", "true").replace("finite (_x select 1)", "true")
    # Emulate only the unavailable hashmap primitive, preserving real map values.
    for name, key in (("_prepLocal", "_x"), ("_prepLocal", "_sideSeen"), ("_ribPending", "_side")):
        source = source.replace(f"{name} getOrDefault [{key}, []]", f"[{name}, {key}, []] call _getDefault")
    # Namespace stand-ins retain nil-valued keys in this VM; Arma getVariable
    # returns the supplied default after an object variable has been cleared.
    source = source.replace('_patient getVariable [_name, []]', '[_patient, _name, []] call _getVariableDefault')
    return adapt(source)


def setup():
    code = r'''
        private _getDefault = {params ["_map", "_key", "_default"]; if (_key in _map) then {_map get _key} else {_default}};
        private _getVariableDefault = {params ["_object", "_key", "_default"]; if (isNil {_object getVariable _key}) then {_default} else {_object getVariable _key}};
        ACME_fnc_chestAccessPreparing = {};
        ACM_GUI_fnc_resumeMedicalMenuPFH = {};
        ACME_fnc_thoraRender = {};
        ACME_fnc_thoraUpdateTrayIcons = {};
        uiNamespace setVariable ["ACME_Thora_Patient", _patient];
        uiNamespace setVariable ["ACME_Thora_Medic", objNull];
        uiNamespace setVariable ["ACME_Thora_PrepEpoch", 7];
        uiNamespace setVariable ["ACME_Thora_Side", "right"];
        _patient setVariable ["ACME_clinicalEpoch", 7];
        _patient setVariable ["ACME_thora_prep_right", []];
        _patient setVariable ["ACME_thora_ver", 0];
    '''
    for name in ("clinicalEpoch", "thoraSideStateCommit", "thoraBumpVer", "thoraPrepFlush", "thoraClose", "thoraFlip"):
        code += "ACME_fnc_" + name + "={" + adapted(read(name)) + "};\n"
    owner = block(read("ownerDispatch"), 'case "thoraPrepCommit":')
    code += 'private _ownerPrep = {params ["_patient", "_args"];' + adapted(owner) + '};\n'
    code += 'private _deliver = {params ["_packet"]; [_packet select 0, _packet select 2] call _ownerPrep;};\n'
    return code


def test_concurrent_providers_merge_at_owner_and_old_replays_are_idempotent():
    execute(setup() + r'''
        private _a = [0.1, 0.2]; private _b = [0.2, 0.3]; private _c = [0.3, 0.4];
        _patient setVariable ["ACME_thora_prep_right", [_a]];
        // Both providers began against the same replica containing only A.
        [_patient, [_patient, "right", [_a, _b], 7]] call _ownerPrep;
        [_patient, [_patient, "right", [_a, _c], 7]] call _ownerPrep;
        [(_patient getVariable "ACME_thora_prep_right") isEqualTo [_a, _b, _c], "concurrent prep overwritten"] call _check;
        private _version = _patient getVariable "ACME_thora_ver";
        [_patient, [_patient, "right", [_a, _b], 7]] call _ownerPrep;
        [(_patient getVariable "ACME_thora_ver") == _version, "duplicate prep bumped revision"] call _check;
        [count (_patient getVariable "ACME_thora_prep_right") == 3, "stale replay erased prep"] call _check;
    ''')


def test_delayed_prep_cannot_resurrect_a_reset_patient():
    execute(setup() + r'''
        _patient setVariable ["ACME_clinicalEpoch", 8];
        [_patient, [_patient, "right", [[0.1, 0.2]], 7]] call _ownerPrep;
        [(_patient getVariable "ACME_thora_prep_right") isEqualTo [], "old episode prep restored"] call _check;
        [_patient, [_patient, "right", [[0.1, 0.2]], 8]] call _ownerPrep;
        [count (_patient getVariable "ACME_thora_prep_right") == 1, "new episode prep rejected"] call _check;
        [_patient, [_patient, "back", [[0.1, 0.2]], 8]] call _ownerPrep;
        [(_patient getVariable "ACME_thora_ver") == 1, "invalid side advanced revision"] call _check;
    ''')


def test_owner_prep_is_bounded_and_rejects_malformed_geometry():
    execute(setup() + r'''
        private _points = [["bad", 0.1], [0.1], [-0.1, 0.1], [0.1, 1.1], 5, [0.1, 0.2]];
        [_patient, [_patient, "right", _points, 7]] call _ownerPrep;
        [(_patient getVariable "ACME_thora_prep_right") isEqualTo [[0.1, 0.2]], "bad geometry accepted"] call _check;
        _points = []; for "_i" from 1 to 200 do {_points pushBack [_i / 200, 0.5];};
        [_patient, [_patient, "right", _points, 7]] call _ownerPrep;
        private _stored = _patient getVariable "ACME_thora_prep_right";
        [count _stored == 130, "prep cap exceeded"] call _check;
        [(_stored select 0) isEqualTo [0.1, 0.2], "cap evicted earlier applied prep"] call _check;
    ''')


def test_close_mid_stroke_flushes_before_clearing_local_state():
    execute(setup() + r'''
        uiNamespace setVariable ["ACME_Thora_Prepping", true];
        uiNamespace setVariable ["ACME_Thora_PrepLocal", createHashMapFromArray [["right", [[0.1, 0.2]]]]];
        [] call ACME_fnc_thoraClose;
        [count _events == 1, "close lost painted prep"] call _check;
        [count (uiNamespace getVariable "ACME_Thora_PrepLocal") == 0, "close retained UI state"] call _check;
        [_events select 0] call _deliver;
        [(_patient getVariable "ACME_thora_prep_right") isEqualTo [[0.1, 0.2]], "close packet lost prep"] call _check;
    ''')


def test_side_change_flushes_original_side_and_rejects_reset_ui_buffer():
    execute(setup() + r'''
        uiNamespace setVariable ["ACME_Thora_Prepping", true];
        uiNamespace setVariable ["ACME_Thora_PrepLocal", createHashMapFromArray [["right", [[0.1, 0.2]]]]];
        [] call ACME_fnc_thoraFlip;
        [count _events == 1, "side change dropped prep"] call _check;
        [(((_events select 0) select 2) select 1) == "right", "prep attached to wrong side"] call _check;
        [!(uiNamespace getVariable "ACME_Thora_Prepping"), "stroke continued across sides"] call _check;
        _events = [];
        _patient setVariable ["ACME_clinicalEpoch", 8];
        [] call ACME_fnc_thoraPrepFlush;
        [count _events == 0, "stale UI buffer sent after reset"] call _check;
    ''')


def test_rib_target_is_stable_during_delayed_owner_reply_and_first_owner_commit_wins():
    source = read("thoraTick")
    start = source.index("private _tgt = if (isNull _patZ)")
    end = source.index('_tgt params ["_tU"', start)
    target = adapted(source[start:end])
    execute(setup() + r'''
        private _patZ = _patient; private _side = "right";
        uiNamespace setVariable ["ACME_Thora_RibPending", createHashMap];
        private _proposals = [];
        private _realCommit = ACME_fnc_thoraSideStateCommit;
        ACME_fnc_thoraSideStateCommit = {_proposals pushBack _this;};
    ''' + 'private _targetTick = {' + target + '_tgt};\n' + r'''
        private _first = [] call _targetTick;
        for "_i" from 1 to 60 do {
            [([] call _targetTick) isEqualTo _first, "pending palpation target moved"] call _check;
        };
        [count _proposals == 1, "pending rib target flooded owner"] call _check;
        ACME_fnc_thoraSideStateCommit = _realCommit;
        (_proposals select 0) call ACME_fnc_thoraSideStateCommit;
        [_patient, "right", "ribTarget", [0.8, 0.8, 0, 1]] call ACME_fnc_thoraSideStateCommit;
        [(_patient getVariable "ACME_thora_ribTarget_right") isEqualTo _first, "second provider changed established anatomy"] call _check;
        [_patient, "right", "ribTarget", nil] call ACME_fnc_thoraSideStateCommit;
        [isNil {_patient getVariable "ACME_thora_ribTarget_right"}, "clinical reset could not clear rib target"] call _check;
        _patient setVariable ["ACME_clinicalEpoch", 8];
        (_proposals select 0) call ACME_fnc_thoraSideStateCommit;
        [isNil {_patient getVariable "ACME_thora_ribTarget_right"}, "old episode restored pending anatomy"] call _check;
        [_patient, "right", "ribTarget", [0.8, 0.8, 0, 1]] call ACME_fnc_thoraSideStateCommit;
        [(_patient getVariable "ACME_thora_ribTarget_right") isEqualTo [0.8, 0.8, 0, 1], "new episode could not establish new anatomy"] call _check;
    ''')


def test_remote_prep_during_stroke_merges_without_dropping_unsent_local_points():
    source = read("thoraTick")
    start = source.index('private _thPat = uiNamespace getVariable')
    end = source.index('// cabin motion.', start)
    observe = adapted(source[start:end])
    execute(setup() + r'''
        private _display = missionNamespace;
        private _a = [0.1, 0.2]; private _b = [0.2, 0.3]; private _c = [0.3, 0.4];
        uiNamespace setVariable ["ACME_Thora_Prepping", true];
        uiNamespace setVariable ["ACME_Thora_PrepLocal", createHashMapFromArray [["right", [_a, _b]]]];
        _patient setVariable ["ACME_thora_prep_right", [_a, _c]];
        _patient setVariable ["ACME_thora_ver", 1];
    ''' + 'private _observe = {' + observe + '}; call _observe;' + r'''
        private _localPoints = (uiNamespace getVariable "ACME_Thora_PrepLocal") get "right";
        [count _localPoints == 3 && {_b in _localPoints} && {_c in _localPoints}, "remote update discarded unsent stroke or remote antiseptic"] call _check;
        // Prep replication can arrive after its revision without another version change.
        _patient setVariable ["ACME_thora_prep_right", [_a, _c, [0.4, 0.5]]];
        call _observe;
        [count ((uiNamespace getVariable "ACME_Thora_PrepLocal") get "right") == 4, "prep after revision was never observed"] call _check;
    ''')
