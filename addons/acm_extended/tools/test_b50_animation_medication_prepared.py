from historical_source import read_source, assert_release_identity
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT / rel, encoding='utf-8-sig', errors='ignore')

def test_version_batch():
    assert_release_identity()
    p = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()

def test_finite_provider_animations_are_one_shot_not_watchdog_replayed():
    from test_historical_pose_lifecycle import test_finite_work_enters_once_without_a_fixed_replay_loop, test_owner_hold_reasserts_only_observed_drift_and_never_replays_running_action
    for mode in ('response','airway','torsoBandage'):
        test_finite_work_enters_once_without_a_fixed_replay_loop(mode)
    for disturbance in ('none','speed','state'):
        test_owner_hold_reasserts_only_observed_drift_and_never_replays_running_action(disturbance)

def test_tsp_sling_is_latched_and_never_reinvoked_during_same_handoff():
    # The one-shot guarantee belongs to the current holster reservation, not old TSP timings.
    from test_historical_weapon_preflight import test_real_pose_handoff_shares_pending_holster_instead_of_restarting_it
    for weapon in ('pistol','rifle','launcher'):
        test_real_pose_handoff_shares_pending_holster_instead_of_restarting_it(weapon)

def test_medication_three_column_overlay_is_restored_and_direct_data_driven():
    # The native live labels win; metadata joins by medication key and fills missing rows.
    from test_bounded_medication_presentation import renderer_contract
    from test_historical_medication_rows import test_visible_rows_keep_native_labels_but_recover_blank_labels_from_metadata, test_visible_rows_bind_metadata_by_key_and_recover_missing_backing_entries, test_stock_preview_uses_reserved_volume_and_the_rows_exact_physical_class
    renderer_contract()
    test_visible_rows_keep_native_labels_but_recover_blank_labels_from_metadata()
    test_visible_rows_bind_metadata_by_key_and_recover_missing_backing_entries('[]')
    test_stock_preview_uses_reserved_volume_and_the_rows_exact_physical_class()

def test_native_medication_list_is_hidden_backing_selector_everywhere():
    for rel, token in [
        ('functions/fn_skMedicationSync.sqf', '_list ctrlShow false;'),
        ('functions/fn_skSetView.sqf', '(_display displayCtrl 84006) ctrlShow false;'),
        ('functions/fn_skUiTick.sqf', '(_d displayCtrl 84006) ctrlShow false;'),
        ('functions/fn_infusionDrawStock.sqf', '_list ctrlShow false;'),
        ('functions/fn_skInject.sqf', '_medListNative ctrlShow false;'),
    ]:
        assert token in txt(rel), rel

def test_medication_source_mirrors_acm_vial_membership_and_never_requires_extra_registry_filter():
    s = txt('functions/fn_medicationSourceRows.sqf')
    assert 'ACM_circulation_MedicationVialList' in s
    assert 'configClasses (configFile >> "CfgWeapons")' in s
    assert 'getNumber (_cfg >> "ACM_isVial")' in s
    assert '[_holder, _class] call ACME_fnc_vialItemCount' in s
    assert 'if (_label == "") then {_label = _med;};' in s
    # B49's concentration-class display gate was removed; concentration belongs to draw math, not row visibility.
    assert 'if !(isClass _conc) then {continue}' not in s

