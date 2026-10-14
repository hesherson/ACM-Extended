"""Execute spiking, native cargo projection and placement with engine-boundary fixtures.

Real preparation, source receipts, CBA registration, token broker/ACK, class selection,
native tuple filtering and transfer custody run. Capacity/config/cargo/network commands
are explicit engine stand-ins; this is not a live Arma Gear/rendering acceptance test.
"""
import re
import pytest
from test_menu_death_lifecycle import execute, read, adapt, ROOT
from test_b274_transfusion_preparation import stage_setup
from test_b279_inventory_ledger import setup as ledger_setup, adapted
from test_historical_vial_execution import map_defaults
from test_historical_medication_rows import iteration_scopes

WEIGHTS = [11,21,26,31,37,47,51,52,62,72,77,81,101,102,112,122,127,152,202]


def native_code(text):
    text=text.replace('_owner isKindOf "CAManBase"','(_owner getVariable ["isUnit",false])')
    text=text.replace('local _unit','(_unit getVariable ["fixtureLocal",true])')
    for noun,key in [('uniformContainer','uniform'),('vestContainer','vest'),('backpackContainer','backpack')]:
        text=re.sub(noun+r' (_\w+)',r'(\1 getVariable ["'+key+r'",objNull])',text)
    text=text.replace('magazinesAmmoCargo _x','(_x getVariable ["cargo",[]])')
    text=text.replace('objectParent _container','objNull')
    text=re.sub(r'getText \(configFile >> "CfgMagazines" >> (_\w+) >> "ACME_inventoryKind"\)',r'([\1] call _kindConfig)',text)
    return adapted(iteration_scopes(text))


