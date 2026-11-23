from test_menu_death_lifecycle import ROOT, adapt, execute

SKED = ROOT / "addons/acme_sked_ace"


def test_handle_claim_does_not_attach_or_drive_the_provider():
    for fn in ("bearerLocal", "srvTakeHandle", "srvLift", "srvSetDown"):
        source = (SKED / f"functions/fn_{fn}.sqf").read_text()
        assert "_unit attachTo" not in source
        assert "[_unit, _litter, \"follow\"" not in source
    claim = (SKED / "functions/fn_bearerLocal.sqf").read_text()
    assert '[_unit, "letGo"] call acme_sked_fnc_request' in claim


def test_talon_steps_preserve_each_endpoint_and_handle_order():
    import re

    # B366-B385 replaced the B373 handles-only swap with the full authored sequence played on four part models
    # (fn_talonTransition.sqf): folding puts the handles in first, unfolding takes them out last.
    source = (SKED / "functions/fn_talonSteps.sqf").read_text()
    step_re = r'\["(fold|handles)",\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)\]'
    fold, unfold = source.split('if (_mode == "fold") exitWith {', 1)[1].split("};", 1)
    for mode, state in ((fold, 1), (unfold, 0)):
        steps = [(kind, float(phase), float(sec), float(pause)) for kind, phase, sec, pause in re.findall(step_re, mode)]
        kinds = [kind for kind, *_ in steps]
        handles = [phase for kind, phase, *_ in steps if kind == "handles"]
        folds = [phase for kind, phase, *_ in steps if kind == "fold"]
        assert len(handles) == 4 and folds
        # every source reaches its endpoint and moves one way only
        for phases in (handles, folds):
            assert phases[-1] == state
            assert phases == sorted(phases, reverse=not state)
        # handle order: all handles before the fold when folding, all after it when unfolding
        assert kinds == (["handles"] * 4 + ["fold"] * len(folds) if state else ["fold"] * len(folds) + ["handles"] * 4)
        # the returned total is the sum of every step's seconds and pause
        total = float(re.search(r'\],\s*([\d.]+)\]', mode).group(1))
        assert abs(total - sum(sec + pause for _, _, sec, pause in steps)) < 1e-6


def test_server_checks_actor_ownership_and_distance_before_strapping():
    source = (SKED / "functions/fn_request.sqf").read_text()
    replacements = {
        "objNull, [objNull]": "objNull",
        '_actor isKindOf "CAManBase"': '_actor getVariable ["person", false]',
        '_target isKindOf "CAManBase"': '_target getVariable ["person", false]',
        '_extra isKindOf "ACME_SKED_Open"': '_extra getVariable ["openSked", false]',
        "isRemoteExecuted": "_remote",
        "local _actor": "_local",
        "owner _actor": "_owner",
        "remoteExecutedOwner": "_sender",
        "alive _actor": "_awake",
        "objectParent _actor": "objNull",
        "_actor distance _target": "_patientDistance",
        "_target distance _extra": "_skedDistance",
        '[_actor, _action, _target, _extra] remoteExecCall ["acme_sked_fnc_request", 2]': "{}",
    }
    for original, fixture in replacements.items():
        assert original in source
        source = source.replace(original, fixture)
    execute("private _request = {" + adapt(source) + "};" + r'''
        _medic setVariable ["person", true];
        _patient setVariable ["person", true];
        uiNamespace setVariable ["openSked", true];
        private _remote = true;
        private _local = false;
        private _owner = 8;
        private _sender = 7;
        private _awake = true;
        private _patientDistance = 1;
        private _skedDistance = 1;
        private _loaded = [];
        acme_sked_fnc_srvLoad = {_loaded pushBack _this};

        [_medic, "strap", _patient, uiNamespace] call _request;
        [_loaded isEqualTo [], "an impersonated actor strapped a patient in"] call _check;
        _sender = 8;
        _skedDistance = 4;
        [_medic, "strap", _patient, uiNamespace] call _request;
        [_loaded isEqualTo [], "a remote litter was used"] call _check;
        _skedDistance = 1;
        _awake = false;
        [_medic, "strap", _patient, uiNamespace] call _request;
        [_loaded isEqualTo [], "an incapacitated rescuer strapped a casualty in"] call _check;
        _awake = true;
        [_medic, "strap", _patient, uiNamespace] call _request;
        [_loaded isEqualTo [[_medic, _patient, uiNamespace]], "authorized nearby rescue failed"] call _check;
    ''')


def test_unit_owner_accepts_sked_actions_from_server_only():
    source = (SKED / "functions/fn_applyLocal.sqf").read_text()
    for original, fixture in (
        ("objNull, [objNull]", "objNull"),
        ("isRemoteExecuted", "_remote"),
        ("remoteExecutedOwner", "_sender"),
        ("local _unit", "_local"),
    ):
        assert original in source
        source = source.replace(original, fixture)
    execute("private _apply = {" + adapt(source) + "};" + r'''
        private _remote = true;
        private _sender = 7;
        private _local = true;
        private _applied = [];
        acme_sked_fnc_releaseLocal = {_applied pushBack _this};

        [_patient, "releaseLocal", [_patient, uiNamespace]] call _apply;
        [_applied isEqualTo [], "a peer released a casualty directly"] call _check;
        _sender = 2;
        [_patient, "releaseLocal", [_medic, uiNamespace]] call _apply;
        [_applied isEqualTo [], "owner action accepted an inconsistent target"] call _check;
        [_patient, "releaseLocal", [_patient, uiNamespace]] call _apply;
        [_applied isEqualTo [[_patient, uiNamespace]], "authorized release was lost"] call _check;
    ''')