def test_prepared_iv_sets_button_counts_and_pulses_green():
    from test_menu_death_lifecycle import adapt, execute
    s = txt('functions/fn_updateTransfusionControls.sqf')
    # Preserve this historical identity. B275 deliberately replaces the green
    # pulse with the approved black/grey toggle; bottle custody and counts still
    # execute the real filters and the original prepared-entry index mapping.
    count = re.search(r'private _preparedSetCountB50 = .*?;', s).group()
    shown = s[s.index('private _shown = [];'):s.index('private _wantSig = str _shown;')]
    entries = re.search(r'private _preparedEntries = .*?;', s).group()
    prepared_filter = s[s.index('private _shownPrepared = [];'):s.index('if (!isNull _ctrlPreparedList) then {', s.index('private _shownPrepared = [];'))]
    prepared_filter = prepared_filter.replace('getText (configFile >> "ace_medical_treatment" >> "IV" >> (_entry param [2,""]) >> "type")', '"Saline"')
    # B276 restores prepared selection by custody ID. Execute its real capture
    # and fallback block so filtered rows still map to their original indices.
    restore_start = s.index('private _oldSelected = missionNamespace getVariable ["ACME_infusion_SelectedPreparedIndex"')
    restore_identity = s[restore_start:s.index('lbClear _ctrlPreparedList;', restore_start)]
    row_start = s.index('private _label = [_entry] call ACME_fnc_formatPreparedLabel;')
    row_begin = s.rfind('{', 0, row_start)
    row_end = s.index('} forEach _shownPrepared;', row_start) + len('} forEach _shownPrepared;')
    rows = s[row_begin:row_end]
    rows = rows.replace('private _i = _ctrlPreparedList lbAdd _label;', 'private _i = _renderedPrepared pushBack _label;')
    rows = rows.replace('_ctrlPreparedList lbSetValue [_i,_index];', '_renderedPreparedIndices pushBack _index;')
    rows = rows.replace('_ctrlPreparedList lbSetTooltip [_i,_label];', '')
    rows = rows.replace('_ctrlPreparedList lbSetColor [_i,[0.79,0.73,0.89,1]];', '_renderedPreparedColors pushBack [0.79,0.73,0.89,1];')
    rows = rows.replace('_ctrlPreparedList lbSetCurSel _i;', '_restoredSelection=_i;')
    paint = s[s.index('_ctrlSetsBtn ctrlSetText (format ["Prepared IV sets (%1)"'):s.index('[_ctrlSetsBtn,"show",true]')]
    paint = paint.replace('_ctrlSetsBtn ctrlSetText (', '_buttonLabel = (')
    paint = paint.replace('_ctrlSetsBtn ctrlSetFontHeight', '_paintFontHeight =').replace('safeZoneH','1')
    paint = paint.replace('_ctrlSetsBtn ctrlSetBackgroundColor', '_paintBackground =')
    paint = paint.replace('_ctrlSetsBtn ctrlSetTextColor', '_paintText =')
    execute(r'''
        private _normal=["saline-set","SalineIV_500","SalineIV_500","","","","Saline prepared",false,"yset",500,0];
        private _bottle=["prop-bottle","ACM_Vial_Propofol","ACME_PropofolIV_50","","","","Propofol prepared",false,"propofol",50,0];
        private _prepared=["prop-bottle","ACM_Vial_Propofol","ACME_PropofolIV_50","Propofol",500,1800,20,0,0,0,50];
        ACE_player setVariable ["ACME_preparedIVSets",[_normal,_bottle]];
        ACE_player setVariable ["ACME_infusion_PreparedBags",[_prepared]];
        private _sets=ACE_player getVariable ["ACME_preparedIVSets",[]];
        private _tgtNet="";
        private _targetPatient=_patient;private _targetBodyPart="leftarm";private _flIV=true;private _flSite=0;
        private _selectingPiggyback=false;private _preparedMode=false;
        private _display=missionNamespace;private _restoredSelection=-1;
        missionNamespace setVariable ["ACME_infusion_SelectedPreparedIndex",0];
        _display setVariable ["ACME_txPreparedIdentity",[]];
        private _renderedPrepared=[];private _renderedPreparedIndices=[];
        private _renderedPreparedColors=[];
        ACME_fnc_piggybackEligible={true};
        ACME_fnc_formatPreparedLabel={(_this select 0) param [0,""];};
    ''' + adapt(count + shown + entries + prepared_filter + restore_identity + rows) + r'''
        [_preparedSetCountB50==1,"paired bottle incorrectly counted as a plain IV set"] call _check;
        [_shown isEqualTo [["saline-set","Saline prepared"]],"bottle leaked into the plain Prepared IV Sets overlay"] call _check;
        [_renderedPrepared isEqualTo ["prop-bottle"] && {_renderedPreparedIndices isEqualTo [0]},"prepared bottle is missing or duplicated in Prepared Infusions"] call _check;
        [_restoredSelection==0,"prepared selection mapping was lost"] call _check;
        [count (ACE_player getVariable "ACME_preparedIVSets")==2,"UI filtering destroyed paired bottle custody"] call _check;
        private _paintBackground=[];private _paintText=[];private _buttonLabel="";private _paintFontHeight=0;
        private _paint={
    ''' + adapt(paint) + r'''
        };
        {
            _nowTime=_x;call _paint;
            [_paintBackground isEqualTo [0.18,0.18,0.18,1] && {_paintFontHeight==.017},"prepared tab lost its visible neutral grey surface or type size"] call _check;
            [_buttonLabel=="Prepared IV sets (1)","plain-set count missing from toggle"] call _check;
        } forEach [0,0.25,0.5,0.75];
        _preparedMode=true;call _paint;
        [_buttonLabel=="Prepared IV sets (1)","prepared tab changed its title when selected"] call _check;
        ACE_player setVariable ["ACME_preparedIVSets",[_bottle]];
    ''' + adapt(count) + r'''
        [_preparedSetCountB50==0,"bottle-only inventory should show zero plain prepared IV sets"] call _check;
        call _paint;
        [_paintBackground isEqualTo [0.18,0.18,0.18,1] && {_buttonLabel=="Prepared IV sets (0)"},"bottle-only custody changed plain-set count or grey tab surface"] call _check;
        private _salineA=["saline-a","SalineIV_100","SalineIV_100","TXA",1000,0,20,60,1,100,100];
        private _salineB=["saline-b","SalineIV_100","SalineIV_100","TXA",1000,0,20,60,1,100,100];
        ACE_player setVariable ["ACME_infusion_PreparedBags",[_salineA,_prepared,_salineB]];
        _selectingPiggyback=true;_oldSelected=2;_restoredSelection=-1;
        missionNamespace setVariable ["ACME_infusion_SelectedPreparedIndex",2];
        _renderedPrepared=[];_renderedPreparedIndices=[];_renderedPreparedColors=[];
    ''' + adapt(entries + prepared_filter + restore_identity + rows) + r'''
        [_renderedPrepared isEqualTo ["saline-a [PiB]","saline-b [PiB]"] && {_renderedPreparedIndices isEqualTo [0,2]},"filtered prepared rows retargeted the original infusion indices"] call _check;
        [_restoredSelection==1 && {count _renderedPreparedColors==2},"filtered selection/highlight did not follow the visible row"] call _check;
        [count _preparedEntries==3 && {(ACE_player getVariable "ACME_infusion_PreparedBags") isEqualTo [_salineA,_prepared,_salineB]},"picker filtering consumed prepared custody"] call _check;
    ''')
    assert 'Prepared IV sets (%1)' in s
    assert 'private _setPulse =' not in s