def setup(sync=False):
    config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    declared=re.findall(r'class (ACME_Prepared(?:IVSet_M\w+|Syringe_\d+)): ACME_Prepared\w+ \{ mass = ([\d.]+); \};',config)
    masses=','.join(f'["{name}",{value}]' for name,value in declared)
    selector=read('inventoryLedgerClass')
    selector=re.sub(r'getNumber \(configFile >> "CfgWeapons" >> (_\w+) >> "ItemInfo" >> "mass"\)',r'([\1] call _sourceMass)',selector)
    selector=selector.replace('isClass (configFile >> "CfgMagazines" >> _class)','(_class in _carrierMass)')
    selector=selector.replace('configFile >> "CfgMagazines" >> _class','_class')
    selector=selector.replace('isClass _cfg','(_cfg in _carrierMass)')
    selector=selector.replace('getNumber (_cfg >> "mass")','(_carrierMass get _cfg)')
    reply=read('inventoryLedgerReply')
    reply=re.sub(r'_owner canAdd \[([^]]+)\]',r'([_owner,\1] call _canAddNative)',reply)
    reply=reply.replace('_owner addMagazine [_class,_token]','[_owner,_class,_token] call _addNative')
    reply=reply.replace('createVehicle ["GroundWeaponHolder",getPosATL _owner,[],0,"CAN_COLLIDE"]','(call _createHolder)')
    reply=reply.replace('_destination addMagazineAmmoCargo [_class,1,_token]','[_destination,_class,_token] call _addNative')
    # Historical GUI stand-ins provide actual source receipts/selection/timers.
    # Replace only their inventory/runtime boundary with the production ledger.
    return stage_setup()+ledger_setup()+f'''
      private _syncEvents={str(sync).lower()};
      private _registered=createHashMap;private _classEvents=createHashMap;private _inventoryPFHs=[];
      private _messages=[];private _paints=[];private _canAddArguments=[];private _holdersCreated=0;
      private _denyOwner=false;private _denyHolder=false;private _denyCreation=false;
      private _uniform=parsingNamespace;
      _medic setVariable ["isUnit",true];_medic setVariable ["uniform",_uniform];
      _uniform setVariable ["cargo",[]];_receiver setVariable ["cargo",[]];_holder setVariable ["cargo",[]];
      _medic setVariable ["containerMax",50];_medic setVariable ["soldierMax",40];
      private _carrierMass=createHashMapFromArray [["ACME_PreparedIVSet",18],["ACME_PreparedSyringe",1],{masses}];
      private _sourceMasses=createHashMapFromArray [["ACME_IVLine",0.1],["ACME_YTubing",0.2],
        ["ACM_SalineBag_500",5],["ACM_BloodBag_ON_500",12.9],["ACM_Vial_Propofol",1.65],
        ["ACME_HTSBag",6.2],["ACM_EsmololBag",6.2],["HeavyKit",44.9],["UnknownBag",6.75]];
      private _sourceMass={{params ["_class"];if (_class in _sourceMasses) then {{_sourceMasses get _class}} else {{0}}}};
      private _kindConfig={{params ["_class"];if ((_class find "ACME_PreparedSyringe")==0) exitWith {{"syringe"}};if (_class in _carrierMass) then {{"prepared"}} else {{""}}}};
      private _cargoDestination={{params ["_unit"];if (_unit getVariable ["isUnit",false]) then {{_unit getVariable "uniform"}} else {{_unit}}}};
      private _canAddNative={{
        params ["_unit","_class","_count",["_ignoreSoldierMax",false]];
        _canAddArguments pushBack +_this;
        private _mass=0;{{_mass=_mass+([_x] call _sourceMass);}} forEach (_unit getVariable ["fixtureStock",[]]);
        private _cargo=[_unit] call _cargoDestination;
        {{_mass=_mass+(_carrierMass get (_x select 0));}} forEach (_cargo getVariable ["cargo",[]]);
        private _after=_mass+(_carrierMass get _class)*_count;
        !_denyOwner && {{_after<=(_unit getVariable ["containerMax",50])+0.00001}}
          && {{_ignoreSoldierMax || {{_after<=(_unit getVariable ["soldierMax",40])}}}}
      }};
      _addNative={{
        params ["_unit","_class","_token"];
        if ((_unit isEqualTo _medic && {{_denyOwner}}) || {{_unit isEqualTo _holder && {{_denyHolder}}}}) exitWith {{}};
        private _cargo=[_unit] call _cargoDestination;
        private _rows=+(_cargo getVariable ["cargo",[]]);_rows pushBack [_class,_token];_cargo setVariable ["cargo",_rows];
      }};
      private _createHolder={{_holdersCreated=_holdersCreated+1;if (_denyCreation) then {{objNull}} else {{_holder}}}};
      ace_common_fnc_removeSpecificMagazine={{
        params ["_unit","_class","_token"];private _cargo=[_unit] call _cargoDestination;
        private _rows=+(_cargo getVariable ["cargo",[]]);private _at=_rows find [_class,_token];
        if (_at<0) exitWith {{false}};_rows deleteAt _at;_cargo setVariable ["cargo",_rows];true
      }};
      ace_common_fnc_displayTextStructured={{_messages pushBack (_this select 0);}};
      ACME_fnc_updateTransfusionControls={{
        private _sets=ACE_player getVariable ["ACME_preparedIVSets",[]];
        _paints pushBack [count _sets,uiNamespace getVariable ["ACME_preparedListMode",false],+_sets];
      }};
      CBA_fnc_addEventHandler={{params ["_name","_code"];_registered set [_name,_code];0}};
      CBA_fnc_addClassEventHandler={{_classEvents set [_this select 1,_this select 2];0}};
      CBA_fnc_addPerFrameHandler={{_inventoryPFHs pushBack _this;count _inventoryPFHs-1}};
      CBA_fnc_addPlayerEventHandler={{[_medic] call (_this select 1);0}};
      CBA_fnc_execNextFrame={{(_this select 1) call (_this select 0);}};
      CBA_fnc_serverEvent={{if (_syncEvents) then {{(_this select 1) call (_registered get (_this select 0));}} else {{_queue pushBack +_this;}}}};
      CBA_fnc_targetEvent={{if (_syncEvents) then {{(_this select 1) call (_registered get (_this select 0));}} else {{_replies pushBack +_this;}}}};
      _broker={{while {{count _queue>0}} do {{private _e=_queue deleteAt 0;(_e select 1) call (_registered get (_e select 0));}}}};
      _reply={{while {{count _replies>0}} do {{private _e=_replies deleteAt 0;(_e select 1) call (_registered get (_e select 0));}}}};
      _flush={{while {{count _queue>0 || {{count _replies>0}}}} do {{call _broker;call _reply;}}}};
    '''+'ACME_fnc_inventoryLedgerClass={'+adapted(selector)+'};'+\
      'ACME_fnc_inventoryLedgerNative={'+native_code(read('inventoryLedgerNative'))+'};'+\
      'ACME_fnc_inventoryLedgerReply={'+adapted(reply)+'};'+\
      'ACME_fnc_inventoryLedgerInit={'+native_code(read('inventoryLedgerInit'))+'};'+r'''
      call ACME_fnc_inventoryLedgerInit;
      ["ACME_inventoryBroker" in _registered && {"ACME_inventoryReply" in _registered},"runtime event handlers missing"] call _check;
      private _spike={
        _rowData=["ACM_SalineBag_500|SalineIV_500"];
        _medic setVariable ["fixtureStock",["HeavyKit","ACM_SalineBag_500","ACME_IVLine"]];
        [] call ACME_fnc_transfusionSpikeOrAdd;
        private _job=_waits deleteAt 0;(_job select 1) call (_job select 0);
      };
    '''


