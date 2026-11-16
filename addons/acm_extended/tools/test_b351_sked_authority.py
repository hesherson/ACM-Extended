from test_menu_death_lifecycle import ROOT, adapt, execute

SKED = ROOT / "addons/acme_sked_ace"


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