def test_prep_infusion_only_enables_for_selected_prepared_saline():
    s = txt('functions/fn_updateTransfusionControls.sqf')
    gate = s[s.index('private _canPrep = false;'):s.index('private _preparedEntries')]
    assert 'if (_preparedMode) then {' in gate
    assert 'ACME_preparedIVSets' in gate
    assert 'param [8, "yset"]' in gate
    assert 'ACME_fnc_isSalineItem' in gate
    assert '_canPrep = (_pSetsPrep findIf' not in gate
    assert 'In loose-bag view _canPrep deliberately remains false' in gate

def test_prep_callback_has_same_hard_gate():
    s = txt('functions/fn_openPrepFromInventoryMenu.sqf')
    assert 'if (!_preparedMode) exitWith' in s
    assert 'Open Prepared IV sets and select a saline set first.' in s
    assert 'Only a selected normal saline set can be prepared into an infusion.' in s
    assert 'ACME_fnc_isSalineItem' in s

def test_previous_b49_intubation_and_obtunded_contracts_untouched():
    p = txt('functions/fn_postInit.sqf')
    assert 'ACME_laryngo_cuffRunTime = 1.0' in p
    assert 'ACME_ETT_MinSeatFrame = 5' in p
    assert 'ACME_obtunded_getUpTime = 5.5' in p
    assert 'ACME_obtunded_sprintFallChance = 0.35' in p
