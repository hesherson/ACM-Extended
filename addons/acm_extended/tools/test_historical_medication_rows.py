"""Batch 5: execute native registry writes and the real medication row pipeline.

Config/item queries and listbox primitives use fixtures. Source membership,
normalization, selection and metadata binding execute unchanged SQF. Nested-array alphabetical
ordering is not certified by this VM; the source sort delegation is checked separately.
Unsupported VM continue maps to a scope exit for its own iteration only; no
patient or UI outcome is replaced. Does not simulate rendered Arma controls.
"""
import re
from pathlib import Path
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, adapt, execute
from test_historical_vial_execution import map_defaults

F=ROOT/'addons/acm_extended/functions'


def iteration_scopes(text):
    """Preserve multiple loop iterations when the VM lacks continue."""
    ts=lex(text); pairs=matching(ts); edits=[]; scopes={}
    for i,t in enumerate(ts):
        if t.kind!='ident' or t.value!='continue': continue
        loops=[(a,b) for a,b in pairs.items() if a<i<b and ts[a].value=='{'
               and ((b+1<len(ts) and ts[b+1].value in ('forEach','forEachReversed'))
                    or (a>0 and ts[a-1].value=='do'))]
        assert loops, ('continue outside recognized loop',t.line)
        a,b=max(loops); name=scopes.setdefault((a,b),'rowIteration'+str(len(scopes)))
        edits.append((t.offset,t.offset+len(t.value),'breakOut "'+name+'"'))
    for (a,b),name in scopes.items():
        edits.append((ts[a].offset+1,ts[a].offset+1,'call {scopeName "'+name+'";'))
        edits.append((ts[b].offset,ts[b].offset,'};'))
    for a,b,new in sorted(edits,reverse=True):text=text[:a]+new+text[b:]
    return text


def config_code(text):
    # Catalog contains finalized config field values. This does not emulate config inheritance.
    text=re.sub(r'''["']getNumber \(_x >> 'ACM_isVial'\) > 0["'] configClasses \(configFile >> "CfgWeapons"\)''',
                '(keys _catalog select {([_x,"ACM_isVial"] call _cfgRead)>0})',text)
    text=re.sub(r'configFile >> "CfgWeapons" >> (_\w+)',r'\1',text)
    text=re.sub(r'\bconfigName (_\w+)',r'\1',text)
    text=re.sub(r'\bisClass (_\w+)',r'(\1 in _catalog)',text)
    text=re.sub(r'''\b(?:getText|getNumber) \((_[A-Za-z0-9]+) >> ["']([^"']+)["']\)''',r'([\1,"\2"] call _cfgRead)',text)
    text=text.replace('_class select [_at + count _needle]', '_class select [_at + count _needle, count _class]')
    return adapt(map_defaults(iteration_scopes(text)))


def fn(name):return 'ACME_fnc_'+name+'={'+config_code((F/('fn_'+name+'.sqf')).read_text())+'};'


def registry_setup():
    native=(ROOT/'addons/circulation/functions/fnc_setLocalUiState.sqf').read_text()
    # Execute the entire initializer, not a mock accepting its incoming argument shape.
    return '''
        private _mapDefault={params ["_map","_args"];_args params ["_k","_default"];if (_k in _map) then {_map get _k} else {_default}};
        private _catalog=createHashMapFromArray [
            ["ACM_Vial_Ketamine",["Ketamine","ket.paa",1]],
            ["ACM_Vial_Fentanyl",["Fentanyl","fent.paa",1]],
            ["ACM_Ampule_Dimercaprol",["Dimercaprol","dim.paa",1]],
            ["ACM_Vial_EpinephrineCardiac",["Old epi","old.paa",1]],
            ["ACME_Vial_EpinephrineCardiac",["Cardiac epi","epi.paa",1]],
            ["THIRD_Vial_Drug_With_Suffix",["Foreign medicine","foreign.paa",1]],
            ["ACM_Vial_EmptyLabel",["","",1]],
            ["NotAVial",["Not a vial","wrong.paa",0]]
        ];
        private _cfgRead={params ["_class","_field"];
            private _row=[_catalog,[_class,["","",0]]] call _mapDefault;
            _row select (["displayName","picture","ACM_isVial"] find _field)};
        private _resolvedHolder=_medic;
        private _selfCounts=createHashMap;private _patientCounts=createHashMap;
        private _countReads=[];
        ACME_fnc_vialHolder={_resolvedHolder};
        ace_common_fnc_getCountOfItem={params ["_h","_c"]; _countReads pushBack [_h,_c];
            [if (_h isEqualTo _medic) then {_selfCounts} else {_patientCounts},[_c,0]] call _mapDefault};
        private _holderPerson=true;private _cargo=[[],[]];
        _medic setVariable ["ACME_infusion_openVials",createHashMap];
        _patient setVariable ["ACME_infusion_openVials",createHashMap];
    '''+'ACM_circulation_fnc_setLocalUiState={'+adapt(native,'circulation')+'};'+fn('itemCount')+fn('vialClass')+fn('vialMedication')+fn('initMedicationRegistry')+fn('restoreMedicationList')+fn('medicationSourceRows')+\
        'ACME_fnc_vialItemCount={'+config_code((F/'fn_vialItemCount.sqf').read_text().replace('_holder isKindOf "CAManBase"','_holderPerson').replace('getItemCargo _holder','_cargo'))+'};'


