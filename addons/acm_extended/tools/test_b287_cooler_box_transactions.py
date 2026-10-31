"""Execute server cooler box custody/debit and replay handling.

Transport, native cargo, engine creation and ownership are fixture boundaries.
The production broker, requests, replies and native ledger transitions run.
"""
import re

from test_b287_cooler_backend import setup as backend_setup
from test_b279_inventory_ledger import adapted
from test_historical_medication_rows import iteration_scopes
from test_menu_death_lifecycle import F, execute


def function(name):
    text=(F/f'fn_{name}.sqf').read_text()
    text=text.replace('serverTime','CBA_missionTime')
    text=text.replace('alive _owner','true').replace('_owner distance _box','_distance')
    text=text.replace('createVehicle [_boxClass,_owner getRelPos [1.1,0],[],0,"CAN_COLLIDE"]','_boxFixture')
    text=text.replace('_box setDir getDir _owner','_box setVariable ["dir",0]')
    text=text.replace('netId _box','"box"')
    for prefix,field in [('Weapon','weapons'),('Magazine','magazines'),('Item','cargo'),('Backpack','backpacks')]:
        text=text.replace(f'clear{prefix}CargoGlobal _box',f'_box setVariable ["{field}",[]]')
    for command,field in [('itemCargo','cargo'),('weaponCargo','weapons'),('magazineCargo','magazines'),('backpackCargo','backpacks')]:
        text=text.replace(f'{command} _box',f'(_box getVariable ["{field}",[]])')
    text=text.replace('_box addItemCargoGlobal [_x select 0,1]','[_box,_x select 0] call _addCargo')
    text=text.replace('_box addItemCargoGlobal [_x,1]','[_box,_x] call _addCargo')
    text=text.replace('_box setObjectTextureGlobal [_x,"#(argb,8,8,3)color(0.62,0.10,0.10,1.0,co)"]','nil')
    text=text.replace('deleteVehicle _box','_box setVariable ["deleted",true]')
    for c in ['uniformContainer','vestContainer','backpackContainer']:
        text=text.replace(f'{c} _owner','_holder')
    text=text.replace('_owner isKindOf "CAManBase"','true')
    text=text.replace('isNull (_holder)','false')
    text=text.replace('getNumber (configFile >> "CfgWeapons" >> (_state select 0) >> "ACME_coolerCapacityMl")','1000')
    text=text.replace('_box addItemCargoGlobal [_bagClass,-1]','[_box,_bagClass] call _removeCargo')
    text=text.replace('_box addItemCargoGlobal [_x select 0,-1]','[_box,_x select 0] call _removeCargo')
    text=text.replace('_box addItemCargoGlobal ["ACME_SpoiledBlood",1]','[_box,"ACME_SpoiledBlood"] call _addCargo')
    text=text.replace('forEach _requests;','forEach (keys _requests);').replace('private _args=+_y;','private _args=+(_requests get _x);')
    return f'ACME_fnc_{name}={{'+adapted(iteration_scopes(text))+'};'


