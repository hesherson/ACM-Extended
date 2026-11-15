"""Run the production chest state machine with mocked Arma objects and 3D commands."""
import re
import struct

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read


def request_fixture():
    request = adapt(read("medicalChestRequest"))
    transition = adapt(read("medicalChestSetOpen"))
    motion = adapt(read("medicalChestOpenMotion"))
    for engine, stand_in in {
        "getPosWorld _lid": "(_lid getVariable 'fixturePosition')",
        "vectorDir _lid": "[0,0,1]",
        "vectorUp _lid": "[-1,0,0]",
        "vectorDir _chest": "[0,1,0]",
        "vectorUp _chest": "[-1,0,0]",
        "(0 boundingBoxReal _chest) select 1 select 1": "0.16",
        "(0 boundingBoxReal _lid) select 1 select 1": "0.04",
        "_chest modelToWorldWorld [0, _chestFront - _lidFront, 0]": "[20, 12 + _chestFront - _lidFront, 0.43]",
        "_x setVectorDirAndUp [_dir, _up];": "_x setVariable ['fixtureAxes', [_dir, _up]];",
        "_x setPosWorld _position;": "_x setVariable ['fixturePosition', _position];",
        "typeOf _cabinet": "'fixture cabinet'",
    }.items():
        assert engine in motion, engine
        motion = motion.replace(engine, stand_in)
    lid_base = adapt(read("medicalChestLidBase")).replace("0 boundingBoxReal _chest", "[[-.423,-.170,-.266],[.421,.163,.266]]")
    replacements = {
        'isRemoteExecuted': '_remote',
        'is3DEN': '_eden',
        'remoteExecutedOwner': '_sender',
        'alive _actor': '_alive',
        'owner _actor': '_ownerNum',
        '_chest isKindOf "ACME_MedicalChest"': '_chest getVariable ["fixtureChest", false]',
        '_actor distance _target': '_distance',
        'getNumber (configOf _chest >> "acmeChestVariant")': '_fixtureVariant',
        'createVehicle [_class, ASLToATL _base, [], 0, "CAN_COLLIDE"]': '([_class] call _spawn)',
        'createSimpleObject ["Land_PortableCabinet_01_lid_olive_F", _base]':
            '(["Land_PortableCabinet_01_lid_olive_F"] call _spawn)',
        '    _cabinet allowDamage false;': '',
        '    _cabinet enableSimulationGlobal false;': '    _cabinet setVariable ["fixtureFrozen", true];',
        '    _cargo attachTo [_cabinet, [0, 0, 0]];': '    _cargo setVariable ["fixtureAttached", _cabinet];',
        '    detach _cargo;': '    _cargo setVariable ["fixtureAttached", objNull];',
        '    _cargo setPosWorld (_base vectorAdd [0, 0, -25]);': '',
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
        "ACME_fnc_medicalChestOpenMotion = {" + motion + "};"
        "ACME_fnc_medicalChestLidBase = {" + lid_base + "};"
    )
    return definitions + r'''
        ACME_fnc_medicalChestGround = {[_this select 0, [0, 0, 1]]};
        private _chest = _patient;
        private _cargo = missionNamespace;
        private _created = [];
        private _deleted = [];
        private _audio = [];
        private _placed = [];
        private _gearRequests = [];
        private _drawers = [];
        private _plans = [];
        private _motion = [];
        private _removedMotion = [];
        private _fixtureLidPaint = currentNamespace;
        private _openedAt = CBA_missionTime;
        private _tickOpening = {
            private _remote = false;
            CBA_missionTime = _openedAt + _this;
            [_motion select 2, 30] call (_motion select 0);
        };
        private _markings = [];
        private _fixtureVariant = 10;
        private _hidden = false;
        private _failLid = false;
        private _remote = true;
        private _eden = false;
        private _sender = _ownerNum;
        private _spawn = {
            params ["_class"];
            _created pushBack _class;
            if (_class == "Land_PortableCabinet_01_lid_olive_F") exitWith {
                if (_failLid) then {objNull} else {parsingNamespace}
            };
            uiNamespace
        };
        _chest setVariable ["fixtureChest", true];
        _chest setVariable ["ACME_medicalChestPlacement", [[20, 12, 0], 0]];
        _chest setVariable ["ACME_medicalChestState", [0, false]];
        _chest setVariable ["ACME_medicalChestCargo", _cargo];
        _cargo setVariable ["stock", ["ACM_IV_18g", "ACM_ACCUVAC"]];
        ACME_fnc_medicalChestPlace = {
            _placed pushBack _this;
            if ((_this select 3) == "lid") then {
                (_this select 0) setVariable ["fixturePosition", [20.7, 12, 0.05]];
            };
        };
        ACME_fnc_medicalChestDrawerPlan = {_plans pushBack _this; [["drawer"], [0.63], true]};
        ACME_fnc_medicalChestDrawers = {_drawers pushBack _this;};
        ACME_fnc_medicalChestDecals = {
            _markings pushBack (_this select [1, 2]);
            if ((_this select 1) isEqualTo "lid") then {[_fixtureLidPaint]} else {[]}
        };
        CBA_fnc_addPerFrameHandler = {_motion = _this; 30};
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
        [_markings isEqualTo [["cabinet",10], ["lid",10]], "opening did not transfer the selected finish"] call _check;
        [(_placed select 0 select 1) isEqualTo [20.7, 12, 0] && {(_placed select 0 select 3) == "lid"} && {(_placed select 1 select 3) == "cabinet"}, "lid used the cabinet footprint or remained upright"] call _check;
        [_chest, _medic, true, 0] call _request;
        [count _created == 2, "concurrent open spawned extra visuals"] call _check;
        [(_open getVariable ["fixtureFrozen", false]) && {(_drawers select 0 select 2) == 0}, "cabinet was free to tip or drawers began open"] call _check;
        [_open, _medic, false, 1] call _request;
        [count _markings == 2 && {_gearRequests isEqualTo []}, "early close or Gear interrupted the animation"] call _check;
        0.59 call _tickOpening;
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [1,true] && {_hidden}, "opening did not publish the finished cabinet"] call _check;
        [_gearRequests isEqualTo [["ACME_medicalChestOpened", [_medic, _chest, _cargo, 1], _medic]], "open did not send exactly one Gear request to the initiating player"] call _check;
        _cargo setVariable ["stock", ["ACM_ACCUVAC", "ACE_tourniquet"]];
        [_open, _medic, false, 1] call _request;
        [_open, _medic, false, 1] call _request;
        [_markings isEqualTo [["cabinet",10], ["lid",10], ["closed",10]], "closing did not restore the selected finish"] call _check;
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [2,false] && {!_hidden}, "close left the chest open"] call _check;
        [_chest, _medic, true, 0] call _request;
        [count _created == 2, "old open replayed after the chest closed"] call _check;
        [_chest, _medic, true, 2] call _request;
        [(_chest getVariable "ACME_medicalChestCargo") isEqualTo _cargo && {(_cargo getVariable "stock") isEqualTo ["ACM_ACCUVAC", "ACE_tourniquet"]}, "using drawers refilled or discarded live cargo"] call _check;
        [_audio isEqualTo ["medical_chest_open", "medical_chest_close", "medical_chest_open"], "transition failed to emit exactly one matching sound"] call _check;
    ''')


