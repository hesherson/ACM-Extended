"""Reproduce piggyback-preparation refresh abortion and delayed initial reveal.

The production prepared picker and native opener/controller reveal blocks run
in SQF-VM. Control queries, fade writes and configuration lookups are explicit
Arma boundaries; these cases do not certify native rendering or multiplayer.
"""
import re
import subprocess

import pytest

from test_b156_procedure_supplies import primitives
from test_historical_core_boundaries import block_at
from test_menu_death_lifecycle import ROOT, adapt, execute, read


BASELINE = "18d16a5732b8d878d6e6c2f9dfdc3381e6235050"
OPEN = ROOT / "addons/circulation/functions/fnc_openTransfusionMenu.sqf"


def picker(source):
    start = source.index("private _shownPrepared = [];")
    end = source.index("if (!isNull _ctrlPreparedList)", start)
    code = source[start:end]
    code = code.replace(
        'getText (configFile >> "ace_medical_treatment" >> "IV" >> (_entry param [2,""]) >> "type")',
        '([_entry param [2,""]] call _carrierType)',
    )
    return primitives(adapt(code))


def picker_setup():
    return r'''
        private _preparedEntries=[];
        private _selectingPiggyback=true;
        private _targetPatient=_patient;private _targetBodyPart="leftarm";
        private _flIV=true;private _flSite=0;private _eligibleCalls=[];
        private _carrierType={params["_action"];["Saline","ACME_Propofol"] select (_action=="PropofolIV_50")};
        ACME_fnc_piggybackEligible={_eligibleCalls pushBack _this;(_this select 4)=="Saline"};
        // Actual prepared-record schema: field 16 is numeric carrier volume;
        // unopened bottle kind, when present, occupies field 17.
        private _prepared=["saline-set","ACM_SalineBag_100","SalineIV_100","CalciumChloride",1000,0,20,60,1,10,110,0,objNull,objNull,[["CalciumChloride",1000,1]],"saline-set",100];
        private _bottle=["bottle-set","ACM_Vial_Propofol","PropofolIV_50","Propofol",500,0,20,0,0,0,50,0,objNull,objNull,[["Propofol",500,1]],"bottle-set",50,"propofol-bottle"];
    '''