@pytest.mark.parametrize('initial',[
    '[]', '["ACM_Vial_Ketamine","ACM_Vial_EpinephrineCardiac"]',
    '["THIRD_Vial_Drug_With_Suffix","ACME_Vial_EpinephrineCardiac"]'])
def test_initializer_publishes_real_native_catalog_and_snapshot(initial):
    execute(registry_setup()+f'missionNamespace setVariable ["ACM_circulation_MedicationVialList",{initial}];'+'''
        call ACME_fnc_initMedicationRegistry;
        private _live=missionNamespace getVariable ["ACM_circulation_MedicationVialList",[]];
        private _full=missionNamespace getVariable ["ACME_medicationVialRegistryFull",[]];
        [_live isEqualTo _full && {count _live>0},"initializer failed to publish native registry"] call _check;
        ["ACME_Vial_EpinephrineCardiac" in _live && {!("ACM_Vial_EpinephrineCardiac" in _live)},"deprecated epi registry alias retained"] call _check;
        [!("NotAVial" in _live),"non-vial in registry"] call _check;
        private _saved=+_full;
        _live set [0,"external mutation"];
        [(missionNamespace getVariable "ACME_medicationVialRegistryFull") isEqualTo _saved,"live registry mutated immutable snapshot"] call _check;
        [count _countReads==0,"initialization consumed/read selected inventory"] call _check;
    ''')


@pytest.mark.parametrize('damage',['[]','["ForeignOnly"]','["ACM_Vial_EpinephrineCardiac"]'])
def test_restore_repairs_the_real_native_registry_without_mutating_snapshot(damage):
    execute(registry_setup()+'''
        private _full=["ACM_Vial_Ketamine","THIRD_Vial_Drug_With_Suffix","ACME_Vial_EpinephrineCardiac"];
        missionNamespace setVariable ["ACME_medicationVialRegistryFull",+_full];
    '''+f'missionNamespace setVariable ["ACM_circulation_MedicationVialList",{damage}];'+'''
        ACME_infusion_savedMedicationVials=["obsolete"];
        call ACME_fnc_restoreMedicationList;
        private _live=missionNamespace getVariable ["ACM_circulation_MedicationVialList",[]];
        [_live isEqualTo _full,"restore did not repair native registry"] call _check;
        _live set [0,"changed"];
        [(missionNamespace getVariable "ACME_medicationVialRegistryFull") isEqualTo _full,"restored list aliases snapshot"] call _check;
        [isNil "ACME_infusion_savedMedicationVials","retired saved list not cleared"] call _check;
    ''')


def test_empty_snapshot_does_not_erase_a_valid_live_registry():
    execute(registry_setup()+'''
        missionNamespace setVariable ["ACM_circulation_MedicationVialList",["ForeignOnly"]];
        missionNamespace setVariable ["ACME_medicationVialRegistryFull",[]];
        call ACME_fnc_restoreMedicationList;
        [(missionNamespace getVariable "ACM_circulation_MedicationVialList") isEqualTo ["ForeignOnly"],"empty snapshot erased registry"] call _check;
    ''')


def row_setup():
    return registry_setup()+'''
        missionNamespace setVariable ["ACM_circulation_MedicationVialList",keys _catalog];
        missionNamespace setVariable ["ACME_medicationVialRegistryFull",keys _catalog];
        private _getRows={[_this] call ACME_fnc_medicationSourceRows};
    '''