def test_lid_and_paint_move_together_before_the_drawers_slide_and_gear_opens():
    execute(request_fixture() + r'''
        [_chest, _medic, true, 0] call _request;
        private _lid = _chest getVariable "ACME_medicalChestLid";
        private _start = _lid getVariable "fixturePosition";
        [abs ((_start select 1) - 12.12) < 0.001 && {(_lid getVariable "fixtureAxes") isEqualTo [[0,1,0],[-1,0,0]]},
            "the lid did not start in the closed chest's plane"] call _check;
        private _sample = {
            _this call _tickOpening;
            private _pos = _lid getVariable "fixturePosition";
            private _axes = _lid getVariable "fixtureAxes";
            [_pos isEqualTo (_fixtureLidPaint getVariable "fixturePosition") && {_axes isEqualTo (_fixtureLidPaint getVariable "fixtureAxes")},
                "paint drifted away from the lid"] call _check;
            [_pos, _axes]
        };
        (0.10 call _sample) params ["_lift", "_liftAxes"];
        [(_lift select 1) > (_start select 1) && {(_lift select 2) > (_start select 2)} && {_liftAxes isEqualTo [[0,1,0],[-1,0,0]]},
            "lid did not lift clear of the case before rotating"] call _check;
        (0.23 call _sample) params ["_swing", "_swingAxes"];
        [(_swing select 0) > (_start select 0) && {(_swingAxes select 0 select 2) > 0} && {count _drawers == 1}
            && {_gearRequests isEqualTo []}, "lid failed to swing clear before the drawers and Gear"] call _check;
        (0.44 call _sample) params ["_settle", "_settleAxes"];
        private _drawerFraction = _drawers select 1 select 2;
        [(_settle select 2) < (_swing select 2) && {_settleAxes isEqualTo [[0,0,1],[-1,0,0]]}
            && {_drawerFraction > 0 && {_drawerFraction < 1}} && {_gearRequests isEqualTo []},
            "drawers did not slide while the painted lid settled or Gear opened early"] call _check;
        (0.57 call _sample) params ["_end", "_endAxes"];
        [_end isEqualTo [20.7,12,0.05] && {_endAxes isEqualTo [[0,0,1],[-1,0,0]]}
            && {(_drawers select 2 select 2) == 1} && {count _gearRequests == 1} && {_removedMotion isEqualTo [30]},
            "opening failed to complete at the exact resting pose and expose Gear"] call _check;
    ''')


