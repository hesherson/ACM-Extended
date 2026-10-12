"""Native opener input, hidden-list selection and action admission execute in SQF-VM.

Dialog creation, native controls and inventory/config queries are explicit engine
boundaries. These tests do not certify Arma pointer routing or click acoustics.
"""
import re

import pytest

import test_menu_death_lifecycle as vm
from test_b226_transfusion_presentation import switch_ui_setup
from test_b274_transfusion_preparation import stage_setup
from test_b275_transfusion_return_access import opener_prefix, setup as opener_setup
from test_b278_transfusion_geometry import renderer_setup
from test_b279_transfusion_ui import hidden_inventory_cards
from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_b156_procedure_supplies import primitives
from source_scan import lex, matching


def native_inventory_setup():
    # Config classes/names are engine lookups; the checked-out inventory builder
    # and its input handling remain intact. Avoid unrelated missing-config VM warnings.
    source = re.sub(r'configFile >> "CfgWeapons" >> _\w+', 'configNull', switch_ui_setup())
    return source.replace('_rows=[];', '_rows=[];_rowData=[];_rowTips=[];')


def card_event_setup():
    source = read('updateTransfusionCards')
    start = source.index('_hit ctrlAddEventHandler ["ButtonClick",')
    end = source.index('for "_child" from 10 to 39', start)
    source = source[start:end].replace('_hit ctrlAddEventHandler', '_cardEvents pushBack')
    return 'private _cardEvents=[];' + source + 'private _cardClick=(_cardEvents select 0)select 1;'


def native_initialization():
    source = (ROOT / 'addons/circulation/functions/fnc_openTransfusionMenu.sqf').read_text()
    start = source.index('call FUNC(TransfusionMenu_UpdateSelection);')
    end = source.index('private _ctrlPatientName =', start)
    resets = re.findall(r'_display setVariable \["ACME_txInputTrace(?:Count|Last)"[^;]+;', source)
    assert len(resets) == 2
    return adapt('\n'.join(resets) + source[start:end], 'circulation')


def input_trace_source():
    source = read('updateTransfusionControls')
    source = source[source.index('// B280 native-input observation:'):]
    source = source.replace('lbCurSel _ctrlRightList', '_selection')
    source = source.replace('ctrlShown _ctrlY', '_yVisible')
    source = source.replace('ctrlEnabled _ctrlY', '_yEnabled')
    source = source.replace('ctrlText _ctrlY', '_yText')
    source = source.replace('diag_log', '_diagnostics pushBack')
    return primitives(adapt(source))


def admission_source():
    source = read('updateTransfusionControls')
    # Execute the selection/classification predicates and both actual action gates.
    # The skipped interval is native layout geometry, not admission decisions.
    visible = source[source.index('private _selRow0 ='):source.index('private _ctrlSpikeBtn =')]
    actions = source[source.index('private _ctrlSpike ='):source.index('[_display,_flTarget')]
    source = visible + actions
    source = source.replace('_display displayCtrl 86141', 'uiNamespace')
    source = source.replace('_display displayCtrl 86142', 'profileNamespace')
    source = source.replace('lbCurSel _ctrlRightList', '_selection')
    source = source.replace('_ctrlRightList lbData _selRow0', '(_rowData select _selRow0)')
    source = source.replace('_ctrlRightList lbData _si2', '(_rowData select _si2)')
    source = source.replace('_ctrlRightList lbData _si', '(_rowData select _si)')
    source = source.replace('_ctrlSpike ctrlSetText', '_spikeText=')
    source = source.replace('_ctrlY ctrlSetText', '_yText=')
    source = re.sub(r'_ctrlSpike ctrlSetTooltip [^;]+;', '', source)
    return primitives(adapt(source))


