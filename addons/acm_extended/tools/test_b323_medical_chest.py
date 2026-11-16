"""Run the production chest state machine with mocked Arma objects and 3D commands."""
import re
import struct

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read


def request_fixture():
    request = adapt(read("medicalChestRequest"))
    transition = adapt(read("medicalChestSetOpen"))
    motion = adapt(read("medicalChestLidMotion"))
    for engine, stand_in in {
        "isMultiplayer": "false",
        "_lid setVectorDirAndUp [_dir, _up];": "_lid setVariable ['fixtureAxes', [_dir, _up]];",
        "_lid setPosWorld _position;": "_lid setVariable ['fixturePosition', _position];",
        "typeOf _cabinet": "'fixture cabinet'",
    }.items():
        assert engine in motion, engine
        motion = motion.replace(engine, stand_in)
    view = adapt(read("medicalChestView"))
    drawer_tick = adapt(read("medicalChestDrawerTick"))
    for engine, stand_in in {
        "isRemoteExecuted": "_remote",
        "remoteExecutedOwner": "_sender",
        "owner _actor": "_ownerNum",
        "alive _actor": "_alive",
        "_actor distance _cargo": "_distance",
        '_cargo isKindOf "ACME_MedicalChestCargo"': '_cargo getVariable ["fixtureCargo", false]',
        "typeOf _cabinet": "'fixture cabinet'",
    }.items():
        view = view.replace(engine, stand_in)
        drawer_tick = drawer_tick.replace(engine, stand_in)
    lid_base = adapt(read("medicalChestLidBase"))
    replacements = {
        'isRemoteExecuted': '_remote',
        'is3DEN': '_eden',
        'remoteExecutedOwner': '_sender',
        'alive _actor': '_alive',
        'owner _actor': '_ownerNum',
        '_chest isKindOf "ACME_MedicalChest"': '_chest getVariable ["fixtureChest", false]',
        '_actor distance _target': '_distance',
        'createVehicle [_class, ASLToATL _base, [], 0, "CAN_COLLIDE"]': '([_class] call _spawn)',
        'createSimpleObject ["ACME_MedicalChestLid", _seatPose select 0]':
            '(["ACME_MedicalChestLid"] call _spawn)',
        '    _cabinet allowDamage false;': '',
        'getObjectTextures _chest': '[_chest getVariable "fixtureTexture"]',
        'getObjectTextures _cabinet': '[_cabinet getVariable "fixtureTexture"]',
        'getObjectTextures _lid': '[_lid getVariable "fixtureTexture"]',
        '_cabinet setObjectTextureGlobal ["camo", _texture];': '_cabinet setVariable ["fixtureTexture", _texture];',
        '_lid setObjectTextureGlobal ["camo", _texture];': '_lid setVariable ["fixtureTexture", _texture];',
        '    _cabinet enableSimulationGlobal false;': '    _cabinet setVariable ["fixtureFrozen", true];',
        '    _cargo attachTo [_cabinet, [0, 0, 0]];': '    _cargo setVariable ["fixtureAttached", _cabinet];',
        '    detach _cargo;': '    _cargo setVariable ["fixtureAttached", objNull];',
        '    _cargo setPosWorld (_base vectorAdd [0, 0, -25]);': '',
        '_cabinet setVectorDirAndUp [_cabinetDir, _cabinetUp];':
            '_cabinet setVariable ["fixtureAxes", [_cabinetDir, _cabinetUp]];',
        '_cabinet setPosWorld _cabinetPosition;': '_cabinet setVariable ["fixturePosition", _cabinetPosition];',
        '_lid setVectorDirAndUp [_dir, _up];': "_lid setVariable ['fixtureAxes', [_dir, _up]];",
        '_lid setPosWorld _position;': "_lid setVariable ['fixturePosition', _position];",
        '_chest hideObjectGlobal true;': '_hidden = true;',
        '_chest hideObjectGlobal false;': '_hidden = false;',
        'playSound3D [format ["acm_extended\\sound\\%1.ogg", _sound], objNull, false, getPosWorld _chest, 1.5, 1, 18];':
            '_audio pushBack _sound;',
    }
    for engine, stand_in in replacements.items():
        assert engine in request or engine in transition, engine
        request = request.replace(engine, stand_in)
        transition = transition.replace(engine, stand_in)
    transition = re.sub(r'deleteVehicle ([^;]+);', r'_deleted pushBack (\1);', transition)
    definitions = (
        "private _request = {" + request + "};"
        "ACME_fnc_medicalChestSetOpen = {" + transition + "};"
        "ACME_fnc_medicalChestLidMotion = {" + motion + "};"
        "ACME_fnc_medicalChestLidBase = {" + lid_base + "};"
        "ACME_fnc_medicalChestView = {" + view + "};"
        "ACME_fnc_medicalChestDrawerTick = {" + drawer_tick + "};"
    )
    return definitions + r'''
        private _fixtureFloor = 0;
        ACME_fnc_medicalChestGround = {
            private _point = +(_this select 0);
            _point set [2, _fixtureFloor];
            [_point, [0, 0, 1]]
        };
        private _chest = _patient;
        private _cargo = missionNamespace;
        private _created = [];
        private _deleted = [];
        private _audio = [];
        private _placed = [];
        private _gearRequests = [];
        private _drawers = [];
        private _motion = [];
        private _drawerMotion = [];
        private _removedMotion = [];
        private _tickDrawers = {
            CBA_missionTime = CBA_missionTime + _this;
            [_drawerMotion select 2, 31] call (_drawerMotion select 0);
        };
        private _tickLid = {
            private _remote = false;
            CBA_missionTime = CBA_missionTime + _this;
            [_motion select 2, 30] call (_motion select 0);
        };
        private _hidden = false;
        private _failLid = false;
        private _remote = true;
        private _eden = false;
        private _sender = _ownerNum;
        private _spawn = {
            params ["_class"];
            _created pushBack _class;
            if (_class == "ACME_MedicalChestLid") exitWith {
                if (_failLid) then {objNull} else {parsingNamespace}
            };
            uiNamespace
        };
        _chest setVariable ["fixtureChest", true];
        _chest setVariable ["fixtureTexture", "fixture_body_co.paa"];
        _chest setVariable ["ACME_medicalChestPlacement", [[20, 12, 0], 90]];
        _chest setVariable ["ACME_medicalChestState", [0, false]];
        _chest setVariable ["ACME_medicalChestCargo", _cargo];
        _cargo setVariable ["fixtureCargo", true];
        _cargo setVariable ["ACME_medicalChestAnchor", _chest];
        _cargo setVariable ["stock", ["ACM_IV_18g", "ACM_ACCUVAC"]];
        ACME_fnc_medicalChestPlace = {
            _placed pushBack _this;
            [(_this select 1) vectorAdd [0,0,0.05], [0,0,1], [0,1,0], [0,0,1]]
        };
        ACME_fnc_medicalChestLidSeat = {[[20, 11.88, 0.43], [0,-1,0], [1,0,0]]};
        ACME_fnc_medicalChestDrawerPlan = { [["drawer"], [0.63], true]};
        ACME_fnc_medicalChestDrawers = {_drawers pushBack _this;};
        CBA_fnc_addPerFrameHandler = {
            if (count (_this select 2) == 4) exitWith {_drawerMotion = _this; 31};
            _motion = _this;
            30
        };
        CBA_fnc_removePerFrameHandler = {_removedMotion append _this;};
        CBA_fnc_globalEvent = {_events pushBack _this;};
        CBA_fnc_targetEvent = {_gearRequests pushBack _this;};
    '''


