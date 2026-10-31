"""Execute fridge stock/door/provider lifecycles; native hinge and RTM playback are engine boundaries."""
import re
import pytest
from test_menu_death_lifecycle import adapt, execute, read
from test_historical_vial_execution import map_defaults
from test_historical_medication_rows import iteration_scopes


def source(name):
    raw = read(name)
    for old, new in {
        'isServer': '_server', 'local _player': '_playerLocal',
        'canSuspend': 'false',
        'alive _player': '_alive', 'alive _unit': '_alive',
        '_player distance _anchor': '_distance', '_unit distance _anchor': '_distance',
        'objectParent _player': '_vehicle', 'netId _player': '_playerId',
        'owner _player': '_requestOwnerSim',
        'getText (configFile >> "CfgWeapons" >> _class >> "displayName")': '"Blood"',
        '(dateToNumber date) * _yearHours': '10',
        'allPlayers select {alive _x && {(_x distance _anchor) <= 80}}': '[_player]',
        '_takers getOrDefault [_key, []]': '([_takers, _key] call _mapGet)',
        '_history getOrDefault [_key, 0]': '([_history, _key, 0] call _mapGet)',
        '(allPlayers apply {owner _x})': '[6,7,8]',
        'netId _anchor': '"fridge"',
        'uniformItems _player': '(_player getVariable ["fixtureItems",[]])',
        'vestItems _player': '[]', 'backpackItems _player': '[]',
        'nearestObject [_player,"WeaponHolder"]': '_groundHolder',
        'itemCargo _nearHolder': '(_nearHolder getVariable ["fixtureItems",[]])',
        'itemCargo _holder': '(_holder getVariable ["fixtureItems",[]])',
        '(_placement select 1) isEqualType objNull': 'true',
        'isNull (_placement select 1)': '((_placement select 1) isEqualTo objNull)',
    }.items():
        raw = raw.replace(old, new)
    raw = re.sub(r'_anchor animateSource ([^;]+);', r'_doors pushBack \1;', raw)
    raw = re.sub(r'(_anchor|_openObj) hideObjectGlobal ([^;]+);', r'_hidden pushBack [\1, \2];', raw)
    raw=re.sub(r'\bfinite (_\w+)',r'(\1 call _finite)',raw)
    return adapt(map_defaults(iteration_scopes(raw)))


def resource_source(name):
    from test_b288_resource_returns import source as generic_source
    text = generic_source(name)
    for old,new in {
        '_ownerNum':'_requestOwnerSim','_medicLocal':'_playerLocal',
        'nativeItems':'fixtureItems','_ground':'_groundHolder',
    }.items():
        text=text.replace(old,new)
    return text