def test_missing_lid_cancels_the_motion_and_allows_a_fresh_open():
    execute(request_fixture() + r'''
        [_chest, _medic, true, 0] call _request;
        (_motion select 2) set [2, objNull];
        _chest setVariable ["ACME_medicalChestLid", objNull];
        0.15 call _tickOpening;
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [1,false] && {!_hidden}
            && {_gearRequests isEqualTo []} && {_removedMotion isEqualTo [30]},
            "interrupted opening did not restore the closed shell"] call _check;
        _openedAt = CBA_missionTime;
        [_chest, _medic, true, 1] call _request;
        0.59 call _tickOpening;
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
        [(_created select 0) isEqualTo "ACME_MedicalChest4Drawers", "initial drawer layout differs from Eden"] call _check;
        [(_plans select 0 select 1) && {(_drawers select 0 select 2) == 1} && {_motion isEqualTo []}
            && {_audio isEqualTo []} && {_gearRequests isEqualTo []}, "initialization animated the drawers or played audio"] call _check;
        [(_cargo getVariable "fixtureAttached") isEqualTo (_chest getVariable "ACME_medicalChestCabinet"), "open chest did not expose the live cargo"] call _check;
        private _open = _chest getVariable "ACME_medicalChestCabinet";
        [_open, _medic, false, 1] call _request;
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
    assert 'call ACME_fnc_medicalChestDecals' in eden
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
        ("0 boundingBoxReal _closed", "_closedBounds"),
        ("_object setVectorDirAndUp [_dir, _up];", "_orient = [_dir, _up];"),
        ("_object setPosWorld", "_worldPosition ="),
    ):
        assert engine in source
        source = source.replace(engine, fixture)
    return "private _place={" + source + "};"


@pytest.mark.parametrize("heading", [0, 90, 228])
@pytest.mark.parametrize("face_y", [True, False])
def test_cabinet_is_right_side_up_with_the_same_bearing_as_the_previous_open_pose(heading, face_y):
    closed = "[[-.423,-.170,-.266],[.421,.163,.266]]" if face_y else "[[-.423,-.266,-.170],[.421,.266,.163]]"
    cabinet = "[[-.266,-.170,-.421],[.266,.09,.423]]" if face_y else "[[-.266,-.423,-.170],[.266,.421,.09]]"
    execute(placement_fixture() + f'''
        private _heading = {heading};
        private _closedBounds = {closed};
        private _bounds = _closedBounds;
        private _orient = [];
        private _worldPosition = [];
        [_medic, [0,0,1], _heading, "closed"] call _place;
        _orient params ["_closedY", "_closedZ"];
        [((_closedY vectorCrossProduct _closedZ) select 2) > .999, "closed case no longer stands on the wheel end"] call _check;
        _bounds = {cabinet};
        [_medic, [0,0,1], _heading, "cabinet", [0,0,1], _patient] call _place;
        _orient params ["_modelY", "_modelZ"];
        private _oldFront = {"_closedY" if face_y else "_closedZ"};
        [(_orient select {1 if face_y else 0}) isEqualTo {"[0,0,1]" if face_y else "[0,0,-1]"}, "cabinet still stacks the drawers upside down"] call _check;
        [((_orient select {0 if face_y else 1}) vectorDotProduct _oldFront) < -.999, "uprighting the drawers changed their bearing"] call _check;
        [abs ((_worldPosition select 2) - 1.429) < 0.0001, "cabinet used the upside-down support edge"] call _check;
        _bounds = _closedBounds;
        [_medic, [0,0,1], _heading, "cabinet", [0,0,1], _patient] call _place;
        [((_orient select {0 if face_y else 1}) vectorDotProduct _oldFront) < -.999 && {{(((_orient select 0) vectorCrossProduct (_orient select 1)) select 2) < -.999}}, "long-X cabinet was not flipped around its drawer face"] call _check;
        [abs ((_worldPosition select 2) - 1.429) < .0001, "long-X cabinet used the wrong support edge"] call _check;
    ''')


@pytest.mark.parametrize("bounds,face_axis", [
    ("[[-.4145,-.0408,-.265],[.4151,.0413,.265]]", 0),
    ("[[-.4145,-.265,-.0408],[.4151,.265,.0413]]", 1),
])
@pytest.mark.parametrize("normal", ["[0,0,1]", "[0.3,0.2,0.9327]"])
def test_lid_paint_faces_up_and_the_inner_face_follows_the_support(bounds, face_axis, normal):
    execute(placement_fixture() + f'''
        private _closedBounds = [[-.423,-.170,-.266],[.421,.163,.266]];
        private _bounds = {bounds};
        private _orient = [];
        private _worldPosition = [];
        private _normal = vectorNormalized {normal};
        private _base = [20,12,1];
        [_medic, _base, 73, "lid", _normal, _patient] call _place;
        private _modelNormal = _orient select {face_axis};
        [(_modelNormal vectorDotProduct _normal) > .999, "lid failed to show the painted face"] call _check;
        [abs (((_worldPosition vectorDiff _base) vectorDotProduct _normal) - .0488) < .0001, "lid failed to rest at the height of its inner face"] call _check;
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


def test_chest_ace_actions_are_direct_and_gear_waits_for_matching_open_state():
    vehicles = (ROOT / "addons/acm_extended/MedicalChestVehicles.hpp").read_text()
    runtime = read("registerMedicalChestRuntime")
    assert vehicles.count('class ACE_MainActions {') == 3
    assert 'class ACE_Actions {class ACE_MainActions {condition = "false";};};' in vehicles
    assert 'class ACME_OpenMedicalChest' not in vehicles
    assert 'class ACME_CloseMedicalChest' not in vehicles
    assert 'Open Supplies' not in vehicles
    assert "[_target,_player,true] call ACME_fnc_medicalChestUse" in vehicles
    assert "[_target,_player,false] call ACME_fnc_medicalChestUse" in vehicles
    assert "[_target,_player,true] call ACME_fnc_medicalChestCanUse" in vehicles
    assert "[_target,_player,false] call ACME_fnc_medicalChestCanUse" in vehicles
    assert 'isEqualTo [_revision, true]' in runtime
    assert 'attachedTo _cargo isNotEqualTo objNull' in runtime
    assert '_actor action ["Gear", _this select 2]' in runtime


def test_overlapping_chests_offer_only_the_pointed_active_case_action():
    source = read("medicalChestCanUse")
    for engine, fixture in (
        ('isObjectHidden _target', '(_target getVariable ["hidden",false])'),
        ('isObjectHidden _aim', '(_aim getVariable ["hidden",false])'),
        ('cursorObject', '_aimObject'), ('_actor distance _aim', '1'),
        ('_aim isKindOf "ACME_MedicalChest"', '(_aim getVariable ["closedClass",false])'),
    ):
        assert engine in source
        source = source.replace(engine, fixture)
    execute('private _canUse={' + adapt(source) + '};' + r'''
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
    assert 'class ACME_MedicalChest: Land_PortableCabinet_01_closed_olive_F' in vehicles
    assert 'ACME_MedicalChest4Drawers,Land_PortableCabinet_01_4drawers_olive_F' in vehicles
    assert 'ACME_MedicalChest7Drawers,Land_PortableCabinet_01_7drawers_olive_F' in vehicles
    for asset in ("chest_title", "chest_serial", "chest_cross", "chest_tape_lid", "chest_tape_side", "chest_tape_back"):
        assert (addon / "data/medical_chest" / f"{asset}.p3d").read_bytes().startswith(b"MLOD")
        assert (addon / "data/medical_chest" / f"{asset}_ca.paa").is_file()
    for number in range(1, 11):
        name = f"ACME_MedicalChest_{number:02d}"
        assert f'"{name}"' in config
        assert f"ACME_MEDICAL_CHEST_RETEXTURE({name},{number}," in vehicles
        folder = addon / "data/medical_chest/variants"
        texture = f"acm_extended\\data\\medical_chest\\variants\\chest_{number}_ca.paa"
        assert (folder / f"chest_{number}_ca.paa").is_file()
        for surface in ("closed", "cabinet4", "cabinet7", "lid"):
            model = (folder / f"chest_{number}_{surface}.p3d").read_bytes()
            assert model.startswith(b"MLOD") and texture.encode() + b"\0" in model
    for name in ("open", "close"):
        assert (addon / "sound" / f"medical_chest_{name}.ogg").read_bytes().startswith(b"OggS")


def test_open_finishes_use_the_native_part_transform():
    source = read("medicalChestDecals")
    for engine, fixture in (
        ('typeOf _object', '_partClass'),
        ('_object modelToWorldWorld _modelPos', '([_modelPos] call _partPoint)'),
        ('_object vectorModelToWorld _modelDir', '([_modelDir] call _partVector)'),
        ('_object vectorModelToWorld _modelUp', '([_modelUp] call _partVector)'),
        ('createSimpleObject [format ["\\acm_extended\\data\\medical_chest\\%1.p3d", _asset], _position, _localOnly]',
         '([_asset, _position, _localOnly] call _spawn)'),
        ('_decal setVectorDirAndUp', '_axis ='), ('_decal setPosWorld', '_at ='),
    ):
        assert engine in source
        source = source.replace(engine, fixture)
    execute('private _finish={' + adapt(source) + '};' + r'''
        private _partClass="ACME_MedicalChest7Drawers";
        private _parts=[]; private _axis=[]; private _at=[];
        private _partPoint={params ["_p"]; [11,12,13] vectorAdd _p};
        private _partVector={params ["_v"]; [_v select 0,-(_v select 2),_v select 1]};
        private _spawn={_parts pushBack _this; _patient};
        [_medic,"cabinet",8] call _finish;
        [_parts isEqualTo [["variants\chest_8_cabinet7",[11,12,13],false]], "seven drawers borrowed another shell's finish"] call _check;
        [_axis isEqualTo [[0,0,1],[0,-1,0]] && {_at isEqualTo [11,12,13]}, "paint did not inherit the exact model frame"] call _check;
        _parts=[];
        [_medic,"lid",0,true] call _finish;
        [_parts isEqualTo [["variants\chest_0_lid",[11,12,13],true]], "generic lid still has separate floating paint objects"] call _check;
    ''')


def test_cabinet_paint_meshes_stay_behind_the_drawer_openings():
    folder = ROOT / "addons/acm_extended/data/medical_chest/variants"
    for number in range(11):
        models = []
        for layout in (4, 7):
            model = (folder / f"chest_{number}_cabinet{layout}.p3d").read_bytes()
            points = struct.unpack_from("<I", model, 24)[0]
            positions = [struct.unpack_from("<3f", model, 40 + 16 * i) for i in range(points)]
            assert min(z for _, _, z in positions) > -.005
            assert max(z for _, _, z in positions) > .20
            assert min(y for _, y, _ in positions) < -.40
            assert max(y for _, y, _ in positions) > .40
            models.append(positions)
        assert models[0] != models[1]
    generic_lid = (folder / "chest_0_lid.p3d").read_bytes()
    assert b"chest_0_open_ca.paa\0" in generic_lid
    assert b"chest_0_ca.paa\0" in (folder / "chest_0_closed.p3d").read_bytes()



def test_fitted_lid_uvs_increase_toward_the_viewers_right_in_arma():
    folder = ROOT / "addons/acm_extended/data/medical_chest/variants"
    for model in sorted([*folder.glob("*_closed.p3d"), *folder.glob("*_lid.p3d")]):
        data = model.read_bytes()
        _, _, points, normals, faces, _ = struct.unpack_from("<6I", data, 16)
        offset = 40 + 16 * points + 12 * normals
        checked = 0
        for _ in range(faces):
            corners = []
            for i in range(3):
                vertex, _, u, v = struct.unpack_from("<IIff", data, offset + 4 + 16 * i)
                x, _, z = struct.unpack_from("<3f", data, 40 + 16 * vertex)
                corners.append((x, z, u, v))
            offset = data.index(b"\0\0", offset + 72) + 2
            # The first atlas row contains the front and rear projections.
            if max(corner[3] for corner in corners) >= 1609 / 4096:
                continue
            if max(corner[2] for corner in corners) >= 1010 / 2048:
                continue
            left, *_, right = sorted(corners, key=lambda corner: -corner[1])
            if left[1] - right[1] > .001:
                assert left[2] < right[2], model
                checked += 1
            low, *_, high = sorted(corners, key=lambda corner: corner[0])
            if high[0] - low[0] > .001:
                assert low[3] > high[3], model
        assert checked > 30, model