def test_chest_reopen_retains_live_supply_container_and_ignores_stale_requests():
    execute(request_fixture() + '''
        [_chest, _medic, true, 0] call _request;
        private _open = _chest getVariable "ACME_medicalChestCabinet";
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [0,false] && {_hidden}, "inventory became available during the visual swap"] call _check;
        [count _created == 2 && {count _drawers == 1} && {count _placed == 2}, "missing lid or independently animated cabinet"] call _check;
        private _lid = _chest getVariable "ACME_medicalChestLid";
        [(_open getVariable "fixtureTexture") isEqualTo (_chest getVariable "fixtureTexture")
            && {(_lid getVariable "fixtureTexture") isEqualTo (_chest getVariable "fixtureTexture")},
            "cabinet or lid lost the closed chest's native albedo"] call _check;
        [((_placed select 1 select 1) vectorDistance [20.82, 12, 0]) < .001 && {(_placed select 1 select 5) isEqualTo false}, "lid used the cabinet footprint or remained upright"] call _check;
        [_chest, _medic, true, 0] call _request;
        [count _created == 2, "concurrent open spawned extra visuals"] call _check;
        [(_open getVariable ["fixtureFrozen", false]) && {(_drawers select 0 select 2) == 0}, "cabinet was free to tip or drawers began open"] call _check;
        [_open, _medic, false, 1] call _request;
        [_gearRequests isEqualTo [], "early close or Gear interrupted the animation"] call _check;
        1.00 call _tickLid;
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [1,true] && {_hidden}, "opening did not publish the finished cabinet"] call _check;
        [_gearRequests isEqualTo [["ACME_medicalChestOpened", [_medic, _chest, _cargo, 1], _medic]], "open did not send exactly one Gear request to the initiating player"] call _check;
        _cargo setVariable ["stock", ["ACM_ACCUVAC", "ACE_tourniquet"]];
        [_open, _medic, false, 1] call _request;
        [_open, _medic, false, 1] call _request;
        [(_chest getVariable "ACME_medicalChestTransition") && {_hidden}
            && {_events isEqualTo [["ACME_medicalChestClosing", [_cargo, 1]]]}, "closing swapped models or missed the Gear close signal"] call _check;
        1.00 call _tickLid;
        [(_chest getVariable "fixtureTexture") isEqualTo "fixture_body_co.paa", "closing changed the original finish"] call _check;
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [2,false] && {!_hidden}, "close left the chest open"] call _check;
        [_chest, _medic, true, 0] call _request;
        [count _created == 2, "old open replayed after the chest closed"] call _check;
        [_chest, _medic, true, 2] call _request;
        [(_chest getVariable "ACME_medicalChestCargo") isEqualTo _cargo && {(_cargo getVariable "stock") isEqualTo ["ACM_ACCUVAC", "ACE_tourniquet"]}, "using drawers refilled or discarded live cargo"] call _check;
        [_audio isEqualTo ["medical_chest_open", "medical_chest_close", "medical_chest_open"], "transition failed to emit exactly one matching sound"] call _check;
    ''')