def setup():
    return backend_setup()+r'''
    private _boxFixture=parsingNamespace;
    private _boxQueue=[];private _boxReplies=[];
    ACME_fnc_coolerBagVolume={500};
    private _removeCargo={params ["_box","_class"];private _cargo=+(_box getVariable ["cargo",[]]);private _i=_cargo find _class;if (_i>=0) then {_cargo deleteAt _i;};_box setVariable ["cargo",_cargo];};
    private _addCargo={params ["_box","_class"];private _cargo=+(_box getVariable ["cargo",[]]);_cargo pushBack _class;_box setVariable ["cargo",_cargo];};
    _boxFixture setVariable ["cargo",[]]; _boxFixture setVariable ["weapons",[]];_boxFixture setVariable ["magazines",[]];_boxFixture setVariable ["backpacks",[]];
    missionNamespace setVariable ["ACME_coolerBoxScale",1];
    CBA_fnc_serverEvent={if ((_this select 0)=="ACME_coolerBoxBroker") then {_boxQueue pushBack (_this select 1)} else {_queue pushBack (_this select 1)}};
    CBA_fnc_targetEvent={if ((_this select 0)=="ACME_coolerBoxReply") then {_boxReplies pushBack (_this select 1)} else {_replies pushBack (_this select 1)}};
    ACME_fnc_coolerBoxReconcile={params ["_box"]; +(_box getVariable ["ACME_boxCoolerState",[]])};
    ACM_core_fnc_setDraggingCapability={};
    private _given=[];private _giveCapacity=true;
    ACME_fnc_coolerGiveBag={params ["_owner","_entry"];if (!_giveCapacity) exitWith {false};_given pushBack +_entry;true};
    private _flushBoxes={while {count _boxQueue>0 || {count _boxReplies>0} || {count _queue>0} || {count _replies>0}} do {
        call _flush;
        while {count _boxQueue>0} do {(_boxQueue deleteAt 0) call ACME_fnc_coolerBoxBroker;};
        while {count _boxReplies>0} do {(_boxReplies deleteAt 0) call ACME_fnc_coolerBoxReply;};
    }};
    private _issueCooler={_medic setVariable ["inputItems",[_base]];[_medic,_base,_state] call ACME_fnc_coolerIssue};
    '''+'\n'.join(function(n) for n in ['coolerBoxRequest','coolerBoxBroker','coolerBoxReply'])


def test_deploy_and_pack_preserve_exact_token_coolant_and_warm_exposure():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    private _originalToken=((_medic getVariable "native") select 0) select 0;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    [(_medic getVariable "native") isEqualTo [] && {(_boxFixture getVariable "cargo") isEqualTo ["ACM_BloodBag_ON_500"]},"deployment duplicated or lost source"] call _check;
    [(_boxFixture getVariable "ACME_boxCoolerState") isEqualTo _state,"deployment changed elapsed/warm state"] call _check;
    ["pack",_medic,"",_boxFixture] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    [(_medic getVariable "native") isEqualTo [[_originalToken,"cooler"]],"packing reminted identity"] call _check;
    [([_medic] call ACME_fnc_coolerRows) isEqualTo [[_sid,_state]],"packing reset coolant or blood warmth"] call _check;
    [_boxFixture getVariable ["deleted",false],"proved packed source box survived"] call _check;
    ''')


def test_duplicate_deploy_message_does_not_create_another_box_or_carrier():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flush;
    private _message=+(_boxQueue select 0);call _flushBoxes;
    _message call ACME_fnc_coolerBoxBroker;
    while {count _boxReplies>0} do {(_boxReplies deleteAt 0) call ACME_fnc_coolerBoxReply;};
    [(_boxFixture getVariable "cargo") isEqualTo ["ACM_BloodBag_ON_500"] && {count (_medic getVariable "native")==0},"duplicate deploy replayed source"] call _check;
    [(missionNamespace getVariable "ACME_inventoryTokenSequence")==1,"deployment allocated another token"] call _check;
    ''')


def test_pending_pack_is_unusable_until_server_observes_native_placement():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    ["pack",_medic,"",_boxFixture] call ACME_fnc_coolerBoxRequest;
    (_boxQueue deleteAt 0) call ACME_fnc_coolerBoxBroker;
    (_boxReplies deleteAt 0) call ACME_fnc_coolerBoxReply;
    [count (_medic getVariable "native")==1 && {([_medic] call ACME_fnc_coolerRows) isEqualTo []},"packing token became usable before source was retired"] call _check;
    [!(_boxFixture getVariable ["deleted",false]) && {(_boxFixture getVariable "cargo") isEqualTo ["ACM_BloodBag_ON_500"]},"source cleared before placement proof"] call _check;
    call _flushBoxes;
    [count ([_medic] call ACME_fnc_coolerRows)==1,"placement proof did not finish custody"] call _check;
    ''')


def test_pack_with_unrelated_or_spoiled_cargo_preserves_source_untouched():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    _boxFixture setVariable ["cargo",["ACM_BloodBag_ON_500","ACME_SpoiledBlood","Radio"]];
    ["pack",_medic,"",_boxFixture] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    [(_boxFixture getVariable "cargo") isEqualTo ["ACM_BloodBag_ON_500","ACME_SpoiledBlood","Radio"] && {count (_medic getVariable "native")==0},"pack discarded unrelated cargo or created carrier"] call _check;
    [!(_boxFixture getVariable ["ACME_coolerPacking",false]),"rejected pack locked source"] call _check;
    ''')