@pytest.mark.parametrize('holder',['_medic','_patient','objNull'])
def test_rows_follow_selected_inventory_and_never_manufacture_stock(holder):
    execute(row_setup()+f'_resolvedHolder={holder};'+'''
        _selfCounts set ["ACM_Vial_Ketamine",2];
        _patientCounts set ["ACM_Vial_Fentanyl",1];
        private _rows=false call _getRows;
    '''+f'private _expected={"[\"Ketamine\"]" if holder=="_medic" else "[\"Fentanyl\"]" if holder=="_patient" else "[]"};'+'''
        [(_rows apply {_x select 1}) isEqualTo _expected,"rows used wrong inventory or ghost stock"] call _check;
        { [(_x select 0) isEqualTo _resolvedHolder,"counted stock from another holder"] call _check; } forEach _countReads;
        [(_selfCounts get "ACM_Vial_Ketamine")==2 && {(_patientCounts get "ACM_Vial_Fentanyl")==1},"row read consumed stock"] call _check;
    ''')


@pytest.mark.parametrize('live,snapshot',[
    ('[]','[]'),('[]','["ACM_Vial_Ketamine"]'),
    ('["ACM_Vial_Ketamine","ACM_Vial_Ketamine",42,""]','["ACM_Vial_Ketamine","Missing"]')])
def test_catalog_fallbacks_and_duplicate_entries_do_not_change_medication_identity(live,snapshot):
    execute(row_setup()+f'missionNamespace setVariable ["ACM_circulation_MedicationVialList",{live}];missionNamespace setVariable ["ACME_medicationVialRegistryFull",{snapshot}];'+'''
        _selfCounts set ["ACM_Vial_Ketamine",1];
        _selfCounts set ["NotAVial",9];
        private _before=+(missionNamespace getVariable "ACM_circulation_MedicationVialList");
        private _rows=false call _getRows;
        [_rows isEqualTo [["Ketamine","Ketamine","ket.paa","ACM_Vial_Ketamine"]],"fallback/duplicate changed row identity"] call _check;
        [(missionNamespace getVariable "ACM_circulation_MedicationVialList") isEqualTo _before,"row read rewrote global catalog"] call _check;
    ''')


@pytest.mark.parametrize('source',['legacy','extended','both','partial'])
def test_epinephrine_alias_is_one_row_with_canonical_presentation(source):
    changes={'legacy':'_selfCounts set ["ACM_Vial_EpinephrineCardiac",1];',
             'extended':'_selfCounts set ["ACME_Vial_EpinephrineCardiac",1];',
             'both':'_selfCounts set ["ACM_Vial_EpinephrineCardiac",1];_selfCounts set ["ACME_Vial_EpinephrineCardiac",2];',
             'partial':'_medic setVariable ["ACME_infusion_openVials",createHashMapFromArray [["EpinephrineCardiac",0.5]]];'}
    execute(row_setup()+changes[source]+'''
        private _rows=false call _getRows;
        [_rows isEqualTo [["Cardiac epi","EpinephrineCardiac","epi.paa","ACME_Vial_EpinephrineCardiac"]],"epi alias duplicated or mislabeled"] call _check;
    ''')


@pytest.mark.parametrize('amount,visible',[(0,False),(0.000001,False),(0.01,True),(2,True)])
def test_open_partial_survives_consumed_physical_item_without_zero_volume_ghosts(amount,visible):
    execute(row_setup()+f'_medic setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",{amount}]]];'+
        'private _rows=false call _getRows;'+f'[count _rows=={int(visible)},"partial-vial membership incorrect"] call _check;')


def test_ampule_and_foreign_keys_keep_their_full_identity_across_refreshes():
    execute(row_setup()+'''
        { _selfCounts set [_x,1]; } forEach ["THIRD_Vial_Drug_With_Suffix","ACM_Ampule_Dimercaprol","ACM_Vial_Ketamine"];
        private _rows=false call _getRows;
        [count _rows==3,"medication count changed"] call _check;
        [["Dimercaprol","Dimercaprol","dim.paa","ACM_Ampule_Dimercaprol"] in _rows,"ampule identity changed"] call _check;
        [["Foreign medicine","Drug_With_Suffix","foreign.paa","THIRD_Vial_Drug_With_Suffix"] in _rows,"foreign suffix/class changed"] call _check;
        [["Ketamine","Ketamine","ket.paa","ACM_Vial_Ketamine"] in _rows,"native identity changed"] call _check;
        for "_i" from 1 to 4 do {[(false call _getRows) isEqualTo _rows,"refresh changes identity/order"] call _check;};
    ''')