def input_setup():
    return stage_setup() + native_inventory_setup() + opener_setup() + hidden_inventory_cards() + card_event_setup() + r'''
        private _ivPresent=[];private _ioPresent=[];
        private _switchArguments=[];private _bagPaints=0;
        private _ctrlRightList=missionNamespace;
        private _targetPatient=_patient;private _preparedMode=false;
        private _ctrlSetsList=objNull;private _selectedAccessValid=false;
        private _selectingPiggyback=false;private _flTarget=_patient;
        private _spikeEnabled=false;private _yEnabled=false;
        private _spikeText="";private _yText="";private _yVisible=false;
        private _diagnostics=[];
        private _mapDefault={params["_map","_args"];_args params["_key","_default"];if(_key in _map)then{_map get _key}else{_default}};
        ACME_fnc_itemList={(_this select 0)getVariable["fixtureStock",[]]};
        ACME_fnc_itemCount={params["_unit","_class"];{_x==_class}count(_unit getVariable["fixtureStock",[]])};
        // The real native list maps these physical blood items at postInit.
        ACM_circulation_Fluids_Array=["ACM_BloodBag_ON_500","ACM_SalineBag_500","ACM_FieldBloodTransfusionKit"];
        ACM_circulation_Fluids_Array_Data=["BloodBag_ON_500","SalineIV_500","FieldBloodTransfusionKit"];
        ACM_circulation_fnc_TransfusionMenu_UpdateSelection={};
        ACM_circulation_fnc_TransfusionMenu_UpdateBagList={_bagPaints=_bagPaints+1;};
        ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory={
            _switchArguments pushBack +_this;
            _this call _switchInventory;
            _selection=_sel;
        };
        ACME_fnc_transfusionUiSet={params ["_ctrl","_kind","_value"];
            if (_kind=="enable") then {
                if (_ctrl isEqualTo uiNamespace) then {_spikeEnabled=_value;};
                if (_ctrl isEqualTo profileNamespace) then {_yEnabled=_value;};
            };
        };
    ''' + 'private _nativeOpen={' + opener_prefix() + native_initialization() + '};' + \
        'ACME_fnc_updateTransfusionControls={_preparedMode=uiNamespace getVariable["ACME_preparedListMode",false];' + admission_source() + '_yVisible=_showY0;' + input_trace_source() + '};'


def capture_execute(monkeypatch, source):
    """Retain actual VM diagnostics, including typed-params warnings not fatal to SQF."""
    runs = []
    original = vm.subprocess.run

    def capture(*args, **kwargs):
        result = original(*args, **kwargs)
        runs.append(result.stdout + result.stderr)
        return result

    monkeypatch.setattr(vm.subprocess, 'run', capture)
    execute(source)
    assert len(runs) == 1
    return runs[0]


@pytest.mark.parametrize('io', [False, True], ids=['no-access', 'torso-FAST1'])
def test_native_open_resets_object_payload_and_card_selection_enables_blood_actions(monkeypatch, io):
    output = capture_execute(monkeypatch, input_setup() + f'''
        _ioPresent={('["body"]' if io else '[]')};
        _medic setVariable ["stock",["ACM_BloodBag_ON_500","ACM_SalineBag_500"]];
        _medic setVariable ["fixtureStock",["ACM_BloodBag_ON_500","ACM_SalineBag_500","ACME_YTubing"]];
        [_medic,_patient,"body"]call _nativeOpen;
        [_switchArguments isEqualTo [[]],"native opener forwarded its medic Object into the Boolean inventory API"]call _check;
        [ACM_circulation_TransfusionMenu_Selected_Inventory==0 && {{count _rowData==2}},"first native inventory did not initialize Self and its exact rows"]call _check;
        [ACM_circulation_TransfusionMenu_Selected_AccessSite=={0 if io else -1},"native opener lost the real IO/no-access selection"]call _check;
        [_bagPaints==1 && {{_selection==-1}},"initial inventory selected stale prior custody"]call _check;
        call ACME_fnc_updateTransfusionControls;
        [!_yVisible && {{!_yEnabled}} && {{!_spikeEnabled}},"unselected inventory offered preparation actions"]call _check;
        private _bloodRow=_rowData findIf {{(_x splitString "|")select 0=="ACM_BloodBag_ON_500"}};
        _hit setVariable ["ACME_txIdentity",["inventory",_rowData select _bloodRow]];
        [(_cardEvents apply {{_x select 0}})isEqualTo["ButtonClick","MouseZChanged","KeyDown","MouseEnter","MouseExit","SetFocus","KillFocus"],"native card registration order changed"]call _check;
        [_hit]call _cardClick;
        [_selection==_bloodRow && {{_yVisible}} && {{_yEnabled}} && {{_spikeEnabled}},"blood card failed to admit both actual native preparation actions"]call _check;
        [_yText=="Spike Y tubing" && {{_spikeText=="Spike Bag"}},"blood selection painted the wrong action stage"]call _check;
    ''')
    assert '[WRN]' not in output, output


@pytest.mark.parametrize('payload', ['[_medic,_patient,"body"]', '[uiNamespace]', 'uiNamespace', 'bare-call'])
def test_inventory_switch_tolerates_native_event_payload_but_false_preserves_pairing(monkeypatch, payload):
    invocation = 'call _switchInventory;' if payload == 'bare-call' else payload + ' call _switchInventory;'
    output = capture_execute(monkeypatch, native_inventory_setup() + f'''
        _patient setVariable ["stock",["BloodIV"]];_medic setVariable ["stock",["SalineIV"]];
        {invocation}
        [ACM_circulation_TransfusionMenu_Selected_Inventory==1 && {{_rows isEqualTo ["BloodIV"]}},"event payload failed to advance to patient inventory"]call _check;
        missionNamespace setVariable ["ACME_yPending","blood"];
        missionNamespace setVariable ["ACME_yPendingSaline","saline"];
        [false]call _switchInventory;
        [ACM_circulation_TransfusionMenu_Selected_Inventory==1 && {{_rows isEqualTo ["BloodIV"]}},"explicit refresh advanced source"]call _check;
        [(missionNamespace getVariable "ACME_yPending")=="blood" && {{(missionNamespace getVariable "ACME_yPendingSaline")=="saline"}},"refresh discarded the pending funded recipe"]call _check;
    ''')
    assert '[WRN]' not in output, output