def test_lid_only_request_and_inventory_request_offer_different_gear_behavior():
    inventory = adapt(read("medicalChestInventory"))
    for engine, fixture in (
        ('local _actor', 'true'),
        ('alive _actor', '_alive'),
        ('_actor distance _target', '_distance'),
        ('remoteExecCall ["ACME_fnc_medicalChestRequest", 2]', 'call _request'),
    ):
        inventory = inventory.replace(engine, fixture)
    execute(request_fixture() + 'private _inventory={' + inventory + '};' + r'''
        ACME_fnc_medicalChestTarget = {
            [_chest] + (_chest getVariable "ACME_medicalChestState")
        };
        CBA_fnc_localEvent = {_gearRequests pushBack _this;};
        [_chest, _medic, true, 0, false] call _request;
        1.00 call _tickLid;
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [1,true] && {_gearRequests isEqualTo []},
            "the lid-only ACE action opened Gear"] call _check;
        private _cabinet = _chest getVariable "ACME_medicalChestCabinet";
        [_cabinet, _medic] call _inventory;
        [_gearRequests isEqualTo [["ACME_medicalChestOpened", [_medic, _chest, _cargo, 1]]],
            "Inventory on an uncovered chest did not reuse its live cargo"] call _check;
        [_cabinet, _medic, false, 1] call _request;
        1.00 call _tickLid;
        [_chest, _medic] call _inventory;
        [count _gearRequests == 1 && {(_chest getVariable "ACME_medicalChestTransition")}, "Inventory skipped the lid motion"] call _check;
        1.00 call _tickLid;
        [(count _gearRequests == 2) && {(_gearRequests select 1) isEqualTo ["ACME_medicalChestOpened", [_medic, _chest, _cargo, 3], _medic]},
            "Inventory on a covered chest failed to request Gear after the lid opened"] call _check;
    ''')


def test_lid_clears_the_cabinet_before_turning_and_retraces_the_path_on_close():
    execute(request_fixture() + r'''
        [_chest, _medic, true, 0] call _request;
        private _lid = _chest getVariable "ACME_medicalChestLid";
        private _cab = _chest getVariable "ACME_medicalChestCabinet";
        private _start = _lid getVariable "fixturePosition";
        private _upright = [[0,-1,0],[0,0,1]];
        private _flat = [[0,0,1],[0,1,0]];
        private _faceIndex = 0;
        [abs ((_start select 1) - 11.88) < 0.001 && {(_lid getVariable "fixtureAxes") isEqualTo _upright},
            "the lid did not start seated"] call _check;
        private _sample = {
            _this call _tickLid;
            private _pos = _lid getVariable "fixturePosition";
            private _axes = _lid getVariable "fixtureAxes";
            [(_lid getVariable "fixtureTexture") isEqualTo (_chest getVariable "fixtureTexture"),
                "the lid lost its native paint during motion"] call _check;
            [_pos, _axes]
        };
        (0.10 call _sample) params ["_earlyPull", "_earlyAxes"];
        [(_earlyPull select 0) == 20 && {(_earlyPull select 1) < 11.88} && {(_earlyPull select 1) > 11.8} && {(_earlyPull select 2) == (_start select 2)}
            && {_earlyAxes isEqualTo _upright}, "the lid finished the straight pull too early"] call _check;
        (0.08 call _sample) params ["_pop", "_popAxes"];
        [(_pop select 0) == 20 && {abs ((_pop select 1) - 11.77) < .001}
            && {(_pop select 2) == (_start select 2)} && {_popAxes isEqualTo _upright},
            "the lid did not pull a short distance straight out from the painted face"] call _check;
        private _slideStart = ((0.04 call _sample) select 0) select 0;
        private _slideEarly = ((0.07 call _sample) select 0) select 0;
        (0.07 call _sample) params ["_slide", "_slideAxes"];
        [(_slide select 0) > 20.25 && {(_slide select 0) < 20.5}
            && {abs ((_slide select 1) - (_pop select 1)) < .001} && {_slideAxes isEqualTo _upright},
            "lid turned or moved backwards while carrying sideways"] call _check;
        [((_slide select 0) - _slideEarly) > 1.2 * (_slideEarly - _slideStart),
            "slide did not ramp up to its faster middle section"] call _check;
        (0.20 call _sample) params ["_outboard", "_outboardAxes"];
        [abs ((_outboard select 0) - 20.82) < .001 && {abs ((_outboard select 1) - 11.77) < .001}
            && {_outboardAxes isEqualTo _upright}, "lid began to turn before it was beside the cabinet"] call _check;
        (0.125 call _sample) params ["_turn", "_turnAxes"];
        [abs ((_turn select 0) - 20.82) < .001 && {(_turn select 1) < 12} && {(_turn select 1) > 11.77}
            && {(_turnAxes select _faceIndex select 2) > 0} && {_gearRequests isEqualTo []},
            "lid failed to tip into its original depth after clearing the cabinet"] call _check;
        (0.235 call _sample) params ["_settling", "_settlingAxes"];
        [(_settling select 2) > .05 && {(_settling select 2) < .08} && {_settlingAxes isEqualTo _flat}
            && {abs ((_settling select 1) - 12) < .001} && {_gearRequests isEqualTo []},
            "lid hovered or moved sideways instead of settling down"] call _check;
        (0.10 call _sample) params ["_rest", "_restAxes"];
        [(_rest vectorDistance [20.82,12,0.05]) < .001 && {_restAxes isEqualTo _flat}
            && {count _gearRequests == 1} && {count _drawers == 1} && {_removedMotion isEqualTo [30]},
            "Gear opened early or the drawers opened without a viewer"] call _check;
        [_cab, _medic, false, 1] call _request;
        (0.305 call _sample) params ["_reverse", "_reverseAxes"];
        [(_reverse vectorDistance _turn) < 0.001 && {((_reverseAxes select _faceIndex) vectorDistance (_turnAxes select _faceIndex)) < 0.001},
            "closing did not retrace the opening motion"] call _check;
        (0.70 call _sample) params ["_seated", "_seatedAxes"];
        [_seated isEqualTo _start && {_seatedAxes isEqualTo _upright} && {!_hidden}
            && {(_chest getVariable "ACME_medicalChestState") isEqualTo [2,false]}, "lid did not reseat before the shell swap"] call _check;
    ''')