@pytest.mark.parametrize('sync',[False,True])
def test_spike_replaces_sources_at_equal_mass_and_registered_ack_refreshes_prepared_cards(sync):
    execute(setup(sync)+r'''
      call _spike;
      if (!_syncEvents) then {
        [count (_medic getVariable "ACME_inventoryPending")==1 && {(_uniform getVariable "cargo") isEqualTo []},"source funding did not wait for registration"] call _check;
        [(_messages findIf {_x=="Prepared IV set is ready."})<0,"unregistered preparation claimed carried readiness"] call _check;
        call _flush;
      };
      private _sets=_medic getVariable "ACME_preparedIVSets";private _sid=_sets select 0 select 0;
      private _token=(missionNamespace getVariable "ACME_inventoryLedgerIndex") get ("prepared:"+_sid);
      [count _sets==1 && {(_uniform getVariable "cargo") isEqualTo [["ACME_PreparedIVSet_M51",_token]]},"nearly full container lost the equal-mass spiked set"] call _check;
      [(_medic getVariable "fixtureStock") isEqualTo ["HeavyKit"] && {count (_medic getVariable "ACME_inventoryPending")==0},"source debit or registration settlement incorrect"] call _check;
      [(_canAddArguments select 0 select 3) && {uiNamespace getVariable ["ACME_preparedListMode",false]} && {(_paints select (count _paints-1) select 0)==1},"ACE admission or ACK prepared-card refresh omitted"] call _check;
      [(_messages findIf {_x=="Prepared IV set is ready."})>=0 && {_holdersCreated==0},"carried readiness was false or unexpectedly spilled"] call _check;
      [str (_patient getVariable "ACM_circulation_IV_Bags")==_initialBagText,"spike hung a patient bag"] call _check;
    ''')


def test_variant_transfer_adoption_claim_and_return_keep_exact_native_class_and_payload():
    execute(setup()+r'''
      call _spike;call _flush;
      private _set=(_medic getVariable "ACME_preparedIVSets") select 0;private _sid=_set select 0;
      private _tuple=(_uniform getVariable "cargo") select 0;
      _receiver setVariable ["cargo",[_tuple]];_uniform setVariable ["cargo",[]];
      [_medic,_receiver,_tuple select 0] call (_classEvents get "Put");
      [_receiver,_uniform,_tuple select 0] call (_classEvents get "Take");call _flush;
      [(_medic getVariable "ACME_preparedIVSets") isEqualTo [] && {(_receiver getVariable "ACME_preparedIVSets") isEqualTo [_set]},"native variant transfer lost metadata or donor custody"] call _check;
      private _receipt=[_receiver,"prepared",_sid,"return-variant"] call ACME_fnc_inventoryLedgerReserve;
      [count _receipt==2 && {(_receiver getVariable "cargo") isEqualTo []},"variant reserve removed wrong native class"] call _check;
      [_receiver,"return-variant",{},[]] call ACME_fnc_inventoryLedgerClaim;call _flush;
      [_receiver,"return-variant",false] call ACME_fnc_inventoryLedgerSettle;call _flush;
      [(_receiver getVariable "cargo") isEqualTo [_tuple] && {(_receiver getVariable "ACME_preparedIVSets") isEqualTo [_set]},"variant return changed identity/class/contents"] call _check;
    ''')


