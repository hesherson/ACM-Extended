"""Execute production cold-chain math, cargo reconciliation and loose exposure.

Only native config, inventory, holder enumeration, clocks and network delivery
are stand-ins. Production state transitions and the complete aging callbacks run.
"""
import re

import pytest

from test_menu_death_lifecycle import adapt, execute, read
from test_historical_vial_execution import map_defaults


def source(name):
    raw = read(name).replace('serverTime', '_clock').replace('diag_frameNo', '_frame')
    # SQF-VM lacks finite/getOrDefault. Supply those native primitives while
    # retaining the production validation branches and actual map contents.
    raw = re.sub(r'\bfinite (_\w+)', r'(\1 call _finite)', raw)
    raw = raw.replace('finite (_x # 1)', '((_x # 1) call _finite)')
    # The VM's sort leaves nested rows unchanged. Native Arma compares the
    # scalar/string fields of subarrays lexicographically (BIS wiki: sort).
    # These production rows have a numeric primary key; the shim supplies that
    # native ordering without changing any caller's selection logic.
    raw = re.sub(r'(_\w+) sort (true|false);', r'[\1,\2] call _nativeSort;', raw)
    raw = re.sub(r'getNumber \(configFile >> "CfgWeapons" >> (_\w+) >> "(\w+)"\)',
                 r'([\1,"\2"] call _config)', raw)
    raw = raw.replace('itemCargo _box', '(_box getVariable ["fixtureCargo",[]])')
    raw = raw.replace('typeOf _box', '(_box getVariable ["fixtureType",""])')
    raw = raw.replace('allUnits', '_units').replace('allDeadMen', '_dead').replace('vehicles', '_vehicles')
    raw = raw.replace('allPlayers', '[]')
    raw = re.sub(r'allMissionObjects "([^"]+)"',
                 r'(_boxes select {(_x getVariable ["fixtureType",""])=="\1"})', raw)
    raw = re.sub(r'(_\w+) isKindOf "([^"]+)"',
                 r'([\1,"\2"] call _kind)', raw)
    raw = re.sub(r'netId (_\w+)', r'(\1 getVariable ["fixtureId","holder"])', raw)
    raw = re.sub(r'owner (_\w+)', r'(\1 getVariable ["fixtureOwner",7])', raw)
    raw = raw.replace('isNull (objectFromNetId _x)', '((_byId getOrDefault [_x,objNull]) isEqualTo objNull)')
    raw = re.sub(r'\buniformItems (_h|_holder)\b', r'(\1 getVariable ["fixtureCargo",[]])', raw)
    raw = re.sub(r'\b(?:vestItems|backpackItems) (_h|_holder)\b', '[]', raw)
    raw = raw.replace('getItemCargo _h', '([_h] call _cargoCounts)')
    raw = raw.replace('_box addItemCargoGlobal [_x, -1];', '[_box,_x,-1] call _cargoAdjust;')
    raw = raw.replace('_box addItemCargoGlobal ["ACME_SpoiledBlood", count _spoiled];',
                      '[_box,"ACME_SpoiledBlood",count _spoiled] call _cargoAdjust;')
    raw = raw.replace('_h addItemCargoGlobal [_bc, _n];', '[_h,_bc,_n] call _cargoAdjust;')
    raw = raw.replace('_h addItemCargoGlobal [_x, -1];', '[_h,_x,-1] call _cargoAdjust;')
    raw = raw.replace('_h addItemCargoGlobal ["ACME_SpoiledBlood", 1];',
                      '[_h,"ACME_SpoiledBlood",1] call _cargoAdjust;')
    raw = raw.replace('[_h, [], _add] remoteExec ["ACME_fnc_ccApply", _h]', '[_h,[],_add] call _apply')
    raw = raw.replace('[_h, _spoil, _add] remoteExec ["ACME_fnc_ccApply", _h]', '[_h,_spoil,_add] call _apply')
    raw = raw.replace('_box setVariable ["ACME_boxCoolerState", _advanced, _publish];',
                      '_box setVariable ["ACME_boxCoolerState",_advanced];if (_publish) then {_boxPublic pushBack "state";};')
    raw = raw.replace('_box setVariable ["ACME_boxCoolerClass", _base, true];',
                      '_box setVariable ["ACME_boxCoolerClass",_base];_boxPublic pushBack "class";')
    raw = raw.replace('_box setVariable ["ACME_boxCoolantStart", _advanced # 1, true];',
                      '_box setVariable ["ACME_boxCoolantStart",_advanced # 1];_boxPublic pushBack "start";')
    return adapt(map_defaults(raw))