def test_blank_label_and_unknown_open_vial_use_medication_key_fallback():
    execute(row_setup()+'''
        _selfCounts set ["ACM_Vial_EmptyLabel",1];
        _medic setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Unknown_Open",1]]];
        private _rows=false call _getRows;
        [(_rows apply {_x select 0}) isEqualTo ["EmptyLabel","Unknown_Open"],"blank/unknown labels not recoverable"] call _check;
        { [count _x==4 && {(_x findIf {!(_x isEqualType "")})<0},"malformed row"] call _check; } forEach _rows;
    ''')


@pytest.mark.parametrize('infusion',[False,True])
def test_infusion_filter_uses_current_allow_lists_without_mutating_global_catalog(infusion):
    execute(row_setup()+'''
        { _selfCounts set [_x,1]; } forEach ["ACM_Vial_Ketamine","ACM_Vial_Fentanyl","ACM_Ampule_Dimercaprol","THIRD_Vial_Drug_With_Suffix"];
        missionNamespace setVariable ["ACME_infusion_allowedMedications",["Ketamine"]];
        missionNamespace setVariable ["ACME_infusion_allowedVials",["ACM_Vial_Fentanyl"]];
        missionNamespace setVariable ["ACME_infusion_syringeExtraDrawItems",["THIRD_Vial_Drug_With_Suffix"]];
        private _before=+(missionNamespace getVariable "ACM_circulation_MedicationVialList");
    '''+f'private _rows={str(infusion).lower()} call _getRows;'+
        f'[count _rows=={3 if infusion else 4},"infusion allow list incorrect"] call _check;'+'''
        [(missionNamespace getVariable "ACM_circulation_MedicationVialList") isEqualTo _before,"infusion filtering replaced global registry"] call _check;
    ''')


def test_vehicle_rows_use_cargo_counts_not_the_provider_inventory():
    execute(row_setup()+'''
        _holderPerson=false;_resolvedHolder=_patient;_cargo=[["ACM_Vial_Fentanyl"],[3]];
        _selfCounts set ["ACM_Vial_Ketamine",4];
        private _rows=false call _getRows;
        [(_rows apply {_x select 1}) isEqualTo ["Fentanyl"],"vehicle used personal inventory"] call _check;
        [count _countReads==0,"vehicle used ACE person counter"] call _check;
    ''')


def test_native_sort_delegation_is_retained_without_an_index_remap():
    # SQF-VM leaves these nested string rows unordered; do not change production
    # sorting or substitute a Python sort merely to claim alphabetical execution.
    text=(F/'fn_medicationSourceRows.sqf').read_text()
    assert '_rows sort true;' in text
    assert not any(t.value=='_forEachIndex' for t in lex(text))


def listbox_code(text):
    """Represent only the listbox/control engine primitives for one real control."""
    text=text.replace('focusedCtrl _display','_focusedCtrl').replace('ctrlIDC _durationFocus','_focusedId')
    text=text.replace('_display displayCtrl 84006','_listCtrl')
    text=text.replace('lbSize _list','(count _listRecords)').replace('lbCurSel _list','_selected')
    text=text.replace('lbClear _list;', '_listRecords=[]; _selected=-1; _clears=_clears+1;')
    for op,index in [('lbData',1),('lbText',0),('lbPicture',2),('lbValue',5)]:
        text=re.sub(r'_list '+op+r' (_\w+)',lambda m:f'([{m[1]},{index}] call _lbGet)',text)
    text=text.replace('_list lbAdd _label','([_label] call _lbAdd)')
    text=text.replace('_list lbSetCurSel _i;', '_selected=_i;')
    text=text.replace('_list ctrlShow false;', '_shown=false;')
    tokens=lex(text); pairs=matching(tokens); edits=[]
    for i,t in enumerate(tokens):
        if t.kind!='ident' or t.value not in ('lbSetData','lbSetPicture','lbSetTooltip','lbSetTextRight'):continue
        assert tokens[i-1].value=='_list' and tokens[i+1].value=='['
        end=pairs[i+1]
        index={'lbSetData':1,'lbSetPicture':2,'lbSetTooltip':3,'lbSetTextRight':4}[t.value]
        args=text[tokens[i+1].offset:tokens[end].offset+1]
        edits.append((tokens[i-1].offset,tokens[end].offset+1,'['+args+','+str(index)+'] call _lbSet'))
    for a,b,new in reversed(edits):text=text[:a]+new+text[b:]
    return config_code(text)