def test_lid_starts_at_the_hardigg_seam_and_lands_on_the_original_side():
    seat = adapt(read("medicalChestLidSeat"))
    base = adapt(read("medicalChestLidBase"))
    execute(placement_fixture() + "private _seatLid = {" + seat + "}; private _lidBase = {" + base + "};" + r'''
        ACME_fnc_medicalChestGround = {[_this select 0, [0, 0, 1]]};
        private _anchor = [20, 12, 0];
        {
            private _heading = _x;
            private _cabinet = [_medic, _anchor, _heading, "cabinet", [0,0,1], false] call _place;
            ([_cabinet] call _seatLid) params ["_seat", "_outward", "_side"];
            private _front = [-cos _heading, sin _heading, 0];
            private _lateral = [sin _heading, cos _heading, 0];
            [(_outward vectorDistance _front) < .0001 && {(_side vectorDistance _lateral) < .0001},
                "pull or lateral axis rotated away from the new cover"] call _check;
            [(_seat vectorDistance (_anchor vectorAdd (_front vectorMultiply .1175) vectorAdd [0,0,.416])) < .0001,
                "the detached model did not begin at its original origin"] call _check;
            private _landing = ([_anchor, _heading, _patient, _medic] call _lidBase) select 0;
            [(_landing vectorDistance (_anchor vectorAdd (_lateral vectorMultiply .82))) < .0001,
                "lid landed outside the original side placement"] call _check;
        } forEach [0, 90, 172, 270];
    ''')


def test_lid_rises_over_a_step_in_its_release_path():
    execute(request_fixture() + r'''
        _fixtureFloor = 0.26;
        [_chest, _medic, true, 0] call _request;
        private _cover = _chest getVariable "ACME_medicalChestLid";
        0.181 call _tickLid;
        private _pop = _cover getVariable "fixturePosition";
        [(_pop select 1) < 11.78 && {(_pop select 2) < .431},
            "the lid rose before the straight release finished"] call _check;
        0.385 call _tickLid;
        private _turn = _cover getVariable "fixturePosition";
        [(_turn select 0) > 20.8 && {(_turn select 2) - .415 > .26},
            "the lid cut down through the raised support before tipping"] call _check;
    ''')


def test_one_drawer_always_has_a_clear_lead_at_full_extension():
    source = adapt(read("medicalChestDrawerPlan"))
    source = re.sub(r"configProperties \[[\s\S]+?\n\];", "_drawerNames;", source, count=1)
    source = source.replace("configName _x", "_x")
    # Force the highest secondary phase to test the worst case for tied extension.
    source = re.sub(r"selectRandom (\[[^\]]+\])", r"(selectMax \1)", source)
    execute("private _planDrawers={" + source + "};" + r'''
        {
            private _drawerNames = [];
            for "_index" from 1 to _x do {
                _drawerNames pushBack format ["Drawer_%1_move_source", _index];
            };
            ([_patient] call _planDrawers) params ["_names", "_phases", "_sources"];
            private _furthest = selectMax _phases;
            private _other = _phases select {_x != _furthest};
            [count _names == _x && {count _other == _x - 1} && {_furthest - selectMax _other > .25},
                "drawers tied or opened nearly the same amount"] call _check;
        } forEach [4,7];
    ''')


def test_drawers_follow_multiple_viewers_and_retract_before_the_lid_moves():
    execute(request_fixture() + r'''
        [_chest, _medic, true, 0] call _request;
        1.00 call _tickLid;
        private _cab = _chest getVariable "ACME_medicalChestCabinet";
        private _lid = _chest getVariable "ACME_medicalChestLid";
        private _rest = _lid getVariable "fixturePosition";
        private _other = parsingNamespace;
        _sender = 9;
        [_cargo, _medic, 1, true] call ACME_fnc_medicalChestView;
        _sender = _ownerNum;
        [_cargo, _medic, 0, true] call ACME_fnc_medicalChestView;
        [_drawerMotion isEqualTo [], "unauthorized or stale viewing opened drawers"] call _check;
        [_cargo, _medic, 1, true] call ACME_fnc_medicalChestView;
        [_cargo, _other, 1, true] call ACME_fnc_medicalChestView;
        0.12 call _tickDrawers;
        private _half = (_drawers select (count _drawers - 1)) select 2;
        [_half > 0 && {_half < 1}, "inventory opening jumped to the full drawer phase"] call _check;
        [_cargo, _medic, 1, false] call ACME_fnc_medicalChestView;
        0.13 call _tickDrawers;
        [(_chest getVariable "ACME_medicalChestDrawerFraction") == 1, "drawers retracted with another viewer still in Gear"] call _check;
        [_cargo, _other, 1, false] call ACME_fnc_medicalChestView;
        0.12 call _tickDrawers;
        [(_chest getVariable "ACME_medicalChestDrawerFraction") < 1, "leaving Gear did not retract drawers"] call _check;
        [_cargo, _medic, 1, true] call ACME_fnc_medicalChestView;
        0.15 call _tickDrawers;
        [(_chest getVariable "ACME_medicalChestDrawerFraction") == 1, "quick reopen did not reverse the drawers"] call _check;
        [_cab, _medic, false, 1] call _request;
        [_cargo, _other, 1, true] call ACME_fnc_medicalChestView;
        0.10 call _tickLid;
        0.10 call _tickDrawers;
        [(_lid getVariable "fixturePosition") isEqualTo _rest && {(_chest getVariable "ACME_medicalChestViewers") isEqualTo []},
            "lid moved over extended drawers or Gear opened during closing"] call _check;
        0.15 call _tickDrawers;
        [(_chest getVariable "ACME_medicalChestDrawerFraction") == 0, "drawers were still extended after closing Gear"] call _check;
        1.00 call _tickLid;
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [2,false] && {!_hidden}, "lid failed to close after the drawers retracted"] call _check;
    ''')