def fixture():
    code = r'''
        private _clock=0;
        private _frame=0;
        private _boxPublic=[];
        private _nextFrames=[];
        private _box=profileNamespace;
        private _holder=uiNamespace;
        private _units=[]; private _dead=[]; private _vehicles=[]; private _boxes=[];
        private _byId=createHashMapFromArray [["box",_box],["holder",_holder]];
        private _class="ACME_BloodCooler_CSWB1U";
        private _bag="ACM_BloodBag_ON_500";
        private _fresh="ACM_FreshBloodBag_250_7";
        private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in keys _map) then {_map get _key} else {_default}};
        private _nativeSort={params ["_array","_ascending"];
            private _left=+_array; private _ordered=[];
            while {!(_left isEqualTo [])} do {
                private _best=0;
                {
                    private _a=if (_x isEqualType []) then {_x # 0} else {_x};
                    private _current=_left # _best;
                    private _b=if (_current isEqualType []) then {_current # 0} else {_current};
                    if ((_ascending && {_a<_b}) || {!_ascending && {_a>_b}}) then {_best=_forEachIndex;};
                } forEach _left;
                _ordered pushBack (_left deleteAt _best);
            };
            {_array set [_forEachIndex,_x];} forEach _ordered;
        };
        private _config={params ["_base","_field"];
            if (_field=="ACME_coolerColdChainTime") then {
                if (_base=="stable") then {0} else {100}
            } else {500}
        };
        private _kind={params ["_object","_type"];
            if (_type=="CAManBase") then {_object getVariable ["fixtureMan",false]}
            else {(_object getVariable ["fixtureType",""])==_type}
        };
        private _cargoAdjust={params ["_object","_item","_amount"];
            private _cargo=+(_object getVariable ["fixtureCargo",[]]);
            if (_amount<0) then {
                for "_i" from 1 to (-_amount) do {
                    private _at=_cargo find _item;
                    if (_at>=0) then {_cargo deleteAt _at;};
                };
            } else {for "_i" from 1 to _amount do {_cargo pushBack _item;};};
            _object setVariable ["fixtureCargo",_cargo];
        };
        private _cargoCounts={params ["_object"];
            private _counts=createHashMap;
            {_counts set [_x,1+(_counts getOrDefault [_x,0])];} forEach (_object getVariable ["fixtureCargo",[]]);
            private _classes=keys _counts;
            [_classes,_classes apply {_counts get _x}]
        };
        private _apply={params ["_object","_remove","_add"];
            {[_object,_x,-1] call _cargoAdjust;} forEach _remove;
            {[_object,_x,1] call _cargoAdjust;} forEach _add;
        };
        missionNamespace setVariable ["ACME_sys_bloodChain",true];
        missionNamespace setVariable ["ACME_bloodSpoilEnabled",true];
        missionNamespace setVariable ["ACME_bloodLooseSpoilTime",1800];
        missionNamespace setVariable ["ACME_coolerThawRateInside",0.2];
        missionNamespace setVariable ["ACME_bloodFloatTTL",180];
        missionNamespace setVariable ["ACME_ccByHolder",createHashMap];
        missionNamespace setVariable ["ACME_ccBagFloat",createHashMap];
        missionNamespace setVariable ["ACME_ccCoolFloat",createHashMap];
        missionNamespace setVariable ["ACME_ccBrokerFrame",-1];
        missionNamespace setVariable ["ACME_ccBoxAdmissionFrame",-1];
        missionNamespace setVariable ["ACME_coolerAutoCover",false];
        missionNamespace setVariable ["ACME_coolerAutoFill",false];
        _box setVariable ["fixtureType","ACME_BloodCoolerBox_CSWB1U"];
        _box setVariable ["fixtureId","box"];
        _box setVariable ["fixtureCargo",[]];
        _box setVariable ["ACME_boxCoolerState",[]];
        _box setVariable ["ACME_boxCoolerClass",""];
        _box setVariable ["ACME_coolerPacking",false];
        _box setVariable ["ACME_coolerRetired",false];
        _holder setVariable ["fixtureType","CAManBase"];
        _holder setVariable ["fixtureMan",true];
        _holder setVariable ["fixtureId","holder"];
        _holder setVariable ["fixtureOwner",7];
        _holder setVariable ["fixtureCargo",[]];
        _holder setVariable ["ACME_bloodExposureSeedTokens",createHashMap];
        _holder setVariable ["ACME_bloodExposurePending",[]];
        _holder setVariable ["ACME_bloodSeedPending",createHashMap];
        _holder setVariable ["ACME_bloodExposureDeferred",[]];
        CBA_fnc_targetEvent={_events pushBack _this;};
        CBA_fnc_execNextFrame={_nextFrames pushBack +_this;};
    '''
    for name in ['coolerBagVolume', 'coolerAdvance', 'coolerBoxReconcile',
                 'coolerBoxColdChainTick', 'bloodColdChainTick', 'bloodExposureBroker']:
        code += f'ACME_fnc_{name}={{' + source(name) + '};'
    return map_defaults(code)


