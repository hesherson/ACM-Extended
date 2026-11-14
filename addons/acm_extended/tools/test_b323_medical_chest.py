"""Run the production chest state machine with mocked Arma objects and 3D commands."""
import re
import struct

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read


def request_fixture():
    request = adapt(read("medicalChestRequest"))
    transition = adapt(read("medicalChestSetOpen"))
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
        ACME_fnc_medicalChestPlace = {_placed pushBack _this; [_this select 1, [0,1,0], [-1,0,0]]};
        ACME_fnc_medicalChestDrawers = {_drawers pushBack _this;};
        ACME_fnc_medicalChestDecals = {_markings pushBack (_this select [1, 2]); []};
        CBA_fnc_globalEvent = {_events pushBack _this;};
        CBA_fnc_targetEvent = {_gearRequests pushBack _this;};
    '''


def test_chest_reopen_retains_live_supply_container_and_ignores_stale_requests():
    execute(request_fixture() + '''
        [_chest, _medic, true, 0] call _request;
        private _open = _chest getVariable "ACME_medicalChestCabinet";
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [1,true] && {_hidden}, "closed shell did not yield to the drawers"] call _check;
        [count _created == 2 && {count _drawers == 1} && {count _placed == 2}, "missing lid or independently animated cabinet"] call _check;
        [_markings isEqualTo [["cabinet",10], ["lid",10]], "opening did not transfer the selected finish"] call _check;
        [(_placed select 0 select 1) isEqualTo [20.7, 12, 0] && {(_placed select 0 select 3) == "lid"} && {(_placed select 1 select 3) == "cabinet"}, "lid used the cabinet footprint or remained upright"] call _check;
        [_chest, _medic, true, 0] call _request;
        [count _created == 2, "concurrent open spawned extra visuals"] call _check;
        [(_open getVariable ["fixtureFrozen", false]) && {_drawers select 0 select 2}, "open cabinet was free to tip or needs simulation to set the drawers"] call _check;
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


def test_mission_start_open_and_later_close_share_the_same_cargo():
    execute(request_fixture() + r'''
        [_chest, true, 0, true] call ACME_fnc_medicalChestSetOpen;
        [count _created == 0, "remote caller entered the initialization path"] call _check;
        _remote = false;
        [_chest, true, 0, true] call ACME_fnc_medicalChestSetOpen;
        [(_chest getVariable "ACME_medicalChestState") isEqualTo [1,true], "initial lid state was closed"] call _check;
        [(_created select 0) isEqualTo "ACME_MedicalChest4Drawers", "initial drawer layout differs from Eden"] call _check;
        [(_drawers select 0 select 1) && {_audio isEqualTo []} && {_gearRequests isEqualTo []}, "initialization randomized the drawers or played audio"] call _check;
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
        ("_object modelToWorldWorld [0, 0, 0]", "_worldPosition"),
    ):
        assert engine in source
        source = source.replace(engine, fixture)
    return "private _place={" + source + "};"


@pytest.mark.parametrize("heading", [0, 90, 228])
@pytest.mark.parametrize("face_y", [True, False])
def test_cabinet_drawers_stack_vertically_with_the_same_front_as_closed(heading, face_y):
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
        private _paint = [_medic, [0,0,1], _heading, "cabinet", [0,0,1], _patient] call _place;
        _orient params ["_modelY", "_modelZ"];
        [(_orient select {1 if face_y else 0}) isEqualTo {"[0,0,-1]" if face_y else "[0,0,1]"} && {{(_orient select {0 if face_y else 1}) isEqualTo {"_closedY" if face_y else "_closedZ"}}}, "drawer bank did not put drawer 1 at the top facing the closed case heading"] call _check;
        [abs ((_worldPosition select 2) - 1.431) < 0.0001 && {{(_paint select 2) isEqualTo _closedZ}}, "cabinet lost ground contact or rotated its fitted shell"] call _check;
        _bounds = _closedBounds;
        [_medic, [0,0,1], _heading, "cabinet", [0,0,1], _patient] call _place;
        [(_orient select {0 if face_y else 1}) isEqualTo {"_closedY" if face_y else "_closedZ"}, "long-X cabinet did not inherit the closed case front"] call _check;
    ''')