def test_drawers_retract_if_the_viewer_stops_reporting():
    execute(request_fixture() + r'''
        [_chest, _medic, true, 0] call _request;
        1.00 call _tickLid;
        [_cargo, _medic, 1, true] call ACME_fnc_medicalChestView;
        0.25 call _tickDrawers;
        [(_chest getVariable "ACME_medicalChestDrawerFraction") == 1, "view did not extend drawers"] call _check;
        3.01 call _tickDrawers;
        [(_chest getVariable "ACME_medicalChestDrawerFraction") == 0
            && {(_chest getVariable "ACME_medicalChestViewers") isEqualTo []}
            && {31 in _removedMotion}, "lost viewer left the drawers out"] call _check;
    ''')


def test_inventory_reports_require_a_gear_display_and_end_when_it_goes_away():
    runtime = adapt(read("registerMedicalChestRuntime"))
    end_viewing = adapt(read("medicalChestEndViewing"))
    for command, mock in {
        '_unit addEventHandler [': '[',
        '    }];': '    }] call _addInventoryHandler;',
        '_x isKindOf "ACME_MedicalChestCargo"': '_x isEqualTo missionNamespace',
        'isNull (findDisplay 602)': '!_visible',
        'findDisplay 602': 'objNull',
        'alive _unit': '_alive',
        '_unit distance _cargo': '_distance',
        '_unit distance _aim': '_distance',
        '_unit distance _target': '_distance',
        'cursorObject': '_aimObject',
        'cursorTarget': '_aimObject',
        'isNull ACE_player': 'ACE_player isEqualTo objNull',
        ' remoteExecCall ["ACME_fnc_medicalChestView", 2]': ' call _report',
    }.items():
        runtime = runtime.replace(command, mock)
        end_viewing = end_viewing.replace(command, mock)
    runtime = re.sub(r'_previous removeEventHandler \[[^;]+];', '', runtime)
    execute(r'''
        private _inventoryHandlers = [];
        private _inventoryPoll = {};
        private _reports = [];
        private _visible = false;
        private _aimObject = objNull;
        private _requests = [];
        CBA_fnc_execNextFrame = {(_this select 1) call (_this select 0);};
        ACME_fnc_medicalChestInventory = {_requests pushBack _this;};
        ACME_fnc_medicalChestTarget = {
            if ((_this select 0) isEqualTo _patient) exitWith {[_patient, 1, true]};
            []
        };
        private _addInventoryHandler = {
            _inventoryHandlers pushBack _this;
        };
        private _report = {_reports pushBack _this;};
        CBA_fnc_addPlayerEventHandler = {[_medic, objNull] call (_this select 1);};
        CBA_fnc_addPerFrameHandler = {_inventoryPoll = _this select 0;};
        CBA_fnc_addEventHandler = {};
        private _cargo = missionNamespace;
        _cargo setVariable ["ACME_medicalChestAnchor", _patient];
        _patient setVariable ["ACME_medicalChestState", [1, true]];
    ''' + "ACME_fnc_medicalChestEndViewing = {" + end_viewing + "};"
        + "call {" + runtime + "};" + r'''
        private _opened = _inventoryHandlers select 0 select 1;
        private _closed = _inventoryHandlers select 1 select 1;
        [[_medic, _patient, objNull] call _opened, "native Gear on the crate bypassed the shared animation path"] call _check;
        _aimObject = _patient;
        [[_medic, _medic, objNull] call _opened, "inventory hotkey while pointing at a crate did not use the shared path"] call _check;
        [!([_medic, parsingNamespace, objNull] call _opened), "a nearby chest intercepted a different container's Gear"] call _check;
        [_requests isEqualTo [[_patient,_medic],[_patient,_medic]], "vanilla routes did not request that crate's Gear"] call _check;
        [_medic, _cargo, objNull] call _opened;
        call _inventoryPoll;
        CBA_missionTime = CBA_missionTime + 1;
        call _inventoryPoll;
        [_reports isEqualTo [], "an inventory blocked by another handler reported a viewer"] call _check;
        [_medic, objNull, _cargo] call _opened;
        _visible = true;
        call _inventoryPoll;
        [count _reports == 1 && {(_reports select 0) isEqualTo [_cargo, _medic, 1, true]},
            "visible secondary inventory did not report a viewer"] call _check;
        _visible = false;
        call _inventoryPoll;
        [count _reports == 2 && {(_reports select 1) isEqualTo [_cargo, _medic, 1, false]},
            "losing the Gear display did not report departure"] call _check;
        _visible = true;
        [_medic, _cargo, objNull] call _opened;
        call _inventoryPoll;
        [_medic, _cargo] call _closed;
        [count _reports == 4 && {(_reports select 3) isEqualTo [_cargo, _medic, 1, false]},
            "InventoryClosed did not report departure immediately"] call _check;
    ''')