@pytest.mark.parametrize('bag,ml', [
    ('ACM_BloodBag_ON_1000', 1000), ('ACM_BloodBag_AB_500', 500),
    pytest.param('ACM_FreshBloodBag_250_7', 250, id='ACM_FreshBloodBag_A_250-250'), ('ACME_SpoiledBlood', 0),
    ('ACM_BloodBag_ON_500_bad', 0), ('SalineIV_1000', 0),
])
def test_bag_volume_uses_supported_terminal_size(bag, ml):
    execute(fixture()+f'[["{bag}"] call ACME_fnc_coolerBagVolume=={ml},"bad bag volume"] call _check;')


@pytest.mark.parametrize('last,now,expected', [
    (0, 99, 0), (99, 100, 0), (99, 105, 1), (105, 115, 2), (105, 105, 0), (105, 90, 0),
])
def test_advance_only_counts_post_expiry_elapsed(last, now, expected):
    execute(fixture()+f'''
        private _initial=[_class,0,[[_bag,17]],{last}];
        private _state=[_initial,{now}] call ACME_fnc_coolerAdvance;
        [abs ((((_state # 2) # 0) # 1)-({17+expected}))<0.001,"wrong exposure"] call _check;
        [((_initial # 2) # 0) # 1==17,"advance mutated input"] call _check;
        ((_state # 2) # 0) set [1,900];
        [((_initial # 2) # 0) # 1==17,"returned entries alias source"] call _check;
    ''')


def test_delayed_tick_equals_many_short_ticks_and_stable_coolant_never_ages():
    execute(fixture()+r'''
        private _initial=[_class,0,[[_bag,13],[_fresh,9]],90];
        private _long=[_initial,1000] call ACME_fnc_coolerAdvance;
        private _short=_initial;
        for "_t" from 95 to 1000 step 5 do {_short=[_short,_t] call ACME_fnc_coolerAdvance;};
        [_long isEqualTo _short,"callback cadence changes expiry"] call _check;
        private _stable=[["stable",0,[[_bag,13]],0],10000] call ACME_fnc_coolerAdvance;
        [((_stable # 2) # 0) # 1==13,"stable coolant aged blood"] call _check;
    ''')


def test_editor_box_is_stamped_once_and_late_admission_has_its_own_exposure():
    execute(fixture()+r'''
        _box setVariable ["fixtureCargo",[_bag]];
        private _first=[_box,0] call ACME_fnc_coolerBoxReconcile;
        private _aged=[_box,200] call ACME_fnc_coolerBoxReconcile;
        [_aged # 1==0 && {((_aged # 2) # 0) # 1==20},"editor start refreshed"] call _check;
        _box setVariable ["fixtureCargo",[_bag,_fresh]];
        private _added=[_box,210] call ACME_fnc_coolerBoxReconcile;
        private _ages=(_added # 2) apply {[_x # 0,_x # 1]};
        [[_bag,22] in _ages && {[_fresh,0] in _ages},"new bag inherited old box exposure"] call _check;
        private _later=[_box,220] call ACME_fnc_coolerBoxReconcile;
        [[_fresh,2] in (_later # 2),"new bag did not age from admission"] call _check;
    ''')


def test_same_class_removal_keeps_oldest_and_transfer_pool_retains_elapsed_age():
    execute(fixture()+r'''
        _box setVariable ["ACME_boxCoolerState",[_class,0,[[_bag,900],[_bag,100]],200]];
        _box setVariable ["fixtureCargo",[_bag]];
        private _state=[_box,200] call ACME_fnc_coolerBoxReconcile;
        [(_state # 2) isEqualTo [[_bag,900]],"kept younger ambiguous bag"] call _check;
        _box setVariable ["fixtureCargo",[_bag,_bag]];
        private _later=[_box,210] call ACME_fnc_coolerBoxReconcile;
        [[_bag,110] in (_later # 2),"transfer pool reset warmth or ignored elapsed time"] call _check;
    ''')