@pytest.mark.parametrize("bounds,face_axis", [
    ("[[-.4145,-.0408,-.265],[.4151,.0413,.265]]", 0),
    ("[[-.4145,-.265,-.0408],[.4151,.265,.0413]]", 1),
])
@pytest.mark.parametrize("normal", ["[0,0,1]", "[0.3,0.2,0.9327]"])
def test_lid_resting_face_follows_the_support_in_both_model_layouts(bounds, face_axis, normal):
    execute(placement_fixture() + f'''
        private _closedBounds = [[-.423,-.170,-.266],[.421,.163,.266]];
        private _bounds = {bounds};
        private _orient = [];
        private _worldPosition = [];
        private _normal = vectorNormalized {normal};
        private _base = [20,12,1];
        private _paint = [_medic, _base, 73, "lid", _normal, _patient] call _place;
        private _modelNormal = _orient select {face_axis};
        [(_modelNormal vectorDotProduct _normal) < -.999 && {{((_paint select 1) vectorDotProduct _normal) < -.999}}, "lid or its finish remained on edge"] call _check;
        [abs (((_worldPosition vectorDiff _base) vectorDotProduct _normal) - .0493) < .0001, "lid failed to rest at the height of its painted face"] call _check;
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
    assert vehicles.count('class ACE_MainActions {') == 2
    assert 'class ACME_OpenMedicalChest' not in vehicles
    assert 'class ACME_CloseMedicalChest' not in vehicles
    assert 'Open Supplies' not in vehicles
    assert "[_target,_player,true] call ACME_fnc_medicalChestUse" in vehicles
    assert "[_target,_player,false] call ACME_fnc_medicalChestUse" in vehicles
    assert 'isEqualTo [_revision, true]' in runtime
    assert 'attachedTo _cargo isNotEqualTo objNull' in runtime
    assert '_actor action ["Gear", _this select 2]' in runtime


def test_live_catalog_routes_medical_items_and_charges_to_native_cargo():
    source = read("medicalChestStock")
    source = source.replace('_cargo addItemCargoGlobal [_x, 1]', '_itemsOut pushBack _x')
    source = source.replace('_cargo addMagazineCargoGlobal [_x, 1]', '_magazinesOut pushBack _x')
    source = source.replace('_cargo addBackpackCargoGlobal [_x, 1]', '_packsOut pushBack _x')
    source = source.replace('getNumber (configFile >> "CfgVehicles" >> _x >> "isBackpack") == 1', '_x == "MedicalBackpack"')
    execute('private _stock={' + source + '};' + r'''
        private _itemsOut = []; private _magazinesOut = []; private _packsOut = [];
        missionNamespace setVariable ["ACME_medicalChestCatalog",
            [["ACME_TempusLS_Item","ACME_IVStartKit_18g"],["ACM_OxygenTank_425"],["MedicalBackpack","HealthVehicle"]]];
        [_patient] call _stock;
        [_itemsOut isEqualTo ["ACME_TempusLS_Item","ACME_IVStartKit_18g"], "missing ordinary stock"] call _check;
        [_magazinesOut isEqualTo ["ACM_OxygenTank_425"], "charge-bearing supplies used the wrong cargo type"] call _check;
        [_packsOut isEqualTo ["MedicalBackpack"], "whole vehicles treated as backpacks"] call _check;
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
        for surface in ("closed", "cabinet", "lid"):
            model = (folder / f"chest_{number}_{surface}.p3d").read_bytes()
            assert model.startswith(b"MLOD") and texture.encode() + b"\0" in model
    for name in ("open", "close"):
        assert (addon / "sound" / f"medical_chest_{name}.ogg").read_bytes().startswith(b"OggS")



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