def test_draw_debits_one_bag_and_duplicate_network_delivery_is_inert():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    private _calls=0;
    ["draw",_medic,"ACM_BloodBag_ON_500",_boxFixture,[{params ["_ok"];if (_ok) then {_calls=_calls+1;}},[]]] call ACME_fnc_coolerBoxRequest;
    private _message=+(_boxQueue select 0);call _flushBoxes;
    _message call ACME_fnc_coolerBoxBroker;call _flushBoxes;
    [(_boxFixture getVariable "cargo") isEqualTo [] && {_given isEqualTo [["ACM_BloodBag_ON_500",123]]} && {_calls==1},"draw duplicated native bag or callback"] call _check;
    ''')


def test_full_inventory_keeps_draw_in_durable_receipt_until_placement_succeeds():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    _giveCapacity=false;
    ["draw",_medic,"ACM_BloodBag_ON_500",_boxFixture] call ACME_fnc_coolerBoxRequest;
    private _message=+(_boxQueue select 0);call _flushBoxes;
    [count _given==0 && {count (_medic getVariable "ACME_coolerBoxRequests")==1},"full inventory lost durable draw"] call _check;
    CBA_missionTime=110;_giveCapacity=true;
    _message call ACME_fnc_coolerBoxBroker;call _flushBoxes;
    [_given isEqualTo [["ACM_BloodBag_ON_500",133]] && {count (_medic getVariable "ACME_coolerBoxRequests")==0},"retry reset freshness, lost bag or did not finish"] call _check;
    ''')


def test_replayed_pack_ack_after_gear_handoff_never_materializes_second_token():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    ["pack",_medic,"",_boxFixture] call ACME_fnc_coolerBoxRequest;
    (_boxQueue deleteAt 0) call ACME_fnc_coolerBoxBroker;
    private _ack=+(_boxReplies deleteAt 0);_ack call ACME_fnc_coolerBoxReply;
    _receiver setVariable ["native",_medic getVariable "native"];_medic setVariable ["native",[]];
    _ack call ACME_fnc_coolerBoxReply;
    [count (_medic getVariable "native")==0 && {count (_receiver getVariable "native")==1},"replayed pack ACK duplicated transferred physical token"] call _check;
    // The new native holder can certify placement even though the old proof was delayed.
    [_receiver] call ACME_fnc_coolerRecover;call _flushBoxes;
    [count ([_receiver] call ACME_fnc_coolerRows)==1 && {count (_medic getVariable "ACME_coolerBoxRequests")==0},"new holder could not finish pending packing"] call _check;
    ''')


def test_completed_pack_receipt_retires_old_request_after_another_edit():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    ["pack",_medic,"",_boxFixture] call ACME_fnc_coolerBoxRequest;
    (_boxQueue deleteAt 0) call ACME_fnc_coolerBoxBroker;
    (_boxReplies deleteAt 0) call ACME_fnc_coolerBoxReply;
    (_boxQueue deleteAt 0) call ACME_fnc_coolerBoxBroker;
    private _done=+(_boxReplies deleteAt 0);
    [_medic,_sid,{params ["_owner","_sid","_state"];[false,_state]}] call ACME_fnc_coolerMutate;call _flush;
    _done call ACME_fnc_coolerBoxReply;
    [count (_medic getVariable "ACME_coolerBoxRequests")==0,"completed receipt was blocked by newer current request"] call _check;
    ''')