def setup():
    code = '''
        private _server=true; private _playerLocal=true; private _vehicle=objNull;
        private _player=_medic; private _anchor=_patient; private _other=missionNamespace;
        private _playerId="one"; private _requestOwnerSim=7;
        private _blocked=false; private _busy=false; private _canInteract=true;
        private _given=[]; private _reaches=[]; private _cancelled=0; private _doors=[]; private _hidden=[];
        private _groundHolder=parsingNamespace;private _giveWorks=true;private _giveGround=false;
        private _machineOwner=7;
        private _resourcePackets=[];private _resourceServerMessages=[];private _resourceQueries=[];
        missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","client-A"];
        missionNamespace setVariable ["ACME_syringeDeliveryMachines",createHashMapFromArray [["2","server"],["7","client-A"],["8","client-B"]]];
        private _finite={_this isEqualType 0};
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
        _player setVariable ["fixtureItems",[]];_groundHolder setVariable ["fixtureItems",[]];
        _anchor setVariable ["ACME_bloodFridge",true];
        _anchor setVariable ["ACME_bf_stock",[["ON",1],["A",2]]];
        _anchor setVariable ["ACME_bf_restock",false];
        _anchor setVariable ["ACME_bf_viewers",createHashMap];
        _anchor setVariable ["ACME_bf_takers",createHashMap];
        missionNamespace setVariable ["ACME_bloodFridges",[_anchor]];
        missionNamespace setVariable ["ACME_sys_bloodChain",false];
        CBA_fnc_serverEvent={
            _events pushBack _this;
            if ((_this select 0)=="ACME_resourceReturn") then {_resourceServerMessages pushBack (_this select 1);};
        };
        CBA_fnc_targetEvent={
            _events pushBack _this;
            if ((_this select 0)=="ACME_resourceReturnDelivery") then {_resourcePackets pushBack (_this select 1);};
        };
        CBA_fnc_ownerEvent={_events pushBack _this;_resourceQueries pushBack _this;};
        ACME_fnc_animBlocked={_blocked}; ACME_fnc_providerStanceOwned={_busy};
        ace_common_fnc_canInteractWith={_canInteract};
        ace_common_fnc_addToInventory={
            _given pushBack _this;
            private _destination=if (_giveGround) then {_groundHolder} else {_this select 0};
            if (_giveWorks) then {private _items=+(_destination getVariable ["fixtureItems",[]]);_items pushBack (_this select 1);_destination setVariable ["fixtureItems",_items];};
            [!_giveGround,_destination]
        };
        ACME_fnc_setVarNet={(_this select 0) setVariable [_this select 1,_this select 2];};
        ACME_fnc_headElevMedicSeq={
            _reaches pushBack _this;
            _player setVariable ["ACME_headElev_medicAnimToken",1+(_player getVariable ["ACME_headElev_medicAnimToken",0])];
            _player setVariable ["ACME_headElev_seqActive",true];
        };
        ACME_fnc_headElevateCancelSeq={
            _cancelled=_cancelled+1;
            _player setVariable ["ACME_headElev_seqActive",false];
            _player setVariable ["ACME_headElev_medicAnimToken",1+(_player getVariable ["ACME_headElev_medicAnimToken",0])];
        };
        private _mapGet={params["_map","_key",["_default",[]]]; if (_key in keys _map) then {_map get _key} else {_default}};
        private _run={
            {private _h=_x;if (_h select 2 && {count (_h select 1)==5}) then {[_h select 1,_forEachIndex] call (_h select 0);};} forEach (+_handlers);
        };
    '''
    for name in ['syringeDeliveryCopy','resourceReturnProductsValid','resourceReturnBroker','resourceReturnReceive','resourceReturnQuery','resourceReturnSourceQuery']:
        code += f'ACME_fnc_{name}={{' + resource_source(name) + '};'
    for name in ['bloodFridgeTick', 'bloodFridgeTake', 'bloodFridgeTakeOwner', 'bloodFridgeReceive']:
        code += f'ACME_fnc_{name}={{' + source(name) + '};'
    init = source('initBloodStorageRuntime')
    stop = init.split('["ACME_bfTakeStop", {', 1)[1].split('}] call CBA_fnc_addEventHandler;', 1)[0]
    code += 'private _stop={' + stop + '};'
    code += r'''
        private _flushResources={
            private _limit=0;
            while {(_resourceServerMessages isNotEqualTo [] || {_resourcePackets isNotEqualTo []} || {_resourceQueries isNotEqualTo []}) && {_limit<80}} do {
                _limit=_limit+1;
                while {_resourceServerMessages isNotEqualTo []} do {
                    private _message=_resourceServerMessages deleteAt 0;
                    _machineOwner=2;missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","server"];
                    _message call ACME_fnc_resourceReturnBroker;
                };
                while {_resourceQueries isNotEqualTo []} do {
                    private _query=_resourceQueries deleteAt 0;
                    private _event=_query select 0;private _payload=_query select 1;
                    if (_event=="ACME_resourceReturnQuery") then {
                        _machineOwner=_payload select 4;missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce",_payload select 5];
                        _payload call ACME_fnc_resourceReturnQuery;
                    };
                    if (_event=="ACME_resourceReturnSourceQuery") then {
                        private _cert=_payload select 4;_machineOwner=_cert select 0;missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce",_cert select 1];
                        _payload call ACME_fnc_resourceReturnSourceQuery;
                    };
                };
                private _deliver=+_resourcePackets;_resourcePackets=[];
                {
                    _machineOwner=_x select 4;missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce",_x select 5];
                    _x call ACME_fnc_resourceReturnReceive;
                } forEach _deliver;
            };
            [_limit<80,"resource transport did not quiesce"] call _check;
            _machineOwner=7;missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","client-A"];
        };
        private _resourceTick={
            _machineOwner=2;missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","server"];
            ["tick",[]] call ACME_fnc_resourceReturnBroker;
            _machineOwner=7;missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","client-A"];
        };
    '''
    return code


def take():
    return '''
        [_anchor,"ON",_player] call ACME_fnc_bloodFridgeTake;
        private _token=(_player getVariable "ACME_bf_take") select 0;
        [_anchor,"ON",_player,_token] call ACME_fnc_bloodFridgeTakeOwner;
        call _flushResources;call ACME_fnc_bloodFridgeTick;
        [_anchor,"ON",_player,_token,"delivered","fridge:one:7:1"] call ACME_fnc_bloodFridgeReceive;
    '''