def test_box_tick_spoils_individual_bags_and_preserves_other_cargo():
    execute(fixture()+r'''
        _box setVariable ["ACME_boxCoolerState",[_class,0,[[_bag,1799],[_fresh,0]],200]];
        _box setVariable ["fixtureCargo",[_bag,_fresh,"bandage","ACME_SpoiledBlood"]];
        _boxes=[_box];_clock=205;
        call ACME_fnc_coolerBoxColdChainTick;
        private _cargo=_box getVariable "fixtureCargo";
        [!(_bag in _cargo) && {_fresh in _cargo} && {"bandage" in _cargo},"wrong cargo spoiled or lost"] call _check;
        [({_x=="ACME_SpoiledBlood"} count _cargo)==2,"spoiled count changed"] call _check;
        [((_box getVariable "ACME_boxCoolerState") # 2) isEqualTo [[_fresh,1]],"spoiled ledger survives"] call _check;
    ''')


@pytest.mark.parametrize('flag', ['ACME_coolerPacking', 'ACME_coolerRetired'])
def test_box_tick_does_not_mutate_a_locked_or_retired_box(flag):
    execute(fixture()+f'''
        private _state=[_class,0,[[_bag,1799]],200];
        _box setVariable ["ACME_boxCoolerState",_state];
        _box setVariable ["fixtureCargo",[_bag]];
        _box setVariable ["{flag}",true];
        _boxes=[_box];_clock=10000;
        call ACME_fnc_coolerBoxColdChainTick;
        [(_box getVariable "fixtureCargo") isEqualTo [_bag],"locked box cargo mutated"] call _check;
        [(_box getVariable "ACME_boxCoolerState") isEqualTo _state,"locked box state mutated"] call _check;
    ''')


def test_generic_loose_age_catches_up_once_includes_corpses_and_excludes_cooler_boxes():
    execute(fixture()+r'''
        _holder setVariable ["fixtureCargo",[_bag]];
        _box setVariable ["fixtureCargo",[_bag]];
        _dead=[_holder];_vehicles=[_box];
        [0] call ACME_fnc_bloodColdChainTick;
        _clock=200;[0] call ACME_fnc_bloodColdChainTick;
        private _exposure=_holder getVariable "ACME_bloodExposure";
        [((_exposure # 0) # 0) # 2==200,"dead holder did not age by elapsed time"] call _check;
        [0] call ACME_fnc_bloodColdChainTick;
        [((_holder getVariable "ACME_bloodExposure") # 0) isEqualTo (_exposure # 0),"same-time nudge aged twice"] call _check;
        [!("box" in keys (missionNamespace getVariable "ACME_ccByHolder")),"generic tick ages deployed cooler"] call _check;
        _clock=1800;call ACME_fnc_bloodColdChainTick;
        [(_holder getVariable "fixtureCargo") isEqualTo ["ACME_SpoiledBlood"],"elapsed loose expiry failed"] call _check;
        [(_box getVariable "fixtureCargo") isEqualTo [_bag],"box blood was spoiled as loose"] call _check;
    ''')


def test_loose_handoff_preserves_exposure_and_ages_time_between_observations():
    execute(fixture()+r'''
        _holder setVariable ["fixtureCargo",[_bag]];_units=[_holder];
        call ACME_fnc_bloodColdChainTick;
        _clock=50;_holder setVariable ["fixtureCargo",[]];call ACME_fnc_bloodColdChainTick;
        _clock=80;_holder setVariable ["fixtureCargo",[_bag]];call ACME_fnc_bloodColdChainTick;
        [(((_holder getVariable "ACME_bloodExposure") # 0) # 0) # 2==80,"handoff refreshed blood"] call _check;
    ''')


def test_exposure_broker_read_seed_replay_and_wrong_owner():
    execute(fixture()+r'''
        _holder setVariable ["fixtureCargo",[_bag]];_units=[_holder];
        ["read",_holder,_bag,[7,1]] call ACME_fnc_bloodExposureBroker;
        [((_events # 0) # 1) # 3==0,"read did not synchronize new blood"] call _check;
        _frame=1;
        ["seed",_holder,_bag,[7,2],600,0] call ACME_fnc_bloodExposureBroker;
        [(((_holder getVariable "ACME_bloodExposure") # 0) # 0) # 2==600,"seed lost prior exposure"] call _check;
        _clock=10;_frame=2;["seed",_holder,_bag,[7,2],999,0] call ACME_fnc_bloodExposureBroker;
        [(((_holder getVariable "ACME_bloodExposure") # 0) # 0) # 2==600,"repeated seed changed later bag"] call _check;
        private _count=count _events;
        ["seed",_holder,_bag,[8,3],1200,10] call ACME_fnc_bloodExposureBroker;
        [count _events==_count,"wrong owner request accepted"] call _check;
    ''')