def test_failed_holder_readback_retains_funding_reuses_holder_and_reports_ground_truth():
    execute(setup()+r'''
      _denyOwner=true;_denyHolder=true;call _spike;call _flush;
      [count (_medic getVariable "ACME_inventoryPending")==1 && {_holdersCreated==1} && {(_holder getVariable "cargo") isEqualTo []},"failed materialization discarded funding or invented cargo"] call _check;
      private _entry=(_medic getVariable "ACME_preparedIVSets") select 0;private _sid=_entry select 0;
      ["register",_medic,"prepared",_sid,[_sid,_entry,[]],""] call ACME_fnc_inventoryLedgerBroker;call _reply;
      [_holdersCreated==1 && {count _messages==2},"retry created another holder or repeated waiting notice"] call _check;
      _denyHolder=false;
      ["register",_medic,"prepared",_sid,[_sid,_entry,[]],""] call ACME_fnc_inventoryLedgerBroker;call _reply;
      [count (_medic getVariable "ACME_inventoryPending")==0 && {count (_holder getVariable "cargo")==1} && {(_medic getVariable "ACME_preparedIVSets") isEqualTo []},"confirmed ground item retained provider-held presentation or lost funding"] call _check;
      [(_messages findIf {(_x find "placed on the ground")>=0})>=0 && {(_messages findIf {_x=="Prepared IV set is ready."})<0},"ground spill claimed carried readiness"] call _check;
    ''')


def test_failed_holder_creation_waiting_notice_is_once_and_terminal_refund_waits_for_cargo():
    execute(setup()+r'''
      _denyOwner=true;_denyCreation=true;call _spike;call _flush;
      private _entry=(_medic getVariable "ACME_preparedIVSets") select 0;private _sid=_entry select 0;
      for "_i" from 0 to 2 do {["register",_medic,"prepared",_sid,[_sid,_entry,[]],""] call ACME_fnc_inventoryLedgerBroker;call _reply;};
      [count _messages==2 && {count (_medic getVariable "ACME_inventoryPending")==1},"failed holder creation repeated waiting notice or lost funded preparation"] call _check;
      _denyOwner=false;_denyCreation=false;
      ["register",_medic,"prepared",_sid,[_sid,_entry,[]],""] call ACME_fnc_inventoryLedgerBroker;call _reply;
      [_medic,"prepared",_sid,"terminal-placement"] call ACME_fnc_inventoryLedgerReserve;
      [_medic,"terminal-placement",{},[]] call ACME_fnc_inventoryLedgerClaim;call _flush;
      _denyOwner=true;_denyHolder=true;
      [_medic,"terminal-placement",false] call ACME_fnc_inventoryLedgerSettle;call _flush;
      [count (_medic getVariable "ACME_inventoryEscrow")==1 && {count (_medic getVariable "ACME_inventoryRequests")==1},"unconfirmed refund erased durable custody/retry"] call _check;
      _denyHolder=false;
      [_medic,"terminal-placement",false] call ACME_fnc_inventoryLedgerSettle;call _flush;
      [count (_medic getVariable "ACME_inventoryEscrow")==0 && {count (_holder getVariable "cargo")==1},"confirmed refund did not settle once into exact holder"] call _check;
    ''')