def ui_setup():
    sync=(F/'fn_skMedicationSync.sqf').read_text()
    return row_setup()+'''
        private _display=missionNamespace;private _d=_display;private _listCtrl=_patient;
        private _focusedCtrl=objNull;private _focusedId=-1;
        private _listRecords=[];private _selected=-1;private _clears=0;private _shown=true;private _stockCalls=0;
        private _lbGet={params ["_i","_field"];if (_i<0 || {_i>=count _listRecords}) exitWith {""};(_listRecords select _i) param [_field,""]};
        private _lbSet={params ["_args","_field"];_args params ["_i","_value"];(_listRecords select _i) set [_field,_value];};
        private _lbAdd={_listRecords pushBack [_this select 0,"","","","",0];count _listRecords-1};
        ACME_fnc_skMedicationStockRefresh={_stockCalls=_stockCalls+1;};
    '''+'ACME_fnc_skMedicationSync={'+listbox_code(sync)+'};'


def test_native_sync_rebuilds_empty_selector_once_and_preserves_each_medication():
    execute(ui_setup()+'''
        _selfCounts set ["ACM_Vial_Ketamine",2];_selfCounts set ["ACM_Vial_Fentanyl",1];
        private _rows=[_display] call ACME_fnc_skMedicationSync;
        [count _rows==2 && {_clears==1},"empty backing selector not rebuilt"] call _check;
        [(_listRecords apply {_x select 1}) isEqualTo (_rows apply {_x select 1}),"selector identity differs from source"] call _check;
        [(_listRecords apply {_x select 0}) isEqualTo (_rows apply {_x select 0}),"selector labels differ from source"] call _check;
        [(_listRecords apply {_x select 2}) isEqualTo (_rows apply {_x select 2}),"selector artwork differs from source"] call _check;
        [(_display getVariable ["ACME_SK_MedicationRows",[]]) isEqualTo _rows,"metadata cache differs from returned rows"] call _check;
        for "_i" from 1 to 4 do {[_display] call ACME_fnc_skMedicationSync;};
        [_clears==1 && {_stockCalls==5} && {!_shown},"unchanged refresh rebuilds or exposes backing list"] call _check;
    ''')


@pytest.mark.parametrize('old_index',[0,1])
def test_sync_restores_selection_by_medication_key_not_row_index(old_index):
    execute(ui_setup()+f'_selected={old_index};'+'''
        _listRecords=[["old F","Fentanyl","old"],["old K","Ketamine","old"]];
        private _key=(_listRecords select _selected) select 1;
        private _input=[["Ketamine","Ketamine","ket.paa","ACM_Vial_Ketamine"],["Fentanyl","Fentanyl","fent.paa","ACM_Vial_Fentanyl"]];
        ACME_fnc_medicationSourceRows={_input};
        [_display] call ACME_fnc_skMedicationSync;
        [_selected>=0 && {((_listRecords select _selected) select 1)==_key},"selection followed row index instead of drug"] call _check;
        [_clears==1,"changed list not rebuilt"] call _check;
    ''')


def test_sync_normalizes_missing_or_wrongly_typed_fields_and_rejects_invalid_identities():
    execute(ui_setup()+'''
        private _input=["not a row",9,[],["", "", "", ""],[9,9,9,"ACM_Vial_Ketamine"],["","Unknown","", "Missing"],[false,"Fentanyl",false,false]];
        ACME_fnc_medicationSourceRows={_input};
        private _rows=[_display] call ACME_fnc_skMedicationSync;
        [_rows isEqualTo [["Ketamine","Ketamine","ket.paa","ACM_Vial_Ketamine"],["Unknown","Unknown","","Missing"],["Fentanyl","Fentanyl","",""]],"normalization changed medication or left malformed fields"] call _check;
        [count _listRecords==3,"bad rows reached native control"] call _check;
    ''')