def test_seed_waits_for_native_replication_and_targets_youngest_new_row():
    execute(fixture()+r'''
        _holder setVariable ["fixtureCargo",[_bag]];_units=[_holder];
        call ACME_fnc_bloodColdChainTick;
        private _store=missionNamespace getVariable "ACME_ccByHolder";
        _store set ["holder",[[[_bag,500,1000,0]],[]]];
        missionNamespace setVariable ["ACME_ccByHolder",_store];
        ["seed",_holder,_bag,[7,1],500,0,2] call ACME_fnc_bloodExposureBroker;
        [count (_holder getVariable "ACME_bloodExposurePending")==1,"seed lost before replication"] call _check;
        [((_events # ((count _events)-1)) # 1) # 3==-1,"missing native placement acknowledged"] call _check;
        _holder setVariable ["fixtureCargo",[_bag,_bag]];_clock=10;_frame=1;
        ["seed",_holder,_bag,[7,1],500,0,2] call ACME_fnc_bloodExposureBroker;
        private _ages=((_holder getVariable "ACME_bloodExposure") # 0) apply {_x # 2};
        [1010 in _ages && {510 in _ages},"seed refreshed new bag or changed older bag"] call _check;
        [(_holder getVariable "ACME_bloodExposurePending") isEqualTo [],"applied seed remains pending"] call _check;
    ''')


def test_seed_survives_owner_change_only_with_exact_published_funding_claim():
    execute(fixture()+r'''
        _holder setVariable ["fixtureCargo",[_bag]];_units=[_holder];
        _holder setVariable ["fixtureOwner",8];
        ["seed",_holder,_bag,[7,1],500,0,1] call ACME_fnc_bloodExposureBroker;
        [count _events==0,"unfunded old-machine seed accepted"] call _check;
        _holder setVariable ["ACME_bloodSeedPending",createHashMapFromArray [["old",[_bag,[7,1],500,0,0,1]]]];
        ["seed",_holder,_bag,[7,1],500,0,1] call ACME_fnc_bloodExposureBroker;
        [(((_holder getVariable "ACME_bloodExposure") # 0) # 0) # 2==500,"funded seed lost after owner migration"] call _check;
    ''')


def test_native_box_take_read_reconciles_source_before_the_receiver_scan():
    execute(fixture()+r'''
        _box setVariable ["ACME_boxCoolerState",[_class,-100,[[_bag,700]],0]];
        _box setVariable ["fixtureCargo",[]];
        _holder setVariable ["fixtureCargo",[_bag]];
        _boxes=[_box];_units=[_holder];_clock=10;
        ["read",_holder,_bag,[7,1]] call ACME_fnc_bloodExposureBroker;
        [((_events # ((count _events)-1)) # 1) # 3==702,"native box take reset warm exposure"] call _check;
        [((_box getVariable "ACME_boxCoolerState") # 2) isEqualTo [],"source retained released bag"] call _check;
    ''')


def test_idle_box_does_not_republish_its_sample_clock():
    execute(fixture()+r'''
        _box setVariable ["fixtureCargo",[_bag]];
        [_box,0] call ACME_fnc_coolerBoxReconcile;
        private _initial=count _boxPublic;
        for "_t" from 5 to 50 step 5 do {[_box,_t] call ACME_fnc_coolerBoxReconcile;};
        [count _boxPublic==_initial,"cold box rebroadcast idle sample clock"] call _check;
        [_box,200] call ACME_fnc_coolerBoxReconcile;
        [count _boxPublic==_initial,"derivable exposure rebroadcast unchanged contents"] call _check;
        [(((_box getVariable "ACME_boxCoolerState") # 2) # 0) # 1==20,"private clock stopped advancing"] call _check;
        _box setVariable ["fixtureCargo",[_bag,_fresh]];
        [_box,210] call ACME_fnc_coolerBoxReconcile;
        [count _boxPublic==_initial+1,"cargo change did not publish a new baseline"] call _check;
    ''')