def test_take_opens_authored_hinge_even_with_cold_chain_disabled_and_closes_after_reach():
    execute(setup()+take()+'''
        [_given isEqualTo [[_player,"ON"]],"inventory grant lost"] call _check;
        [_reaches isEqualTo [[_player,"elevate"]],"not the head-position sequence"] call _check;
        [_doors isEqualTo [["Door_1_noSound_source",1,2]],"native hinge did not open"] call _check;
        [count (_anchor getVariable "ACME_bf_takers")==1,"door take lease missing"] call _check;
        call _run;
        [_doors isEqualTo [["Door_1_noSound_source",1,2]],"door closed during reach"] call _check;
        _player setVariable ["ACME_headElev_seqActive",false]; call _run;
        [_anchor,_player,_token] call _stop;
        [_doors isEqualTo [["Door_1_noSound_source",1,2],["Door_1_noSound_source",0,2]],"door did not close"] call _check;
        [count (_events select {(_x select 0)=="ACME_worldSfx"})==2,"missing or repeated SFX"] call _check;
        [(_player getVariable "ACME_bf_take") isEqualTo [],"local interaction stuck"] call _check;
    ''')


def test_duplicate_take_and_grant_never_duplicate_inventory_or_stock_decrement():
    execute(setup()+take()+'''
        [_anchor,"ON",_player] call ACME_fnc_bloodFridgeTake;
        [_anchor,"ON",_player,_token] call ACME_fnc_bloodFridgeTakeOwner;
        [_anchor,"ON",_player,_token] call ACME_fnc_bloodFridgeReceive;
        [count _given==1 && {count _reaches==1},"duplicate give or theatre"] call _check;
        [((_anchor getVariable "ACME_bf_stock") select 0 select 1)==0,"stock decremented twice"] call _check;
    ''')


def test_two_takers_competing_for_last_unit_are_serialized_on_server():
    execute(setup()+'''
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        _player=_other; _playerId="two";
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        private _acks=_events select {(_x select 0)=="ACME_bfGive"};
        private _deliveries=_events select {(_x select 0)=="ACME_resourceReturnDelivery"};
        [count _acks==1 && {(_acks select 0 select 1 select 1)==""}
            && {count _deliveries==1} && {(_deliveries select 0 select 1 select 3) isEqualTo [["item","ON"]]},"last bag double issued"] call _check;
        call _flushResources;
        [count _given==1 && {(_given select 0 select 0) isEqualTo _medic},"winning funded item was lost or sent to competing taker"] call _check;
        [count (_anchor getVariable "ACME_bf_takers")==1,"out-of-stock take held door"] call _check;
    ''')


@pytest.mark.parametrize('change', ['_distance=8;', '_alive=false;', '_blocked=true;', '_canInteract=false;', '_player setVariable ["ACME_DP_Active",true];', '_nowTime=18;'])
def test_interrupted_reach_keeps_granted_item_and_releases_exact_episode(change):
    execute(setup()+take()+change+'''
        call _run;
        [count _given==1 && {_cancelled==1},"interruption lost item or left owned reach"] call _check;
        [(_player getVariable "ACME_bf_take") isEqualTo [],"interrupted take stuck"] call _check;
        [_anchor,_player,_token] call _stop;
        [!(_anchor getVariable "ACME_bf_open"),"interrupted take door retained"] call _check;
    ''')


def test_new_provider_episode_is_not_cancelled_by_old_fridge_cleanup():
    execute(setup()+take()+'''
        _player setVariable ["ACME_headElev_medicAnimToken",99];
        call _run;
        [_cancelled==0 && {_player getVariable "ACME_headElev_seqActive"},"old fridge interrupted new provider"] call _check;
    ''')


@pytest.mark.parametrize('change', ['_busy=true;', '_blocked=true;', '_canInteract=false;', '_alive=false;', '_distance=8;', '_player setVariable ["ACME_DP_Active",true];'])
def test_invalid_or_busy_provider_cannot_start_a_take(change):
    execute(setup()+change+'''
        [_anchor,"ON",_player] call ACME_fnc_bloodFridgeTake;
        [count _events==0 && {count _given==0},"invalid provider requested stock"] call _check;
    ''')