def test_kit_change_before_pack_reply_cancels_without_native_placement_or_lock():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    ["pack",_medic,"",_boxFixture] call ACME_fnc_coolerBoxRequest;
    (_boxQueue deleteAt 0) call ACME_fnc_coolerBoxBroker;
    _medic setVariable ["ACME_equipmentKitEpoch",1];
    call _flushBoxes;
    [count (_medic getVariable "native")==0 && {!(_boxFixture getVariable ["ACME_coolerPacking",false])},"stale pack replenished new kit or left source locked"] call _check;
    [(_boxFixture getVariable "cargo") isEqualTo ["ACM_BloodBag_ON_500"] && {count (_medic getVariable "ACME_coolerBoxRequests")==0},"cancelled packing lost source or retry retirement"] call _check;
    ''')


def test_final_overcapacity_revalidation_rolls_back_native_carrier_and_unlocks_box():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    ["pack",_medic,"",_boxFixture] call ACME_fnc_coolerBoxRequest;
    (_boxQueue deleteAt 0) call ACME_fnc_coolerBoxBroker;
    (_boxReplies deleteAt 0) call ACME_fnc_coolerBoxReply;
    private _over=[_base,20,[["ACM_BloodBag_ON_500",123],["ACM_BloodBag_ON_500",123],["ACM_BloodBag_ON_500",123]],100];
    _boxFixture setVariable ["ACME_boxCoolerState",_over];
    _boxFixture setVariable ["cargo",["ACM_BloodBag_ON_500","ACM_BloodBag_ON_500","ACM_BloodBag_ON_500"]];
    call _flushBoxes;
    [count (_medic getVariable "native")==0 && {!(_boxFixture getVariable ["ACME_coolerPacking",false])},"invalid final packing left carrier usable or source locked"] call _check;
    [count (_boxFixture getVariable "cargo")==3 && {count (_medic getVariable "ACME_coolerBoxRequests")==0},"rollback lost cargo or retained stale request"] call _check;
    ''')


def test_failed_native_box_debit_rolls_back_and_retains_exact_cargo():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    ["pack",_medic,"",_boxFixture] call ACME_fnc_coolerBoxRequest;
    (_boxQueue deleteAt 0) call ACME_fnc_coolerBoxBroker;
    (_boxReplies deleteAt 0) call ACME_fnc_coolerBoxReply;
    _removeCargo={};
    call _flushBoxes;
    [count (_medic getVariable "native")==0 && {!(_boxFixture getVariable ["ACME_coolerPacking",false])},"failed native source debit kept a duplicate carrier or locked box"] call _check;
    [(_boxFixture getVariable "cargo") isEqualTo ["ACM_BloodBag_ON_500"],"failed debit rollback changed real cargo"] call _check;
    ''')


def test_draw_after_expiry_converts_source_to_spoiled_without_transfusion_callback():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    _boxFixture setVariable ["ACME_boxCoolerState",[_base,20,[["ACM_BloodBag_ON_500",1800]],100]];
    ["draw",_medic,"ACM_BloodBag_ON_500",_boxFixture] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    [count _given==0 && {(_boxFixture getVariable "cargo") isEqualTo ["ACME_SpoiledBlood"]},"expired blood was issued as a transfusable bag"] call _check;
    ''')