def test_baseline_reproduces_fatal_refresh_after_piggyback_infusion_preparation():
    old = subprocess.run(
        ["git", "show", f"{BASELINE}:addons/acm_extended/functions/fn_updateTransfusionControls.sqf"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    with pytest.raises(AssertionError, match="Unknown input combination SCALAR == STRING"):
        execute(picker_setup() + '_preparedEntries=[_prepared];' + picker(old))


@pytest.mark.parametrize("volume", [0, 100, 500])
@pytest.mark.parametrize("mixture", [False, True])
def test_piggyback_prepared_picker_accepts_numeric_carrier_volume_and_keeps_native_record(volume, mixture):
    code = picker_setup() + f'_prepared set[16,{volume}];'
    if mixture:
        code += '(_prepared select 14) pushBack ["CalciumGluconate",3000,1];'
    execute(code + r'''
        _preparedEntries=[_prepared];
        private _before=str _preparedEntries;
    ''' + picker(read("updateTransfusionControls")) + r'''
        [_shownPrepared isEqualTo [[_prepared,0]],"numeric carrier volume stranded prepared piggyback picker"]call _check;
        [count _eligibleCalls==1 && {(_eligibleCalls select 0) isEqualTo [_patient,"leftarm",true,0,"Saline",true]},"picker skipped actual line compatibility"]call _check;
        [_before==str _preparedEntries,"refresh mutated medication or carrier custody"]call _check;
    ''')


@pytest.mark.parametrize("guard", ["marker", "class", "both"])
def test_propofol_bottle_stays_excluded_from_piggyback_even_if_legacy_carrier_metadata_says_saline(guard):
    code = picker_setup() + r'''
        _bottle set[2,"SalineIV_100"];
        _preparedEntries=[_prepared,_bottle];
    '''
    if guard == "marker":
        code += '_bottle set[1,"legacy-propofol-bottle"];'
    if guard == "class":
        code += '_bottle deleteAt 17;'
    execute(code + picker(read("updateTransfusionControls")) + r'''
        [_shownPrepared isEqualTo [[_prepared,0]],"direct propofol bottle appeared as a compatible piggyback carrier"]call _check;
        [count _eligibleCalls==2,"bottle exclusion bypassed compatibility presentation pass"]call _check;
    ''')


def ui_boundary(source):
    source = source.replace('_display displayCtrl _x', '([_display,_x] call _control)')
    source = source.replace('_d displayCtrl _x', '([_d,_x] call _control)')
    source = re.sub(r'_ctrl ctrlSetFade ([^;]+);', r'_ctrl set["fade",\1];_fadeWrites pushBack[_ctrl get "id",\1];', source)
    source = source.replace('_ctrl ctrlCommit 0;', '_commitWrites=_commitWrites+1;')
    return primitives(adapt(source))


def opener_fade(source):
    start = source.index('private _initialLayoutControls = [')
    reveal_start = source.index('private _revealInitialLayout = {', start)
    opening = source.index('{', reveal_start)
    end = opening + len(block_at(source, opening)) + 1
    return ui_boundary(source[start:end])


def delayed_reveal():
    source = read("updateTransfusionControls")
    start = source.index('private _initialLayoutControls = _display getVariable')
    end = source.index('[_display] call ACME_fnc_paintTransfusionYBracket;', start)
    return ui_boundary(source[start:end])


def fade_setup():
    return r'''
        private _display=missionNamespace;
        private _liveControls=createHashMap;
        private _fadeWrites=[];private _commitWrites=0;
        private _control={params["_dialog","_id"];private _key=str _id;
            if !(_key in _liveControls) then {_liveControls set[_key,createHashMapFromArray[["id",_id],["fade",0],["shown",true],["enabled",true]]];};
            _liveControls get _key
        };
        uiNamespace setVariable["ACME_infusion_LayoutDisplay",objNull];
    '''


def test_baseline_delayed_layout_captures_anchors_without_ever_revealing_faded_controls():
    old = subprocess.run(
        ["git", "show", f"{BASELINE}:addons/circulation/functions/fnc_openTransfusionMenu.sqf"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    execute(fade_setup() + opener_fade(old) + r'''
        // Both original reveal attempts precede native anchor readiness.
        [!([_display,_initialLayoutControls]call _revealInitialLayout),"baseline unexpectedly revealed unready layout"]call _check;
        [!([_display,_initialLayoutControls]call _revealInitialLayout),"baseline retry unexpectedly revealed unready layout"]call _check;
        uiNamespace setVariable["ACME_infusion_LayoutDisplay",_display];
        // Later controller ticks contained no reveal. Capturing anchors alone
        // cannot make ctrlSetFade 1 controls visible again.
        {private _c=[_display,_x]call _control;[(_c get "fade")==1,"baseline lost persistent blank-state reproduction"]call _check;}forEach _initialLayoutControls;
    ''')


@pytest.mark.parametrize("missed_frames", [2, 4, 20])
def test_existing_refresh_worker_finishes_pending_reveal_after_delayed_native_layout(missed_frames):
    execute(fade_setup() + opener_fade(OPEN.read_text()) + f'''
        for "_frame" from 1 to {missed_frames} do {{
            [!([_display,_initialLayoutControls]call _revealInitialLayout),"unready layout revealed stale geometry"]call _check;
        }};
    ''' + r'''
        _display setVariable["fixtureInitialIds",+_initialLayoutControls];
        private _firstId=_initialLayoutControls select 0;
        private _firstControl=[_display,_firstId]call _control;
        _firstControl set["shown",false];_firstControl set["enabled",false];
        uiNamespace setVariable["ACME_infusion_LayoutDisplay",_display];
    ''' + delayed_reveal() + r'''
        {private _c=[_display,_x]call _control;[(_c get "fade")==0,"settled layout left control permanently transparent"]call _check;}forEach (_display getVariable["fixtureInitialIds",[]]);
        [(_firstControl get "fade")==0,"pending native controls stayed blank after piggyback return"]call _check;
        [!(_firstControl get "shown") && {!(_firstControl get "enabled")},"reveal enabled/showed a treatment control owned by another state"]call _check;
        [_display getVariable["ACME_txInitialLayoutRevealed",false],"reveal completion was never recorded"]call _check;
        [(_display getVariable["ACME_txInitialLayoutControls",[-1]])isEqualTo [],"completed reveal retained pending work"]call _check;
        private _writesAfterReveal=count _fadeWrites;
        [[_display,_display getVariable["fixtureInitialIds",[]]]call _revealInitialLayout,"completed original reveal unexpectedly failed"]call _check;
        [count _fadeWrites==_writesAfterReveal,"native immediate/next-frame reveal duplicated completed fade writes"]call _check;
    ''' + delayed_reveal() + r'''
        [count _fadeWrites==_writesAfterReveal,"every menu refresh recommitted already revealed controls"]call _check;
    ''')