@pytest.mark.parametrize('blocked', ['missing-tubing', 'busy', 'FBTK'])
def test_selected_native_card_still_obeys_y_component_and_product_gates(blocked):
    changes = {
        'missing-tubing': '_medic setVariable ["fixtureStock",["ACM_BloodBag_ON_500"]];',
        'busy': 'missionNamespace setVariable ["ACME_spikingActive",["ACM_BloodBag_ON_500"]];',
        'FBTK': '',
    }[blocked]
    bag = 'ACM_FieldBloodTransfusionKit' if blocked == 'FBTK' else 'ACM_BloodBag_ON_500'
    execute(input_setup() + f'''
        _medic setVariable ["stock",["{bag}"]];
        _medic setVariable ["fixtureStock",["{bag}","ACME_YTubing"]];
        [_medic,_patient,"body"]call _nativeOpen;
        {changes}
        _hit setVariable ["ACME_txIdentity",["inventory",_rowData select 0]];
        [_hit]call _cardClick;
        [!_yEnabled,"selected card bypassed an unavailable Y component/product gate"]call _check;
    ''' + ('[!_yVisible,"FBTK is a collection kit, not a prepared blood unit"]call _check;' if blocked == 'FBTK' else ''))


def test_card_hit_is_last_enabled_face_above_disabled_artwork():
    source = (ROOT/'addons/acm_extended/TransfusionMenu_Styles.hpp').read_text()
    card = source.split('class ACME_TransfusionCard:', 1)[1].split('class ACME_TransfusionInlineDetails:', 1)[0]
    assert card.index('class Hit:') > card.index('#undef ACME_TX_MARK')
    assert 'class Hit: ACME_TransfusionActionButton' in card
    execute(renderer_setup() + r'''
        [missionNamespace]call ACME_fnc_updateTransfusionCards;
        {[_controlValues get format ["%1:enable",_x] isEqualTo true,"card ancestor remained disabled"]call _check;}forEach [86500,86510,86520,86530,86540];
        {[_controlValues get format ["%1:enable",[_x,9]] isEqualTo true,"native card button remained disabled"]call _check;}forEach [86500,86510,86520,86530,86540];
        for "_child" from 10 to 39 do {
            [_controlValues get format ["%1:enable",[86520,_child]] isEqualTo false,"decorative child claimed card input"]call _check;
        };
    ''')


def test_native_inventory_button_uses_explicit_empty_action_arguments():
    source = (ROOT/'addons/circulation/TransfusionMenu_Dialog.hpp').read_text()
    assert 'action = QUOTE([] call FUNC(TransfusionMenu_SwitchTargetInventory));' in source


@pytest.mark.parametrize('io', [False, True], ids=['no-access', 'torso-FAST1'])
def test_native_blood_and_saline_cards_feed_all_three_config_y_actions(io):
    config = (ROOT/'addons/acm_extended/config.cpp').read_text()
    button = config.split('class ACME_YTubingButton:', 1)[1].split('};', 1)[0]
    action = re.search(r'action = "([^"]+)";', button).group(1)
    execute(input_setup() + f'''
        _ioPresent={('["body"]' if io else '[]')};
        _medic setVariable ["fixtureStock",["ACM_BloodBag_ON_500","ACM_SalineBag_500","ACME_YTubing"]];
        [_medic,_patient,"body"]call _nativeOpen;
        private _bloodRow=_rowData findIf {{(_x splitString "|")select 0=="ACM_BloodBag_ON_500"}};
        _hit setVariable ["ACME_txIdentity",["inventory",_rowData select _bloodRow]];
        [_hit]call _cardClick;
        [_yEnabled && {{_yVisible}},"first config Y action had no clickable blood admission"]call _check;
    ''' + action + ';' + r'''
        [count _waits==0 && {_yText=="Select Flush Saline"} && {!_yEnabled} && {_yVisible},"first action skipped the native saline selection stage"]call _check;
        [count _rowData==1 && {(_rowData select 0)=="ACM_SalineBag_500|SalineIV_500"},"Y picker did not rebuild the real inventory rows as saline-only"]call _check;
        // A native list redraw still carries the same prepared blood intent.
        [false]call ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory;
        _hit setVariable ["ACME_txIdentity",["inventory",_rowData select 0]];
        [_hit]call _cardClick;
        [_yEnabled && {_yVisible} && {_yText=="Select Flush Saline"},"saline card failed to enable the second config action"]call _check;
    ''' + action + ';' + r'''
        [count _waits==0 && {_yEnabled} && {_yText=="Build Y Tubing"},"second action did not admit the explicit third build stage"]call _check;
    ''' + action + ';' + r'''
        [count _waits==1,"third config action failed to queue exactly one assembly"]call _check;
        (_waits select 0 select 1)call (_waits select 0 select 0);
        [count (_medic getVariable["ACME_preparedIVSets",[]])==1 && {(_medic getVariable "fixtureStock")isEqualTo []},"native admitted actions lost a funded Y component"]call _check;
        [uiNamespace getVariable["ACME_preparedListMode",false],"finished Y assembly stayed outside prepared view"]call _check;
        [str (_patient getVariable "ACM_circulation_IV_Bags")==_initialBagText,"inventory preparation changed active patient fluids"]call _check;
    ''')