@pytest.mark.parametrize('return_state',['[]','["bag"]'])
def test_sync_passes_its_actual_prep_infusion_context_to_the_row_builder(return_state):
    execute(ui_setup()+f'_display setVariable ["ACME_SK_Return",{return_state}];'+'''
        private _mode=[];ACME_fnc_medicationSourceRows={_mode=+_this;[]};
        [_display] call ACME_fnc_skMedicationSync;
    '''+f'[_mode isEqualTo [{str(return_state!="[]").lower()}],"wrong prep mode passed"] call _check;')


def visible_setup():
    text=(F/'fn_skListRefresh.sqf').read_text()
    start=text.index('    private _specs = [];')
    end=text.index('    private _rows = _group getVariable',start)
    return ui_setup()+'''private _kind="medication";private _list=_listCtrl;'''+\
        'private _bind={'+listbox_code(text[start:end])+'_specs};'


@pytest.mark.parametrize('native',[
    '[]',
    '[["Fentanyl native","Fentanyl",""],["duplicate","Fentanyl","bad.paa"],["","Ketamine",""]]',
    '[["","Ketamine",""]]'])
def test_visible_rows_bind_metadata_by_key_and_recover_missing_backing_entries(native):
    execute(visible_setup()+'''
        private _meta=[["Ketamine","Ketamine","ket.paa","ACM_Vial_Ketamine"],["Fentanyl","Fentanyl","fent.paa","ACM_Vial_Fentanyl"]];
        _display setVariable ["ACME_SK_MedicationRows",_meta];
    '''+f'_listRecords={native};'+'''
        private _rows=call _bind;
        [count _rows==2,"visible duplicate or missing medication"] call _check;
        {
            private _med=_x select 1;
            private _row=_rows select (_rows findIf {(_x select 1)==_med});
            [(_row select 4)==(_x select 3),"physical vial rebound by index"] call _check;
            [(_row select 3)==(_x select 2),"artwork did not follow medication key"] call _check;
            [(_row select 0)!="","blank visible label"] call _check;
        } forEach _meta;
    ''')


def test_visible_rows_keep_native_labels_but_recover_blank_labels_from_metadata():
    execute(visible_setup()+'''
        _display setVariable ["ACME_SK_MedicationRows",[["K fallback","Ketamine","ket.paa","ACM_Vial_Ketamine"],["","Unknown","",""]]];
        _listRecords=[["Live K","Ketamine","ket.paa"]];
        private _rows=call _bind;
        [(_rows select 0) select 0 == "Live K","valid native display label was replaced"] call _check;
        [(_rows select 1) select 0 == "Unknown","missing native/meta label did not fall back to key"] call _check;
        [(_rows select 1) select 4 == "","metadata physical-class policy changed"] call _check;
    ''')


def test_stock_preview_uses_reserved_volume_and_the_rows_exact_physical_class():
    text=(F/'fn_skListRefresh.sqf').read_text()
    start=text.index('private _fnStockInfo = ')+len('private _fnStockInfo = ')
    tokens=lex(text);pairs=matching(tokens);i=next(i for i,t in enumerate(tokens) if t.offset==start)
    body=text[start:tokens[pairs[i]].offset+1]
    execute(ui_setup()+'''
        private _holder=_patient;private _previewCalls=[];
        ACME_fnc_vialPreview={_previewCalls pushBack _this;[2,4,0,14]};
        ACME_fnc_vialSession={throw "unexpected bound-session branch"};
        _d setVariable ["ACME_SK_VialSessions",createHashMap];
    '''+'private _stock='+config_code(body)+';'+'''
        private _result=["Drug_With_Suffix",3,"THIRD_Vial_Drug_With_Suffix"] call _stock;
        [_previewCalls isEqualTo [[_patient,"Drug_With_Suffix",3,"THIRD_Vial_Drug_With_Suffix"]],"stock preview used another inventory/class or lost reservation"] call _check;
        [_result isEqualTo ["4.00 mL",2,4,14,"x02"],"stock rendering data changed"] call _check;
    ''')


def test_preview_builder_is_synced_before_visible_metadata_is_consumed():
    text=(F/'fn_skListRefresh.sqf').read_text()
    assert text.index('[_d] call ACME_fnc_skMedicationSync;')<text.index('private _metaRows =')
    # Labels may come from the current native row, but physical identity joins by medication key.
    assert '(_x param [1, ""]) == _data' in text
    assert '[_data, _reserved, _item] call _fnStockInfo' in text