def test_missing_lid_cancels_the_motion_and_allows_a_fresh_open():
    execute(request_fixture() + r'''
        [_chest, _medic, true, 0] call _request;
        (_motion select 2) set [2, objNull];
        _chest setVariable ["ACME_medicalChestLid", objNull];
        0.15 call _tickLid;
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [1,false] && {!_hidden}
            && {_gearRequests isEqualTo []} && {_removedMotion isEqualTo [30]},
            "interrupted opening did not restore the closed shell"] call _check;
        [_chest, _medic, true, 1] call _request;
        1.00 call _tickLid;
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [2,true] && {count _gearRequests == 1},
            "interrupted opening blocked future use"] call _check;
    ''')


def test_mission_start_open_and_later_close_share_the_same_cargo():
    execute(request_fixture() + r'''
        [_chest, true, 0, true] call ACME_fnc_medicalChestSetOpen;
        [count _created == 0, "remote caller entered the initialization path"] call _check;
        _remote = false;
        [_chest, true, 0, true] call ACME_fnc_medicalChestSetOpen;
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [1,true], "initial lid state was closed"] call _check;
        [(_created select 0) isEqualTo "ACME_MedicalChest8Drawers", "initial drawer layout differs from Eden"] call _check;
        [(_drawers select 0 select 2) == 0 && {_motion isEqualTo []}
            && {_audio isEqualTo []} && {_gearRequests isEqualTo []}, "initialization animated the drawers or played audio"] call _check;
        [(_cargo getVariable "fixtureAttached") isEqualTo (_chest getVariable "ACME_medicalChestCabinet"), "open chest did not expose the live cargo"] call _check;
        private _open = _chest getVariable "ACME_medicalChestCabinet";
        [_open, _medic, false, 1] call _request;
        1.00 call _tickLid;
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [2,false] && {(_cargo getVariable "stock") isEqualTo ["ACM_IV_18g", "ACM_ACCUVAC"]}, "initially open chest failed to close with stock intact"] call _check;
    ''')


def test_eden_preview_is_local_and_uses_the_saved_state_and_live_assets():
    config = (ROOT / "addons/acm_extended/config.cpp").read_text()
    chest = (ROOT / "addons/acm_extended/MedicalChestVehicles.hpp").read_text()
    eden = read("medicalChestEden")
    init = read("medicalChestInit")
    for handler in ("onMissionLoad", "onMissionNew", "onBeforeMissionPreview", "onMissionPreviewEnd",
                    "onEditableEntityAdded", "onEditableEntityRemoved", "onEntityAttributeChanged", "onEntityDragged"):
        assert re.search(rf'{handler} = "[^\n]+call ACME_fnc_medicalChestEden', config)
    assert 'if (!is3DEN) exitWith' in eden
    assert 'get3DENAttribute "ACME_medicalChestStartOpen"' in eden
    assert 'property = "ACME_medicalChestStartOpen"' in chest
    assert 'getVariable ["ACME_medicalChestStartOpen", false]' in init
    assert 'createSimpleObject [_class, _base, true]' in eden
    assert '_x setObjectTexture ["camo", _texture]' in eden
    assert 'set3DENAttribute' not in eden and 'create3DENEntity' not in eden
    assert 'ACME_fnc_medicalChestStock' not in eden


@pytest.mark.parametrize("cause,spawn_calls", [("_sender=8;", 0), ("_distance=5;", 0), ("_failLid=true;", 2)])
def test_denied_or_failed_open_leaves_stock_and_state_intact(cause, spawn_calls):
    execute(request_fixture() + cause + f'''
        [_chest, _medic, true, 0] call _request;
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [0,false] && {{!_hidden}}, "failed request left a partial swap"] call _check;
        [count _created == {spawn_calls} && {{_audio isEqualTo []}} && {{_gearRequests isEqualTo []}}, "invalid spawn or success sound"] call _check;
        [(_cargo getVariable "stock") isEqualTo ["ACM_IV_18g", "ACM_ACCUVAC"], "failed request changed stock"] call _check;
    ''')


def placement_fixture():
    source = read("medicalChestPlace")
    for engine, fixture in (
        ("0 boundingBoxReal _object", "_bounds"),
        ("_object setVectorDirAndUp [_dir, _up];", "_orient = [_dir, _up];"),
        ("_object setPosWorld", "_worldPosition ="),
    ):
        assert engine in source
        source = source.replace(engine, fixture)
    return "private _place={" + source + "};"


@pytest.mark.parametrize("heading", [0, 90, 228])
def test_hardigg_cabinet_and_closed_chest_use_the_same_pose(heading):
    execute(placement_fixture() + f'''
        private _base = [20,12,1];
        private _closed = [_patient, _base, {heading}, "closed", [0,0,1], false] call _place;
        private _open = [_medic, _base, {heading}, "cabinet", [0,0,1], false] call _place;
        [_closed isEqualTo _open && {{(_open select 0) isEqualTo _base}} && {{(_open select 2) isEqualTo [0,0,1]}},
            "opening moved or tilted the case"] call _check;
    ''')


@pytest.mark.parametrize("normal", ["[0,0,1]", "[0.3,0.2,0.9327]"])
def test_hardigg_lid_paint_faces_up_and_the_inner_face_follows_the_support(normal):
    execute(placement_fixture() + f'''
        private _bounds = [[-.270,-.048,-.423],[.270,.048,.423]];
        private _orient = [];
        private _worldPosition = [];
        private _normal = vectorNormalized {normal};
        private _base = [20,12,1];
        [_medic, _base, 73, "lid", _normal] call _place;
        [((_orient select 0) vectorDotProduct _normal) > .999, "lid failed to show the painted face"] call _check;
        [abs (((_worldPosition vectorDiff _base) vectorDotProduct _normal) - .056) < .0001,
            "lid failed to rest at the height of its inner face"] call _check;
        [(_worldPosition select [0,2]) isEqualTo (_base select [0,2]), "sloped placement pulled the lid out of its sideways path"] call _check;
    ''')