def test_source_mass_selection_fallback_and_raw_invalid_ammo_are_conservative():
    execute(setup()+r'''
      private _single=["s",["s","ACME_HTSBag","HTSIV_250","","","","",false,"premixed"],[]];
      [["prepared",_single] call ACME_fnc_inventoryLedgerClass=="ACME_PreparedIVSet_M63","HTS source mass not preserved"] call _check;
      (_single select 1) set [1,"ACM_EsmololBag"];
      [["prepared",_single] call ACME_fnc_inventoryLedgerClass=="ACME_PreparedIVSet_M63","esmolol source mass not preserved"] call _check;
      (_single select 1) set [1,"UnknownBag"];
      [["prepared",_single] call ACME_fnc_inventoryLedgerClass=="ACME_PreparedIVSet","unknown third-party mass was arbitrarily lowered"] call _check;
      _uniform setVariable ["cargo",[["ACME_PreparedIVSet_M51",0],["ACME_PreparedIVSet_M51",65535],["unrelated",1]]];
      [[_medic] call ACME_fnc_inventoryLedgerNative isEqualTo [],"raw/default invalid identities were imported"] call _check;
    ''')


def test_carrier_config_subtypes_inherit_kind_and_disable_ace_repacking():
    config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    base=config.split('class ACME_PreparedIVSet: CA_Magazine {',1)[1].split('};',1)[0]
    assert 'ace_disableRepacking = 1;' in base and 'ACME_inventoryKind = "prepared";' in base
    for weight in WEIGHTS:
        assert f'class ACME_PreparedIVSet_M{weight}: ACME_PreparedIVSet {{ mass = {weight/10:g}; }};' in config
    assert 'ACME_inventoryKind = "syringe";' in config


@pytest.mark.parametrize('source,secondary,kind,expected',[
    ('ACM_BloodBag_ON_500','','blood','ACME_PreparedIVSet_M130'),
    ('ACM_BloodBag_ON_500','ACM_SalineBag_500','yset','ACME_PreparedIVSet_M181'),
    ('ACM_Vial_Propofol','','premixed','ACME_PreparedIVSet_M1_75'),
])
def test_contributed_bag_weights_execute_through_exact_class_selection(source,secondary,kind,expected):
    execute(setup()+f'''
      private _set=["new-mass","{source}","source-action","{secondary}","secondary-action","","",false,"{kind}"];
      private _class=["prepared",["new-mass",_set,[]]] call ACME_fnc_inventoryLedgerClass;
      [_class=="{expected}","current bag/tubing mass selected wrong physical carrier"] call _check;
    ''')


@pytest.mark.parametrize('size',[1,3,5,10])
def test_syringe_size_carrier_issue_transfer_reserve_and_return_preserve_identity(size):
    execute(setup()+f'''
      private _sid="syringe-size-{size}";
      private _row=["Epinephrine",{size},{size},0,0,0,"compoundB13",0,0,0,0,_sid,"","inventoryB279"];
      [_medic,"syringe",[[_sid,_row]]] call ACME_fnc_inventoryLedgerCommit;call _flush;
      private _tuple=(_uniform getVariable "cargo") select 0;
      [(_tuple select 0)=="ACME_PreparedSyringe_{size}","prepared syringe changed empty syringe encumbrance"] call _check;
      [_tuple select 0] call _kindConfig;
      _receiver setVariable ["cargo",[_tuple]];_uniform setVariable ["cargo",[]];
      [_medic,_receiver,_tuple select 0] call (_classEvents get "Put");
      [_receiver,_uniform,_tuple select 0] call (_classEvents get "Take");call _flush;
      [[_receiver,"syringe",_sid] call ACME_fnc_inventoryLedgerPossessed,"size variant did not retain syringe custody"] call _check;
      private _receipt=[_receiver,"syringe",_sid,"return-size"] call ACME_fnc_inventoryLedgerReserve;
      [count _receipt==2 && {{(_receiver getVariable "cargo") isEqualTo []}},"size variant did not reserve exact native carrier"] call _check;
      [_receiver,"return-size",{{}},[]] call ACME_fnc_inventoryLedgerClaim;call _flush;
      [_receiver,"return-size",false] call ACME_fnc_inventoryLedgerSettle;call _flush;
      [(_receiver getVariable "cargo") isEqualTo [_tuple],"return changed syringe carrier class or token"] call _check;
    ''')