def assert_native_input_diagnostics_bounded():
    execute(input_setup() + r'''
        _medic setVariable ["fixtureStock",["ACM_BloodBag_ON_500","ACM_SalineBag_500","ACME_YTubing"]];
        [_medic,_patient,"body"]call _nativeOpen;
        for "_refresh" from 0 to 20 do {call ACME_fnc_updateTransfusionControls;};
        [count _diagnostics==0,"unselected native menu emitted RPT traffic"]call _check;
        private _bloodRow=_rowData findIf {(_x splitString "|")select 0=="ACM_BloodBag_ON_500"};
        _hit setVariable ["ACME_txIdentity",["inventory",_rowData select _bloodRow]];
        [_hit]call _cardClick;
        [count _diagnostics==1 && {(_diagnostics select 0)find "ACM_BloodBag_ON_500" >= 0},"first blood input state lacked its exact physical item"]call _check;
        for "_refresh" from 0 to 40 do {call ACME_fnc_updateTransfusionControls;};
        [count _diagnostics==1,"steady 0.25-second repaint repeated native input diagnostics"]call _check;
        missionNamespace setVariable ["ACME_spikingActive",["ACM_BloodBag_ON_500"]];
        call ACME_fnc_updateTransfusionControls;
        [count _diagnostics==2 && {!_yEnabled},"busy admission change failed to produce one diagnostic"]call _check;
        missionNamespace setVariable ["ACME_spikingActive",[]];
        for "_change" from 0 to 40 do {
            ACM_circulation_TransfusionMenu_Selected_Inventory=_change % 3;
            call ACME_fnc_updateTransfusionControls;
        };
        [count _diagnostics==16 && {(_display getVariable "ACME_txInputTraceCount")==16},"per-display input diagnostics exceeded their hard cap"]call _check;
        [_medic,_patient,"body"]call _nativeOpen;
        [(_display getVariable "ACME_txInputTraceCount")==0 && {(_display getVariable "ACME_txInputTraceLast")isEqualTo []},"recycled native dialog retained prior trace budget/state"]call _check;
        private _salineRow=_rowData findIf {(_x splitString "|")select 0=="ACM_SalineBag_500"};
        _hit setVariable ["ACME_txIdentity",["inventory",_rowData select _salineRow]];
        [_hit]call _cardClick;
        [count _diagnostics==16,"ordinary selected saline emitted Y diagnostics"]call _check;
    ''')


def test_native_input_diagnostics_are_changed_state_only_and_capped_per_opened_display():
    assert_native_input_diagnostics_bounded()


def assert_startup_identity_log_is_outside_callbacks():
    source = read('initForkStartupRuntime')
    tokens = lex(source)
    pairs = matching(tokens)
    emitters = [i for i, token in enumerate(tokens) if token.kind == 'ident' and token.value == 'diag_log']
    assert len(emitters) == 1
    emitter = emitters[0]
    assert not any(start < emitter < end for start, end in pairs.items() if tokens[start].value == '{')
    assert '"[ACME BUILD] version=%1 batch=%2 revision=%3"' in source
    assert 'ACME_infusion_version,ACME_buildBatch,ACME_networkAuditRevision' in source
    startup = lex(read('postInit'))
    assert sum(a.value == 'call' and b.value == 'ACME_fnc_initForkStartupRuntime' for a, b in zip(startup, startup[1:])) == 1


def test_startup_build_identity_has_one_top_level_emitter_outside_runtime_callbacks():
    assert_startup_identity_log_is_outside_callbacks()
