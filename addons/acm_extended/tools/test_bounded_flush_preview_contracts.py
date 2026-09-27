"""Current shared flush preview and tag-save contracts, without rendering claims.

The full save/tag functions execute via existing inventory stand-ins. Control
prefixes record requests; no font, child overlay, live mouse or transport is simulated.
"""
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import execute
from test_bounded_tag_contracts import source, require
from test_bounded_selector_lifetime import setup as selector_setup
from test_historical_medication_preparation import commit_setup
from test_historical_syringe_identity import function


def flush_block(text):
    ts=lex(text); pairs=matching(ts)
    marker=['if','(','_flush','!=','',')','exitWith','{']
    starts=[i for i in range(len(ts)-len(marker)+1) if [t.value for t in ts[i:i+len(marker)]]==marker]
    assert len(starts)==1
    op=starts[0]+len(marker)-1
    return text[ts[op].offset:ts[pairs[op]].offset+1]


def preview_contract(body=None,move=None,render=None,hot=None):
    body=source('skBodySyringeRender') if body is None else body
    move=source('skBodySyringeMove') if move is None else move
    render=source('skCarouselRender') if render is None else render
    hot=source('skBuildHotspots') if hot is None else hot
    require(body,'call ACME_fnc_skCarouselRender;')
    require(move,'_this call ACME_fnc_skCarouselMove;')
    block=flush_block(render)
    for fragment in [
        '_bar ctrlSetText "\\acm_extended\\ui\\syringe\\syringe_flush_10_barrel_ca.paa";',
        '_hit ctrlSetTooltip "10mL Saline Flush";',
        '_tag ctrlShow false;',
        'for "_ln" from 0 to 2 do {(_d displayCtrl (_bid+4+_ln)) ctrlShow false;};',
        '_hit ctrlEnable (_hh > 4*pixelH);',
    ]:require(block,fragment)
    require(hot,'private _deliveryReady = (_flush != "") || {_syringeIndex >= 0};')
    require(hot,'if (_flush != "") then {_route = "vascular"; uiNamespace setVariable ["ACME_SK_Route", _route];};')


def tag_save_contract(pending=None,draw=None,save=None,pick=None):
    pending=source('skPendingTagRender') if pending is None else pending
    draw=source('skWasteDraw') if draw is None else draw
    save=source('skFlushSave') if save is None else save
    pick=source('skPickFlush') if pick is None else pick
    require(pending,'private _showSetup = (_view == "syringe");')
    require(pending,'_e ctrlShow _hasTag;')
    assert any(t.kind=='string' and 'tag_overlay_%1mL_%2.paa' in t.value for t in lex(pending))
    require(draw,'_components pushBack [_med,_drugMl];')
    # Draw stages measured components. Tag attachment happens at save, not per pull.
    assert not any(t.value=='ACME_fnc_skApplyPendingTag' for t in lex(draw))
    require(save,'call ACME_fnc_skPendingTagCommit;')
    require(save,'[ACE_player,_components,_flushClass,true] call ACME_fnc_medicationTakeSources')
    require(save,'private _entry=[[_primary,_cap,_totalDrug,_label,_nsMl,_components,"dilutionB13"]] call ACME_fnc_skApplyPendingTag;')
    require(save,'_entry set [12,"flush"];')
    require(save,'[ACE_player, _store] call ACME_fnc_narcStoreCommit;')
    tokens=[t.value for t in lex(save)]
    assert tokens.index('ACME_fnc_skPendingTagCommit')<tokens.index('ACME_fnc_skApplyPendingTag')<tokens.index('ACME_fnc_narcStoreCommit')
    require(pick,'[10, _patient, _bodyPart, _flushClass]')


