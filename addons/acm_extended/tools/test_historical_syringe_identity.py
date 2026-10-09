"""Batch 8: execute stored-syringe identity, metadata and lifecycle contracts.

The real SQF writers/resolvers run. Display/control primitives, inventory and
engine event delivery are explicit fixtures. No rendering, Unicode grapheme
measurement, real event inheritance or late preparation callbacks are simulated.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute
from test_historical_medication_rows import iteration_scopes

F=ROOT/'addons/acm_extended/functions'


def source(name):return (F/('fn_'+name+'.sqf')).read_text()


def code(text):
    # Provider objects are namespace stand-ins; locality and public replication are engine boundaries.
    text=text.replace('local _owner', 'true').replace('local _unit', 'true')
    text=text.replace('_owner setVariable ["ACME_narcStore", _store, _public]', '_owner setVariable ["ACME_narcStore", _store]')
    text=text.replace('findDisplay 84000','_drawDisplay')
    text=re.sub(r'_d displayCtrl\s*(\([^\n]+?\)|\d+)',r'\1',text)
    text=text.replace('(ctrlText _ctrl)','([_ctrl] call _readText)')
    text=text.replace('ctrlText ((84601 + _i))','([(84601 + _i)] call _readText)')
    text=text.replace('_ctrl ctrlSetText _t;','[_ctrl,_t] call _writeText;')
    text=text.replace('((84601 + _i)) ctrlSetText _t;','[(84601 + _i),_t] call _writeText;')
    text=text.replace('_c lbData _row','_chosenColor')
    text=text.replace('_c lbSetCurSel -1;','_listReset=-1;')
    text=text.replace('_c ctrlShow false;','_listShown=false;')
    text=text.replace('ctrlSetFocus _focusCtrl;','_focusIds pushBack _focusCtrl;')
    return adapt(iteration_scopes(text))


def function(name):return 'ACME_fnc_'+name+'={'+code(source(name))+'};\n'


def setup():
    return '''
        private _drawDisplay=missionNamespace;
        private _refreshes=0; private _hotspots=0; private _renders=0;
        private _opens=[]; private _focusIds=[];
        private _textValues=createHashMap; private _textWrites=[];
        private _readText={params ["_id"]; private _key=str _id; if (_key in _textValues) then {_textValues get _key} else {""}};
        private _writeText={params ["_id","_value"]; _textWrites pushBack _this; _textValues set [str _id,_value];};
        private _chosenColor="none"; private _listReset=9; private _listShown=true;
        ACME_fnc_skRefreshDrawn={_refreshes=_refreshes+1;};
        ACME_fnc_skBuildHotspots={_hotspots=_hotspots+1;};
        ACME_fnc_skCarouselRender={_renders=_renders+1;};
        ACME_fnc_skOpenDraw={_opens pushBack _this;};
        private _a=["Ketamine",10,2,"label A",0,[["Ketamine",2]],"compoundB13","none","","","","id-a","barrel-a"];
        private _b=["Propofol",5,1,"label B",0,[],"","none","","","","id-b","barrel-b"];
        private _c=["EpinephrineCardiac",10,1,"label C",9,[],"epiMixB12","none","","","","id-c","flush"];
        private _rows=[_a,_b,_c];
        _medic setVariable ["ACME_narcStore",+_rows];
        _patient setVariable ["ACME_narcStore",[["patient kit"]]];
    '''+''.join(function(n) for n in ('narcStoreCommit','skStoreEnsureIds','skSelectedIndex','skSelectStored',
        'skAfterStoredRemoval','skOpenStoredSyringe','skApplyPendingTag','skTagCommit','skPendingTagCommit','skTagColor','skSyringeRemembered'))


def test_legacy_and_duplicate_records_gain_unique_ids_without_losing_payload():
    execute(setup()+'''
        private _legacy=["Fentanyl",3,1,"old label",0,[],"","blue_opioid","line1","line2","line3"];
        private _duplicate=+_b; _duplicate set [11,"id-a"];
        private _before=[+_a,+_legacy,+_duplicate];
        [_medic,+_before] call ACME_fnc_narcStoreCommit;
        private _after=[_medic] call ACME_fnc_skStoreEnsureIds;
        private _ids=_after apply {_x select 11};
        [count (_ids arrayIntersect _ids)==3,"duplicate stable IDs"] call _check;
        [(_ids select 0)=="id-a","existing valid identity changed"] call _check;
        for "_i" from 0 to 2 do {
            [((_after select _i) select [0,11]) isEqualTo ((_before select _i) select [0,11]),"normalization changed drug/tag payload"] call _check;
        };
        private _serial=_medic getVariable ["ACME_narcStoreSerial",0];
        [([_medic] call ACME_fnc_skStoreEnsureIds) isEqualTo _after,"second normalization changed identity"] call _check;
        [(_medic getVariable ["ACME_narcStoreSerial",0])==_serial,"repeat normalization consumed serials"] call _check;
        [(_patient getVariable ["ACME_narcStore",[]]) isEqualTo [["patient kit"]],"normalization changed another kit"] call _check;
    ''')


@pytest.mark.parametrize('selector',[0,1,2,3,8])
def test_numeric_selection_wraps_and_mirrors_one_stable_identity(selector):
    execute(setup()+f'private _index=[{selector},_rows] call ACME_fnc_skSelectStored;'+f'[_index=={selector%3},"incorrect wrap"] call _check;'+'''
        [(uiNamespace getVariable ["ACME_SK_SelectedSyringeId",""])==((_rows select _index) select 11),"wrong stable ID"] call _check;
        [(uiNamespace getVariable ["ACME_SK_SelDrawn",-1])==_index && {(uiNamespace getVariable ["ACME_SK_CarouselIdx",-1])==_index},"presentation mirrors disagree"] call _check;
    ''')


@pytest.mark.parametrize('order',['[_c,_a,_b]','[_b,_c,_a]','[_a,_b,_c]'])
def test_selection_follows_identity_after_store_reordering(order):
    execute(setup()+'''["id-b",_rows] call ACME_fnc_skSelectStored;'''+f'private _changed={order};'+'''
        [_medic,_changed] call ACME_fnc_narcStoreCommit;
        private _index=[_changed,false] call ACME_fnc_skSelectedIndex;
        [((_changed select _index) select 11)=="id-b","selection drifted to another medication"] call _check;
    ''')


@pytest.mark.parametrize('fallback',[True,False])
def test_missing_selected_identity_requires_explicit_fallback(fallback):
    execute(setup()+'''["id-b",_rows] call ACME_fnc_skSelectStored; [_medic,[_a,_c]] call ACME_fnc_narcStoreCommit;'''+
        f'private _index=[[_a,_c],{str(fallback).lower()}] call ACME_fnc_skSelectedIndex;'+
        f'[_index=={1 if fallback else -1},"wrong missing-ID result"] call _check;'+
        f'[(uiNamespace getVariable ["ACME_SK_SelectedSyringeId",""])=="{"id-c" if fallback else "id-b"}","implicit identity reassignment"] call _check;')


@pytest.mark.parametrize('old,remaining,expected',[(0,'[_b,_c]','id-b'),(1,'[_a,_c]','id-c'),(2,'[_a,_b]','id-b'),(0,'[]','')])
def test_removal_selects_nearest_and_clears_only_injection_transients(old,remaining,expected):
    execute(setup()+'''
        uiNamespace setVariable ["ACME_SK_SiteIdx",3]; uiNamespace setVariable ["ACME_SK_EpiDoseChoice",2];
        uiNamespace setVariable ["ACME_SK_SelFlush","flush"]; uiNamespace setVariable ["ACME_SK_PendingInjection",["old"]];
        uiNamespace setVariable ["ACME_SK_DiscardArmedId","old"]; uiNamespace setVariable ["ACME_SK_View","body"];
    '''+f'[_medic,{remaining}] call ACME_fnc_narcStoreCommit; [{old}] call ACME_fnc_skAfterStoredRemoval;'+
        f'[(uiNamespace getVariable ["ACME_SK_SelectedSyringeId","bad"])=="{expected}","wrong next syringe"] call _check;'+'''
        [(uiNamespace getVariable ["ACME_SK_SiteIdx",0]) == -1 && {(uiNamespace getVariable ["ACME_SK_EpiDoseChoice",9])==0},"old site/dose retained"] call _check;
        [(uiNamespace getVariable ["ACME_SK_SelFlush","bad"])=="" && {(uiNamespace getVariable ["ACME_SK_PendingInjection",[1]]) isEqualTo []},"old injection retained"] call _check;
        [(uiNamespace getVariable ["ACME_SK_DiscardArmedId","bad"])=="","discard authorization leaked"] call _check;
        [_refreshes==1 && {_hotspots==1},"body binding not refreshed once"] call _check;
        [(_patient getVariable ["ACME_narcStore",[]]) isEqualTo [["patient kit"]],"other kit changed"] call _check;
    ''')


@pytest.mark.parametrize('size,expected',[(1,1),(3,3),(5,5),(10,10),(2,10),(0,10)])
def test_self_menu_open_uses_stable_id_and_native_size(size,expected):
    execute(setup()+f'_b set [1,{size}]; [_medic,[_c,_a,_b]] call ACME_fnc_narcStoreCommit; ["id-b"] call ACME_fnc_skOpenStoredSyringe;'+
        f'[_opens isEqualTo [[{expected}]],"wrong native draw size"] call _check;'+'''
        [(uiNamespace getVariable ["ACME_SK_OpenCarouselId",""])=="id-b","open request used a stale index"] call _check;
    ''')


def test_stale_self_menu_callback_cannot_open_a_different_syringe():
    execute(setup()+function('skSyringeSelfMenu')+'''
        ace_interact_menu_fnc_createAction={_this}; ACME_fnc_skSyringeSummary={"summary"};
        private _menu=[_medic,_medic,[]] call ACME_fnc_skSyringeSelfMenu;
        private _action=(_menu select 1) select 0;
        [_medic,[_c,_b,_a]] call ACME_fnc_narcStoreCommit;
        [_medic,_medic,_action select 6] call (_action select 3);
        [(uiNamespace getVariable ["ACME_SK_SelectedSyringeId",""])=="id-b","reordered menu opened wrong syringe"] call _check;
        [_medic,[_c,_a]] call ACME_fnc_narcStoreCommit;
        [_medic,_medic,_action select 6] call (_action select 3);
        [count _opens==1,"stale menu opened replacement syringe"] call _check;
    ''')


@pytest.mark.parametrize('color',['none','yellow_induction','red_paralytic'])
@pytest.mark.parametrize('length',[0,12,25,30])
def test_pending_tag_limits_three_lines_and_preserves_drug_id_and_barrel(color,length):
    value='X'*length; clipped='X'*min(length,25)
    execute(setup()+f'uiNamespace setVariable ["ACME_SK_PendingTagColor","{color}"]; uiNamespace setVariable ["ACME_SK_PendingTagText",["{value}","Mixed Case","<tag>"]];'+'''
        private _out=[_c] call ACME_fnc_skApplyPendingTag;
        [(_out select [0,7]) isEqualTo (_c select [0,7]) && {(_out select [11,2]) isEqualTo (_c select [11,2])},"tag edit changed medication/ID/barrel"] call _check;
    '''+f'[(_out select [7,4]) isEqualTo ["{color}","{clipped}","Mixed Case","<tag>"],"tag truncation or content changed"] call _check;'+'''
        [(_c select 7)=="none" && {(_c select 8)==""},"apply mutated original row"] call _check;
    ''')


@pytest.mark.parametrize('color,lines,expected',[(5,'"bad"','["none","","",""]'),('"none"','["short",9]','["none","short","",""]')])
def test_pending_tag_rejects_wrong_metadata_types_without_altering_drug(color,lines,expected):
    execute(setup()+f'uiNamespace setVariable ["ACME_SK_PendingTagColor",{color}]; uiNamespace setVariable ["ACME_SK_PendingTagText",{lines}];'+
        f'private _out=[_a] call ACME_fnc_skApplyPendingTag; [(_out select [7,4]) isEqualTo {expected},"unsafe tag types survived"] call _check;')


@pytest.mark.parametrize('editing',[True,False])
def test_editing_updates_only_selected_tag_without_repainting_active_editor(editing):
    execute(setup()+'''["id-b",_rows] call ACME_fnc_skSelectStored; [_medic,[_c,_a,_b]] call ACME_fnc_narcStoreCommit;
        _textValues set ["84460","123456789012345678901234567890"]; _textValues set ["84461","Case Preserved"]; _textValues set ["84462","third"];
    '''+f'uiNamespace setVariable ["ACME_SK_TagEditMode",{str(editing).lower()}]; call ACME_fnc_skTagCommit;'+'''
        private _store=_medic getVariable ["ACME_narcStore",[]]; private _selected=_store select 2;
        [(_store select [0,2]) isEqualTo [_c,_a],"typing changed other syringes"] call _check;
        [(_selected select [8,3]) isEqualTo ["1234567890123456789012345","Case Preserved","third"],"wrong editor target or length"] call _check;
        [(_selected select [0,8]) isEqualTo (_b select [0,8]) && {(_selected select [11,2]) isEqualTo (_b select [11,2])},"typing changed dose/color/ID"] call _check;
        [count _textWrites==1,"unchanged fields were rewritten"] call _check;
    '''+f'[_refreshes=={int(not editing)} && {{_renders==0}},"editing forced caret-destroying repaint"] call _check;')


@pytest.mark.parametrize('absent',['display','selection'])
def test_tag_commit_cannot_write_when_display_or_selected_record_is_gone(absent):
    execute(setup()+'''["id-b",_rows] call ACME_fnc_skSelectStored;'''+
        ('_drawDisplay=objNull;' if absent=='display' else '[_medic,[_a,_c]] call ACME_fnc_narcStoreCommit;')+'''
        private _before=+(_medic getVariable ["ACME_narcStore",[]]); call ACME_fnc_skTagCommit;
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo _before,"stale editor changed a different record"] call _check;
        [_refreshes==0 && {count _textWrites==0},"stale editor rewrote controls"] call _check;
    ''')


@pytest.mark.parametrize('chosen',['','none','blue_opioid'])
def test_tag_color_uses_selected_identity_without_changing_text_or_dose(chosen):
    execute(setup()+'''["id-b",_rows] call ACME_fnc_skSelectStored; [_medic,[_b,_a,_c]] call ACME_fnc_narcStoreCommit;'''+
        f'_chosenColor="{chosen}"; [100,0] call ACME_fnc_skTagColor;'+'''
        private _store=_medic getVariable ["ACME_narcStore",[]]; private _row=_store select 0;
        [(_row select [0,7]) isEqualTo (_b select [0,7]) && {(_row select [8,5]) isEqualTo (_b select [8,5])},"color changed dose/text/ID"] call _check;
        [(_store select [1,2]) isEqualTo [_a,_c],"color changed other rows"] call _check;
        [_listReset == -1 && {!_listShown} && {_renders==1},"color list did not reset once"] call _check;
    '''+f'[(_row select 7)=="{chosen or "none"}","wrong stored color"] call _check;')


@pytest.mark.parametrize('event',['Killed','Respawn'])
def test_personal_lifecycle_clears_kit_and_selection_but_not_patient_equipment(event):
    text=source('registerSyringeLifecycleRuntime').replace('hasInterface','_interface').replace('player addEventHandler','_lifeHandlers pushBack')
    # Respawn delegates to the shared fresh-kit reset; execute that dependency too.
    reset=function('openVialStoreCommit')+function('resetPersonalMedicationKit')+'ACME_fnc_vialLeaseRelease={}; ACM_core_fnc_equipmentKitChanged={};'
    execute(setup()+reset+'''private _interface=true; private _lifeHandlers=[];'''+code(text)+'''
        [count _lifeHandlers==2,"lifecycle handlers missing"] call _check;
        ["id-b",_rows] call ACME_fnc_skSelectStored; uiNamespace setVariable ["ACME_SK_SiteIdx",3];
        _medic setVariable ["ACME_thora_tube_left",true]; _medic setVariable ["ACME_hpmk_state","wrapped"];
    '''+f'private _callback=(_lifeHandlers select {{(_x select 0)=="{event}"}}) select 0; [_medic] call (_callback select 1);'+'''
        [(_medic getVariable ["ACME_narcStore",[1]]) isEqualTo [],"personal store survived life event"] call _check;
        [(uiNamespace getVariable ["ACME_SK_SelectedSyringeId","bad"])=="" && {(uiNamespace getVariable ["ACME_SK_CarouselIdx",0]) == -1} && {(uiNamespace getVariable ["ACME_SK_SelDrawn",0]) == -1},"selection not invalidated"] call _check;
        [(_patient getVariable ["ACME_narcStore",[]]) isEqualTo [["patient kit"]],"event cleared another patient's kit"] call _check;
        [_medic getVariable ["ACME_thora_tube_left",false],"event removed tube evidence"] call _check;
        [(_medic getVariable ["ACME_hpmk_state",""])=="wrapped","event removed HPMK"] call _check;
    '''+('[(uiNamespace getVariable ["ACME_SK_SiteIdx",0]) == -1,"respawn retained old site"] call _check;' if event=='Respawn' else ''))


def test_headless_machine_does_not_install_personal_kit_handlers():
    text=source('registerSyringeLifecycleRuntime').replace('hasInterface','_interface').replace('player addEventHandler','_lifeHandlers pushBack')
    execute(setup()+'''private _interface=false; private _lifeHandlers=[];'''+code(text)+'''[count _lifeHandlers==0,"non-interface machine installed personal handlers"] call _check;''')


@pytest.mark.parametrize('kind',['compound','flush'])
def test_actual_save_attaches_pending_tag_without_changing_source_funding(kind):
    from test_historical_medication_preparation import commit_setup
    execute(commit_setup()+function('skApplyPendingTag')+'''
        uiNamespace setVariable ["ACME_SK_PendingTagColor","yellow_induction"];
        uiNamespace setVariable ["ACME_SK_PendingTagText",["name","dose","time"]];
        uiNamespace setVariable ["ACME_SK_CompoundComponents",[["Ketamine",2],["Propofol",1]]];
    '''+('call ACME_fnc_skCompoundCommit;' if kind=='compound' else 'call ACME_fnc_skFlushSave;')+'''
        private _store=_medic getVariable ["ACME_narcStore",[]]; [count _store==1,"save did not create one row"] call _check;
        private _row=_store select 0;
        [(_row select [7,4]) isEqualTo ["yellow_induction","name","dose","time"],"save lost pending tag"] call _check;
        [(_row select 5) isEqualTo [["Ketamine",2],["Propofol",1]] && {(_row select 2)==3},"tag changed mixture"] call _check;
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==18 && {([_medic,"Propofol"] call ACME_fnc_infusionVialVolume)==9},"tag changed source debit"] call _check;
    ''')


@pytest.mark.parametrize('display',[True,False])
def test_pending_editor_reads_three_lines_without_rewriting_short_input(display):
    execute(setup()+('_drawDisplay=objNull;' if not display else '')+'''
        _textValues set ["84601","123456789012345678901234567890"];
        _textValues set ["84602","Mixed Case"]; _textValues set ["84603","third"];
        uiNamespace setVariable ["ACME_SK_PendingTagText",["unchanged"]];
        call ACME_fnc_skPendingTagCommit;
    '''+('''
        [(uiNamespace getVariable ["ACME_SK_PendingTagText",[]]) isEqualTo ["1234567890123456789012345","Mixed Case","third"],"pending editor lost text or exceeded limit"] call _check;
        [count _textWrites==1,"short pending text was rewritten"] call _check;
    ''' if display else '''
        [(uiNamespace getVariable ["ACME_SK_PendingTagText",[]]) isEqualTo ["unchanged"] && {count _textWrites==0},"closed editor changed pending text"] call _check;
    '''))


@pytest.mark.parametrize('index,mark,expected',[(0,'none',False),(1,'none',False),(2,'none',True),(3,'none',True),(4,'none',True),(0,'color',True),(0,'text',True),(0,'whitespace',False)])
def test_syringe_memory_is_presentation_only_and_real_tags_identify_older_records(index,mark,expected):
    mark_code={'none':'','color':'_old set [7,"blue_opioid"];','text':'_old set [8,"label"];','whitespace':'_old set [8,"   "];'}[mark]
    execute(setup()+'''private _old=+_a;'''+mark_code+'''
        private _store=[_old,+_a,+_a,+_a,+_a]; private _before=+_store;
    '''+f'private _remembered=[_store,{index}] call ACME_fnc_skSyringeRemembered;'+
        f'[_remembered isEqualTo {str(expected).lower()},"wrong memory visibility"] call _check;'+'''
        [_store isEqualTo _before,"presentation memory changed medical contents"] call _check;
    ''')