def test_ground_hit_passes_surface_normal_to_the_lid():
    source = read("medicalChestGround")
    start = source.index("lineIntersectsSurfaces")
    end = source.index("];", start) + 1
    source = source[:start] + "_mockHits" + source[end:]
    source = source.replace("ATLToASL [_origin select 0, _origin select 1, 0]", "[0,0,0]")
    source = source.replace("surfaceNormal [_origin select 0, _origin select 1]", "[0,0,1]")
    execute("private _ground={" + source + "};" + r'''
        private _mockHits = [[[20,12,1], [0,.6,.8], _patient, _patient]];
        private _lid = [[20,12,1], [], 1, 1, false, true] call _ground;
        [_lid isEqualTo [[20,12,1], [0,.6,.8]], "lid ray used an object reference instead of the support normal"] call _check;
        private _cabinet = [[20,12,1], [], 1, 1] call _ground;
        [_cabinet isEqualTo [20,12,1], "cabinet grounding no longer returns its position"] call _check;
    ''')


def test_chest_actions_share_one_ace_root_and_gear_waits_for_matching_open_state():
    vehicles = (ROOT / "addons/acm_extended/MedicalChestVehicles.hpp").read_text()
    runtime = read("registerMedicalChestRuntime")
    assert vehicles.count('class ACE_MainActions {') == 2
    assert 'class ACE_Actions {class ACE_MainActions {condition = "false";};};' in vehicles
    assert 'ACME_MEDICAL_CHEST_ACTIONS(ACME_OpenMedicalChest' in vehicles
    assert 'ACME_MEDICAL_CHEST_ACTIONS(ACME_CloseMedicalChest' in vehicles
    assert 'displayName = "Medical Chest Inventory"' in vehicles
    assert '[this,ACE_player] call ACME_fnc_medicalChestInventory' in vehicles
    assert '[_target,_player] call ACME_fnc_medicalChestInventory' in vehicles
    assert "[_target,_player,true] call ACME_fnc_medicalChestUse" in vehicles
    assert "[_target,_player,false] call ACME_fnc_medicalChestUse" in vehicles
    assert "[_target,_player,true] call ACME_fnc_medicalChestCanUse" in vehicles
    assert "[_target,_player,false] call ACME_fnc_medicalChestCanUse" in vehicles
    assert 'isEqualTo [_revision, true]' in runtime
    assert 'attachedTo _cargo isNotEqualTo objNull' in runtime
    assert '_actor action ["Gear", _this select 2]' in runtime


def test_overlapping_chests_offer_only_the_pointed_active_case_action():
    source = read("medicalChestCanUse")
    target = read("medicalChestTarget")
    for engine, fixture in (
        ('isObjectHidden _target', '(_target getVariable ["hidden",false])'),
        ('cursorObject', '_aimObject'), ('cursorTarget', '_aimObject'),
        ('_actor distance _aim', '1'),
        ('_target isKindOf "ACME_MedicalChest"', '(_target getVariable ["closedClass",false])'),
    ):
        assert engine in source or engine in target
        source = source.replace(engine, fixture)
        target = target.replace(engine, fixture)
    execute('ACME_fnc_medicalChestTarget={' + adapt(target) + '};'
            + 'private _canUse={' + adapt(source) + '};' + r'''
        ace_common_fnc_canInteractWith={true};
        private _cabinet=parsingNamespace;
        private _other=missionNamespace;
        private _stale=uiNamespace;
        _patient setVariable ["closedClass",true];
        _other setVariable ["closedClass",true];
        _patient setVariable ["ACME_medicalChestState",[1,true]];
        _other setVariable ["ACME_medicalChestState",[0,false]];
        {_x setVariable ["ACME_medicalChestAnchor",_patient];} forEach [_cabinet,_stale];
        _patient setVariable ["ACME_medicalChestCabinet",_cabinet];
        private _aimObject=_cabinet;
        [[_cabinet,_medic,false] call _canUse,"active cabinet has no close action"] call _check;
        [!([_patient,_medic,true] call _canUse),"open chest still offers Open"] call _check;
        [!([_stale,_medic,false] call _canUse),"superseded cabinet still offers Close"] call _check;
        [!([_other,_medic,true] call _canUse),"neighbor's Open overlaps the targeted Close"] call _check;
        _aimObject=_other;
        [[_other,_medic,true] call _canUse,"closed neighbor has no Open when pointed at"] call _check;
        [!([_cabinet,_medic,false] call _canUse),"neighbor's Close overlaps the targeted Open"] call _check;
        _other setVariable ["hidden",true];
        [!([_other,_medic,true] call _canUse),"hidden case appears in ACE"] call _check;
    ''')