@pytest.mark.parametrize('color',['none','white_saline_flush','yellow_induction'])
@pytest.mark.parametrize('long_text',[False,True])
def test_actual_medicated_flush_save_retains_tag_and_source_volumes(color,long_text):
    line='abcdefghijklmnopqrstuvwxyz12345' if long_text else 'Flush label'
    execute(commit_setup()+function('skApplyPendingTag')+f'''
        uiNamespace setVariable ["ACME_SK_PendingTagColor","{color}"];
        uiNamespace setVariable ["ACME_SK_PendingTagText",["{line}","Measured source","Third line"]];
        uiNamespace setVariable ["ACME_SK_CompoundComponents",[["Ketamine",2],["Propofol",1]]];
        call ACME_fnc_skFlushSave;
        private _store=_medic getVariable ["ACME_narcStore",[]];
        [count _store==1 && {{_storeWrites==1}},"flush save did not produce one row"] call _check;
        private _row=_store select 0;
        [(_row select [7,4]) isEqualTo ["{color}","{line[:25]}","Measured source","Third line"],"pending flush tag lost"] call _check;
        [(_row select 2)==3 && {{(_row select 4)==5}} && {{(_row select 5) isEqualTo [["Ketamine",2],["Propofol",1]]}},"tag changed fluid quantities"] call _check;
        [(_row select 6)=="dilutionB13" && {{(_row select 12)=="flush"}},"saved flush identity changed"] call _check;
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==18 && {{([_medic,"Propofol"] call ACME_fnc_infusionVialVolume)==9}},"tag changed source funding"] call _check;
        [(_inventoryCounts get "ACM_SalineFlush_10")==0,"flush container debit wrong"] call _check;
    ''')


@pytest.mark.parametrize('view',['body','syringe'])
@pytest.mark.parametrize('return_context',[False,True])
def test_pending_flush_preview_keeps_current_page_visibility_despite_return_context(view,return_context):
    execute(selector_setup()+f'''
        uiNamespace setVariable ["ACME_SK_View","{view}"];
        uiNamespace setVariable ["ACME_SK_WasteStage","draw"];
    '''+('_display setVariable ["ACME_SK_Return",["bag"]];' if return_context else '')+f'''
        call ACME_fnc_skPendingTagEnsure; _writes=[];
        call _renderPrefix;
        [[84610,"ctrlShow",{str(view=='syringe').lower()}] in _writes,"wrong flush preparation visibility"] call _check;
        [(uiNamespace getVariable ["ACME_SK_WasteStage",""])=="draw","render changed preparation stage"] call _check;
    ''')


@pytest.mark.parametrize('args',['[]','[0.15]','[1,2]','parsingNamespace'])
def test_legacy_body_preview_helpers_delegate_without_rewriting_navigation(args):
    execute('''private _renderCalls=0;private _movesIn=[];
        ACME_fnc_skCarouselRender={_renderCalls=_renderCalls+1;};
        ACME_fnc_skCarouselMove={_movesIn pushBack _this;};
    '''+source('skBodySyringeRender')+f'private _shim={{'+source('skBodySyringeMove')+f'''}};
        {args} call _shim;
        [_renderCalls==1 && {{_movesIn isEqualTo [{args}]}},"compatibility shim changed delegate or arguments"] call _check;
    ''')


@pytest.mark.parametrize('kind,field,name,old,new',[
    ('preview','body','skBodySyringeRender','ACME_fnc_skCarouselRender','ACME_fnc_skBuildHotspots'),
    ('preview','render','skCarouselRender','_tag ctrlShow false;','_tag ctrlShow true;'),
    ('preview','hot','skBuildHotspots','(_flush != "") || {_syringeIndex >= 0}','_syringeIndex >= 0'),
    ('tag','pending','skPendingTagRender','(_view == "syringe");','(_view == "syringe") && {!_infusion};'),
    ('tag','save','skFlushSave','call ACME_fnc_skApplyPendingTag','call ACME_fnc_skCompoundLabel'),
    ('tag','pick','skPickFlush','[10, _patient, _bodyPart, _flushClass]','[1, _patient, _bodyPart, _flushClass]'),
])
def test_current_contracts_reject_regressions_despite_comment_decoys(kind,field,name,old,new):
    check=preview_contract if kind=='preview' else tag_save_contract
    check()
    text=source(name); assert old in text
    with pytest.raises(AssertionError):check(**{field:text.replace(old,new,1)+'\n/* '+old+' */\n'})