def test_failed_native_deploy_population_returns_original_carrier_without_freshness_reset():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    _addCargo={};
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    [([_medic] call ACME_fnc_coolerRows) isEqualTo [[_sid,_state]],"failed world placement lost or refreshed carried contents"] call _check;
    [count (_medic getVariable "native")==1 && {(_boxFixture getVariable "cargo") isEqualTo []},"failed deploy duplicated source"] call _check;
    ''')


def test_final_expiry_rolls_back_physical_carrier_and_preserves_world_blood():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    ["pack",_medic,"",_boxFixture] call ACME_fnc_coolerBoxRequest;
    (_boxQueue deleteAt 0) call ACME_fnc_coolerBoxBroker;
    (_boxReplies deleteAt 0) call ACME_fnc_coolerBoxReply;
    _boxFixture setVariable ["ACME_boxCoolerState",[_base,20,[["ACM_BloodBag_ON_500",1800]],100]];
    call _flushBoxes;
    [count (_medic getVariable "native")==0 && {!(_boxFixture getVariable ["ACME_coolerPacking",false])},"expired final state was issued or source remained locked"] call _check;
    [(_boxFixture getVariable "cargo") isEqualTo ["ACM_BloodBag_ON_500"],"expiry rollback destroyed physical blood"] call _check;
    ''')


def test_proven_kit_retirement_fences_moved_old_alias_before_source_unlock():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    private _oldToken=((_medic getVariable "native") select 0) select 0;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    ["pack",_medic,"",_boxFixture] call ACME_fnc_coolerBoxRequest;
    private _pack=+(_boxQueue select 0);
    (_boxQueue deleteAt 0) call ACME_fnc_coolerBoxBroker;
    private _ack=+(_boxReplies deleteAt 0);_ack call ACME_fnc_coolerBoxReply;
    // Delay placement proof, hand off the physical token, then replace the
    // originating kit. Its old UI cannot authorize this outstanding pickup.
    _boxQueue=[];
    _receiver setVariable ["native",_medic getVariable "native"];_medic setVariable ["native",[]];
    _medic setVariable ["ACME_equipmentKitEpoch",1];
    _ack call ACME_fnc_coolerBoxReply;call _flushBoxes;
    private _newToken=_boxFixture getVariable "ACME_boxCoolerToken";
    [_newToken != _oldToken && {!(_boxFixture getVariable ["ACME_coolerPacking",false])},"retired packing failed to fence alias before unlock"] call _check;
    [([_receiver] call ACME_fnc_coolerRows) isEqualTo [] && {(_boxFixture getVariable "ACME_boxCoolerState") isEqualTo _state},"old moved alias remained usable or source was refreshed"] call _check;
    private _late=["placed",_medic,_sid,_boxFixture,_pack select 4];_late call ACME_fnc_coolerBoxBroker;call _flushBoxes;
    [(_boxFixture getVariable "ACME_boxCoolerToken")==_newToken && {(_boxFixture getVariable "cargo") isEqualTo ["ACM_BloodBag_ON_500"]},"late original proof changed replacement source"] call _check;
    [_receiver] call ACME_fnc_coolerRecover;
    [count (_receiver getVariable "native")==0,"retired alias was not cleaned on native recovery"] call _check;
    ''')


def test_missing_placement_without_retired_kit_does_not_unlock_or_remint():
    execute(setup()+r'''
    private _sid=call _issueCooler;call _flush;
    ["deploy",_medic,_sid] call ACME_fnc_coolerBoxRequest;call _flushBoxes;
    ["pack",_medic,"",_boxFixture] call ACME_fnc_coolerBoxRequest;
    (_boxQueue deleteAt 0) call ACME_fnc_coolerBoxBroker;
    private _ack=+(_boxReplies deleteAt 0);_ack call ACME_fnc_coolerBoxReply;
    _boxQueue=[];
    _receiver setVariable ["native",_medic getVariable "native"];_medic setVariable ["native",[]];
    _ack call ACME_fnc_coolerBoxReply;
    [count (_medic getVariable "native")==0 && {_boxFixture getVariable ["ACME_coolerPacking",false]} && {(missionNamespace getVariable "ACME_inventoryTokenSequence")==1},"missing proof was mistaken for permission to unlock or duplicate"] call _check;
    ''')