def test_live_catalog_routes_generous_medical_stock_to_matching_containers():
    source = read("medicalChestStock")
    source = source.replace('_cargo addItemCargoGlobal [_x, _count]', '_itemsOut pushBack [_x, _count]')
    source = source.replace('_cargo addMagazineCargoGlobal [_x, _count]', '_magazinesOut pushBack [_x, _count]')
    source = source.replace('_cargo addBackpackCargoGlobal [_x, _count]', '_packsOut pushBack [_x, _count]')
    source = re.sub(r'getNumber \(configFile >> "Cfg(?:Weapons|Magazines)" >> _x >> "scope"\) == 2', 'false', source)
    source = source.replace('getNumber (configFile >> "CfgVehicles" >> _x >> "isBackpack") == 1', '_x == "MedicalBackpack"')
    execute('private _stock={' + adapt(source) + '};' + r'''
        private _itemsOut = []; private _magazinesOut = []; private _packsOut = [];
        missionNamespace setVariable ["ACME_medicalChestCatalog",
            [["ACME_TempusLS_Item","ACME_IVStartKit_18g","ACM_ETTube","ACM_CombatGauze","ACM_BloodBag_ON_500",
              "ACME_Vial_Propofol","ACME_SalineBag_100","ACM_Syringe_5"],
             ["ACM_OxygenTank_425","ACM_Syringe_5_Epinephrine"],["MedicalBackpack","HealthVehicle"]]];
        [_patient] call _stock;
        [["ACME_TempusLS_Item",4] in _itemsOut && {["ACME_IVStartKit_18g",24] in _itemsOut}
            && {["ACME_Vial_Propofol",8] in _itemsOut} && {count _itemsOut==8}, "generic stock is incomplete"] call _check;
        [_magazinesOut isEqualTo [["ACM_OxygenTank_425",4],["ACM_Syringe_5_Epinephrine",8]], "charge-bearing cargo used the wrong type or count"] call _check;
        [_packsOut isEqualTo [["MedicalBackpack",4]], "whole vehicles treated as backpacks"] call _check;
        _itemsOut=[]; _magazinesOut=[]; _packsOut=[];
        [_patient,"airway"] call _stock;
        [_itemsOut isEqualTo [["ACM_ETTube",8]] && {_magazinesOut isEqualTo [["ACM_OxygenTank_425",4]]}, "airway stock was missing supplies or included unrelated items"] call _check;
        _itemsOut=[]; _magazinesOut=[];
        [_patient,"blood"] call _stock;
        [["ACM_BloodBag_ON_500",8] in _itemsOut && {["ACM_Syringe_5",8] in _itemsOut} && {_magazinesOut isEqualTo []}, "blood stock omitted supplies or included unrelated medicines"] call _check;
        _itemsOut=[];
        [_patient,"fluids"] call _stock;
        [["ACME_SalineBag_100",8] in _itemsOut && {(["ACM_BloodBag_ON_500",8] in _itemsOut) isEqualTo false}, "fluid chest did not prioritize crystalloid stock"] call _check;
    ''')


def test_editor_class_and_art_are_wired_to_the_cabinet_variants():
    addon = ROOT / "addons/acm_extended"
    config = (addon / "config.cpp").read_text()
    vehicles = (addon / "MedicalChestVehicles.hpp").read_text()
    assert 'units[] = {"ACME_MedicalChest"' in config
    assert 'class ACME_MedicalChest: ACME_MedicalChestVisual' in vehicles
    assert 'class ACME_MedicalChest8Drawers: ACME_MedicalChestVisual' in vehicles
    assert "ACME_CHEST_DRAWER(8)" in vehicles
    assert "hiddenSelectionsTextures[] = {ACME_CHEST_TEXTURE(0)}" in vehicles
    assert "hiddenSelectionsTextures[] = {ACME_CHEST_TEXTURE(NUMBER)}" in vehicles
    folder = addon / "data/medical_chest/hardigg"
    for number in range(12):
        if number:
            name = f"ACME_MedicalChest_{number:02d}"
            assert f'"{name}"' in config
            assert f"ACME_MEDICAL_CHEST_RETEXTURE({name},{number}," in vehicles
        assert (folder / f"case_{number}_co.paa").read_bytes().startswith(b"\x01\xff")
    for name in ("open", "close"):
        assert (addon / "sound" / f"medical_chest_{name}.ogg").read_bytes().startswith(b"OggS")


def test_hardigg_closed_and_detached_lid_use_the_same_unmirrored_uvs():
    def outside_faces(path, origin):
        data = path.read_bytes()
        _, _, points, normals, faces, _ = struct.unpack_from("<6I", data, 16)
        offset = 40 + 16 * points + 12 * normals
        artwork = set()
        for _ in range(faces):
            count = struct.unpack_from("<I", data, offset)[0]
            corners = []
            for i in range(count):
                vertex, _, u, v = struct.unpack_from("<IIff", data, offset + 4 + 16 * i)
                x, z, y = struct.unpack_from("<3f", data, 40 + 16 * vertex)
                corners.append((x, y + origin[0], z + origin[1], u, v))
            key = offset + 72
            first = data.index(b"\0", key)
            second = data.index(b"\0", first + 1)
            texture = data[key:first]
            offset = second + 1
            if not texture.endswith(b"case_co.paa"):
                continue
            if not all(8 / 2048 < c[3] < 1008 / 2048 and 8 / 4096 < c[4] < 1608 / 4096 for c in corners):
                continue
            assert all(c[1] > .139 for c in corners)
            for x, _, z, u, v in corners:
                assert abs(u - (11 + ((.263-x)/.526)*994)/2048) < .001
                assert abs(v - (11 + ((.832-z)/.832)*1594)/4096) < .001
            artwork.add(tuple(tuple(round(value, 5) for value in corner) for corner in corners))
        return artwork

    assets = ROOT / "addons/acm_extended/data/medical_chest/hardigg"
    closed = outside_faces(assets / "medchest.p3d", (0, 0))
    detached = outside_faces(assets / "hardigg_lid.p3d", (.1175, .416))
    assert len(closed) > 30 and closed == detached
    assert not outside_faces(assets / "medchest_open.p3d", (0, 0))