def test_multiple_pending_seed_records_bind_distinct_physical_rows():
    execute(fixture()+r'''
        _units=[_holder];
        ["seed",_holder,_bag,[7,1],500,0,1] call ACME_fnc_bloodExposureBroker;
        ["seed",_holder,_bag,[7,2],600,0,2] call ACME_fnc_bloodExposureBroker;
        _holder setVariable ["fixtureCargo",[_bag,_bag]];
        _clock=10;_frame=1;
        call ACME_fnc_bloodColdChainTick;
        private _ages=((_holder getVariable "ACME_bloodExposure") # 0) apply {_x # 2};
        [510 in _ages && {610 in _ages},"pending seeds collapsed onto one bag"] call _check;
        [(_holder getVariable "ACME_bloodExposurePending") isEqualTo [],"funded seeds did not retire"] call _check;
    ''')


def test_cached_read_with_later_native_inventory_change_defers_one_frame_once():
    execute(fixture()+r'''
        _box setVariable ["ACME_boxCoolerState",[_class,-100,[[_bag,700]],0]];
        _box setVariable ["fixtureCargo",[_bag]];
        _boxes=[_box];_units=[_holder];_clock=10;
        ["read",_holder,_bag,[7,1]] call ACME_fnc_bloodExposureBroker;
        private _count=count _events;
        _box setVariable ["fixtureCargo",[]];_holder setVariable ["fixtureCargo",[_bag]];
        ["read",_holder,_bag,[7,2]] call ACME_fnc_bloodExposureBroker;
        ["read",_holder,_bag,[7,2]] call ACME_fnc_bloodExposureBroker;
        [count _events==_count && {count _nextFrames==1},"stale cached read replied or scheduled twice"] call _check;
        _frame=1;
        private _next=_nextFrames # 0;(_next # 1) call (_next # 0);
        [((_events # ((count _events)-1)) # 1) # 3==702,"deferred read refreshed source exposure"] call _check;
        [(_holder getVariable "ACME_bloodExposureDeferred") isEqualTo [],"read dedupe marker leaked"] call _check;
    ''')


def test_earlier_generic_nudge_cannot_discover_a_box_take_as_fresh_blood():
    execute(fixture()+r'''
        _box setVariable ["ACME_boxCoolerState",[_class,-100,[[_bag,700]],0]];
        _box setVariable ["fixtureCargo",[]];_holder setVariable ["fixtureCargo",[_bag]];
        _boxes=[_box];_units=[_holder];_clock=10;_frame=1;
        [0] call ACME_fnc_bloodColdChainTick;
        ["read",_holder,_bag,[7,1]] call ACME_fnc_bloodExposureBroker;
        [((_events # ((count _events)-1)) # 1) # 3==702,"earlier generic scan refreshed box take"] call _check;
        [(((_holder getVariable "ACME_bloodExposure") # 0) # 0) # 2==702,"generic receiver lost source age"] call _check;
    ''')


def test_full_box_mixed_remove_and_admit_does_not_release_the_source_twice():
    execute(fixture()+r'''
        _box setVariable ["ACME_boxCoolerState",[_class,-100,[[_bag,900]],0]];
        _box setVariable ["fixtureCargo",[_fresh]];_holder setVariable ["fixtureCargo",[_bag]];
        _boxes=[_box];_units=[_holder];_clock=10;_frame=1;
        private _state=[_box,10] call ACME_fnc_coolerBoxReconcile;
        [(_state # 2) isEqualTo [[_fresh,0]],"new admission inherited removed bag exposure"] call _check;
        [(((_holder getVariable "ACME_bloodExposure") # 0) # 0) # 2==902,"receiver lost removed bag exposure"] call _check;
        private _float=missionNamespace getVariable "ACME_ccBagFloat";
        [(_float get _bag) isEqualTo [],"nested generic pass duplicated release age"] call _check;
        [(_box getVariable "ACME_boxCoolerState") isEqualTo _state,"nested reconciliation overwrote canonical state"] call _check;
    ''')


@pytest.mark.parametrize('volume', [250, 500])
@pytest.mark.parametrize('donor', [1, 250, 500, 512])
def test_native_fresh_blood_volume_does_not_read_donor_id_as_volume(volume, donor):
    execute(fixture() + f'''
    [(["ACM_FreshBloodBag_{volume}_{donor}"] call ACME_fnc_coolerBagVolume)=={volume},"fresh donorID was parsed as bag volume"] call _check;
    ''')
