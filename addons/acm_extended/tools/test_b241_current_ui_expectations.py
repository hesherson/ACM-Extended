"""Current UI contracts plus production reopen-gate execution, not UI rendering.

The three historical checks follow already-shipped behavior. No production UI
code is modified by this batch and no inventory/transport fidelity is claimed.
"""
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, read, execute

EXCLUDED=('acme_directpressure','acme_stopdirectpressure','opentransfusionmenu',
          'acme_performthoracostomy','acme_adjustthoracostomy','acme_insertchesttube')


def has(source,fragment):
    tokens=[(t.kind,t.value) for t in lex(source)]
    wanted=[(t.kind,t.value) for t in lex(fragment)]
    return any(tokens[i:i+len(wanted)]==wanted for i in range(len(tokens)-len(wanted)+1))


def pending_block(source):
    ts=lex(source); pairs=matching(ts)
    starts=[i for i in range(len(ts)-2) if ts[i].value=='if' and ts[i+1].value=='('
            and ts[i+2].value=='_groupKey' and ts[i+3].value=='isEqualTo']
    assert len(starts)==1,'reopen eligibility gate missing/ambiguous'
    start=starts[0];then=pairs[start+1]+1
    assert ts[then].value=='then' and ts[then+1].value=='{'
    end=pairs[then+1]
    return source[ts[start].offset:ts[end].offset+1]+';'


def pending_reopen_contract(source):
    block=pending_block(source)
    assert has(block,"if (_groupKey isEqualTo '' && {!(_actionClass in ["+','.join(repr(x) for x in EXCLUDED)+"])}) then")
    assert has(block,'if !(ACE_player getVariable ["ACME_chestAccessPreflightActive", false]) then { ace_medical_gui_pendingReopen = true; };')
    statement="_ctrl ctrlAddEventHandler ['ButtonClick', _statement];"
    assert has(source,statement)
    assert source.index(statement)<source.index(block.rstrip(';'))


def current_finish_tray_contract(refresh,tray):
    assert has(refresh,'[_dlg displayCtrl 86553, _held == "line", 1, false] call ACME_fnc_traySlotState;')
    assert not has(refresh,'missionNamespace getVariable ["ACME_iv_lineSlot", false]')
    assert has(refresh,'if (_tool=="flush") then {["ACM_SalineFlush_10"] call _count} else {1}')
    assert has(refresh,'[_pic,_held==_tool,_stock] call ACME_fnc_traySlotState;')
    assert has(refresh,'forEach (_dlg getVariable ["ACME_IV_FinishTray",[]]);')
    assert has(tray,'private _tools=[["extension","EXTENSION"],["flush","10 mL FLUSH"],["dressing","TEGADERM"],["line","IV TUBING"],["lock","SALINE LOCK"]];')


def flush_selection_contract(source):
    assert has(source,'if (([ACE_player, uiNamespace getVariable ["ACME_SK_Patient",objNull], _flushClass] call ACME_fnc_treatmentSupplyCount) < 1) exitWith')
    assert has(source,'if !([10, _flushClass] call ACME_fnc_skApplySize) exitWith {};')
    assert has(source,'[_flushClass] call ACME_fnc_skWasteBegin;')
    assert source.index('call ACME_fnc_treatmentSupplyCount')<source.index('call ACME_fnc_skApplySize')<source.index('call ACME_fnc_skWasteBegin')
    identifiers={t.value for t in lex(source) if t.kind=='ident'}
    assert not {'closeDialog','createDialog','ACME_fnc_crystalloidCredit','ACME_fnc_skInjectSite'}&identifiers


@pytest.mark.parametrize('action',EXCLUDED+('checkpulse','foreign_addon_treatment'))
@pytest.mark.parametrize('header',[False,True])
@pytest.mark.parametrize('preflight',[False,True])
def test_actual_reopen_handler_respects_modal_ownership(action,header,preflight):
    renderer=(ROOT/'addons/gui/overrides/fnc_updateActions.sqf').read_text()
    pending_reopen_contract(renderer)
    # Substitute only native event-handler registration with an ordered capture.
    # The unmodified eligibility condition and callback body execute in SQF-VM.
    block=pending_block(renderer).replace('_ctrl ctrlAddEventHandler','_handlers pushBack')
    expected_registered=not header and action not in EXCLUDED
    expected_reopen=expected_registered and not preflight
    execute(f'''
        private _handlers=[];private _groupKey="{'group' if header else ''}";private _actionClass="{action}";
        ACE_player=_medic;_medic setVariable ["ACME_chestAccessPreflightActive",{str(preflight).lower()}];
        ace_medical_gui_pendingReopen=false;
        {block}
        [count _handlers=={int(expected_registered)},"wrong handler installed"] call _check;
        {{[(_x select 0)=="ButtonClick","wrong event kind"] call _check;call (_x select 1);}} forEach _handlers;
        [ace_medical_gui_pendingReopen isEqualTo {str(expected_reopen).lower()},"reopen raced modal ownership"] call _check;
    ''')


def test_current_finishing_tray_and_flush_selection_contracts():
    current_finish_tray_contract(read('ivMinigameRefreshBandSlot'),read('ivFinishTray'))
    flush_selection_contract(read('skPickFlush'))


@pytest.mark.parametrize('mutation',['restore-line','flush-stock','reopen-preflight','reopen-exclusion','syringe-recreate','flush-order'])
def test_current_ui_contracts_reject_reintroduced_historical_behavior(mutation):
    renderer=(ROOT/'addons/gui/overrides/fnc_updateActions.sqf').read_text()
    refresh=read('ivMinigameRefreshBandSlot');tray=read('ivFinishTray');flush=read('skPickFlush')
    pending_reopen_contract(renderer);current_finish_tray_contract(refresh,tray);flush_selection_contract(flush)
    with pytest.raises(AssertionError):
        if mutation=='restore-line':current_finish_tray_contract(refresh.replace('false] call ACME_fnc_traySlotState;', 'true] call ACME_fnc_traySlotState;'),tray)
        elif mutation=='flush-stock':current_finish_tray_contract(refresh.replace('["ACM_SalineFlush_10"] call _count','1'),tray)
        elif mutation=='reopen-preflight':pending_reopen_contract(renderer.replace('ACME_chestAccessPreflightActive','wrongFlag'))
        elif mutation=='reopen-exclusion':pending_reopen_contract(renderer.replace("'opentransfusionmenu',",''))
        elif mutation=='syringe-recreate':flush_selection_contract(flush+'\ncloseDialog 0;')
        else:flush_selection_contract(flush.replace('if !([10, _flushClass] call ACME_fnc_skApplySize) exitWith {};','[10, _flushClass] call ACME_fnc_skApplySize;'))