def test_late_ack_delivers_stock_without_overwriting_new_action():
    execute(setup()+'''
        [_anchor,"ON",_player] call ACME_fnc_bloodFridgeTake;
        private _old=(_player getVariable "ACME_bf_take") select 0;
        [_anchor,"ON",_player,_old] call ACME_fnc_bloodFridgeTakeOwner;
        private _w=_waits select 0; (_w select 1) call (_w select 0);
        _player setVariable ["ACME_bf_take",[[7,2],_anchor]];
        call _flushResources;
        [_anchor,"ON",_player,_old,"delivered","fridge:one:7:1"] call ACME_fnc_bloodFridgeReceive;
        [count _given==1 && {count _reaches==0},"late stock lost or stale animation started"] call _check;
        [(_player getVariable "ACME_bf_take") isEqualTo [[7,2],_anchor],"late ack erased successor"] call _check;
    ''')


def test_reconnected_owner_can_start_sequence_one_without_catching_up_old_counter():
    execute(setup()+'''
        private _history=createHashMap; _history set ["6",80];
        _player setVariable ["ACME_bf_serverTakeTokens",_history];
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        [((_anchor getVariable "ACME_bf_stock") select 0 select 1)==0,"old locality counter rejected new owner"] call _check;
        [_anchor,"A",_player,[6,81]] call ACME_fnc_bloodFridgeTakeOwner;
        [((_anchor getVariable "ACME_bf_stock") select 1 select 1)==2,"stale owner took stock"] call _check;
    ''')


def test_returning_to_previous_owner_does_not_redebit_replayed_request():
    execute(setup()+'''
        [_anchor,"A",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        _requestOwnerSim=8;
        [_anchor,"A",_player,[8,1]] call ACME_fnc_bloodFridgeTakeOwner;
        _requestOwnerSim=7;
        [_anchor,"ON",_player,[7,1]] call ACME_fnc_bloodFridgeTakeOwner;
        [((_anchor getVariable "ACME_bf_stock") select 0 select 1)==1,"A-B-A replay debited another bag"] call _check;
        [_anchor,"ON",_player,[7,2]] call ACME_fnc_bloodFridgeTakeOwner;
        [((_anchor getVariable "ACME_bf_stock") select 0 select 1)==0,"returning owner valid request rejected"] call _check;
    ''')


def test_stale_stop_preserves_newer_take_and_other_viewer():
    execute(setup()+take()+'''
        private _t=_anchor getVariable "ACME_bf_takers";
        _t set ["one",[_player,[7,2],20]];
        [_anchor,_player,_token] call _stop;
        [count _t==1 && {_anchor getVariable "ACME_bf_open"},"old stop closed successor"] call _check;
        private _v=_anchor getVariable "ACME_bf_viewers"; _v set ["two",_nowTime];
        [_anchor,_player,[7,2]] call _stop;
        [_anchor getVariable "ACME_bf_open","one taker closed on another viewer"] call _check;
        _nowTime=12; call ACME_fnc_bloodFridgeTick;
        [!(_anchor getVariable "ACME_bf_open"),"expired viewer held door"] call _check;
    ''')


def test_disconnected_take_expires_without_client_callback():
    execute(setup()+take()+'''
        _nowTime=19; call ACME_fnc_bloodFridgeTick;
        [!(_anchor getVariable "ACME_bf_open") && {count (_anchor getVariable "ACME_bf_takers")==0},"lost client held door"] call _check;
    ''')


def test_actual_world_menu_and_bounded_throttled_server_transport():
    init=read('initBloodStorageRuntime')
    assert 'if (_menuType != 0) exitWith {};' in init
    assert 'if (_menuType != 1)' not in init
    assert 'CBA_fnc_serverEvent' in read('bloodFridgeMenuPoll')
    assert '(diag_tickTime - _last) < 0.4' in read('bloodFridgeMenuPoll')
    assert 'if (count _received > 64)' in read('bloodFridgeReceive')
    assert 'ACME_bf_receivedTokens", _received, true' in read('bloodFridgeReceive')


def test_no_model_swap_or_unverified_source_and_shared_provider_safety_remains():
    assert 'createVehicle' not in read('bloodFridgeSetup')
    assert 'Door_1_noSound_source' in read('bloodFridgeTick')
    assert '_anchor hideObjectGlobal true' not in read('bloodFridgeTick')
    seq=read('headElevMedicSeq')
    assert 'ACME_fnc_providerAnimation' in seq and 'ACME_fnc_medicAnimationPrep' in seq
    assert 'ACME_fnc_choreographyRate' in seq
    assert 'AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown' in seq
    assert 'AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon' in seq
    assert 'selectWeapon' not in read('bloodFridgeReceive')
