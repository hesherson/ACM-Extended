"""Execute staged field-IV removal against production owner and UI decisions.

Native controls, pixel metrics, access storage and event transport are explicit
boundaries. These cases do not certify native Arma dragging or replication.
"""
import json

import pytest

import test_menu_death_lifecycle as lifecycle
from test_b232_iv_finish import SETUP, START_SETUP, rules
from test_b233_iv_interactions import fn
from test_b234_field_iv import ui_source
from test_menu_death_lifecycle import execute


@pytest.fixture(autouse=True)
def native_boundary_warnings_fail(monkeypatch):
    original = lifecycle.subprocess.run

    def checked(*args, **kwargs):
        result = original(*args, **kwargs)
        assert "[WRN]" not in result.stdout + result.stderr, result.stdout + result.stderr
        return result

    monkeypatch.setattr(lifecycle.subprocess, "run", checked)


def value(v):
    return json.dumps(v).lower()


def owner_fixture():
    return SETUP + rules() + r'''
        private _patientLocal=true;private _clock=100;
        private _removed=[];private _unplug=[];private _logs=[];
        ACME_fnc_ivAccessoryUnplug={_unplug pushBack _this;true};
        ACM_circulation_fnc_setIVLocal={_removed pushBack _this;_hasIV=false;};
        ACME_fnc_ivLogSite={"left arm"};ace_common_fnc_getName={"Medic"};
        ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
    ''' + fn("ivCatheterPull")


@pytest.mark.parametrize("gauge", [14, 16])
@pytest.mark.parametrize("accessories", [False, True])
def test_owner_refuses_primary_catheter_until_secondary_section_is_out(gauge, accessories):
    state = [accessories, accessories, accessories, accessories, True, gauge, True]
    execute(owner_fixture() + f'''
        _row set [15,{value(state)}];_patient setVariable ["ACME_IV_Marks",[_row]];
        private _before=str (_patient getVariable "ACME_IV_Marks");
        [!([_patient,_medic,"ivhub:7:1",7] call ACME_fnc_ivCatheterPull),
            "primary pull accepted an assembled field catheter"] call _check;
        [!([_patient,_medic,"ivhub:7:1",7] call ACME_fnc_ivCatheterPull),
            "duplicate primary pull bypassed staging"] call _check;
        [_removed isEqualTo [] && {{_unplug isEqualTo []}} && {{_logs isEqualTo []}} && {{_hasIV}},
            "refused primary pull changed native access or disconnected contents"] call _check;
        [str (_patient getVariable "ACME_IV_Marks")==_before,
            "refused primary pull changed assembly marks"] call _check;
    ''')


@pytest.mark.parametrize("gauge", [14, 16])
def test_secondary_owner_removal_preserves_primary_then_allows_separate_primary_pull(gauge):
    execute(owner_fixture() + f'''
        _row set [15,[true,true,true,true,true,{gauge},true]];
        private _other=+_row;_other set [14,"other-hub"];_other set [10,"upper"];
        _patient setVariable ["ACME_IV_Marks",[_row,_other]];
        ["begin","removeSecondary","secondary"] call _invoke;
        _serverTime=101;["finish","removeSecondary","secondary"] call _invoke;
        ["finish","removeSecondary","secondary"] call _invoke;
        [(call _getState) isEqualTo [false,false,false,false,true,0,true],
            "secondary pull did not preserve the primary lock and short film"] call _check;
        [_removed isEqualTo [] && {{_hasIV}} && {{count _unplug==1}},
            "secondary pull removed native venous access or disconnected twice"] call _check;
        [((call _getRow) select 4)=="hub", "secondary pull removed the primary hub"] call _check;
        [(((_patient getVariable "ACME_IV_Marks") select 1) select 15) isEqualTo [true,true,true,true,true,{gauge},true],
            "secondary pull altered a neighbouring catheter"] call _check;
        [[_patient,_medic,"ivhub:7:1",7] call ACME_fnc_ivCatheterPull,
            "primary remained blocked after secondary removal"] call _check;
        [_removed isNotEqualTo [] && {{count _removed==1}} && {{!_hasIV}} && {{count _unplug==2}},
            "separate primary pull did not remove one access"] call _check;
        [((call _getRow) select 4)=="removed", "primary hub remained after its own pull"] call _check;
    ''')


@pytest.mark.parametrize("gauge", [14, 16])
@pytest.mark.parametrize("action", ["removeLock", "removeDressing"])
def test_primary_lock_and_base_only_film_are_protected_until_secondary_removal(gauge, action):
    execute(SETUP + rules() + f'''
        private _state=[false,false,false,false,true,{gauge},true];
        [!(([_state,"{action}",true,16] call ACME_fnc_ivFinishPlan) select 0),
            "protected primary component has an allowed removal plan"] call _check;
        private _after=[_state,"removeSecondary"] call ACME_fnc_ivFieldTransition;
        [([_after,"{action}",true,16] call ACME_fnc_ivFinishPlan) select 0,
            "primary component still blocked after secondary removal"] call _check;
    ''')


@pytest.mark.parametrize("gauge", [14, 16])
@pytest.mark.parametrize("angle", [0, 15, 180])
@pytest.mark.parametrize("aspect", [0.5625, 0.28125])
def test_pull_selection_exposes_secondary_without_primary_catheter_or_lock(gauge, angle, aspect):
    execute(SETUP + rules() + START_SETUP + f'''
        _testPixelW={aspect};_testPixelH=1;
        _row set [13,{angle}];_row set [15,[false,false,false,false,true,{gauge},true]];
        _patient setVariable ["ACME_IV_Marks",[_row]];
        private _secondary=[_row,[1006.5,1140]] call ACME_fnc_ivFieldPoint;
        private _selected=[_secondary select 0,_secondary select 1,"",true] call ACME_fnc_ivFinishTarget;
        [count _selected==3 && {{(_selected select 1)=="removeSecondary"}},
            "secondary needle is not the selectable field pull"] call _check;
        private _primary=[_row select 2,_row select 3];
        private _lock=[_row,[1006.5,1060]] call ACME_fnc_ivFieldPoint;
        private _film=[_row,[1120,970]] call ACME_fnc_ivFieldPoint;
        {{
            private _hit=[_x select 0,_x select 1,"",true] call ACME_fnc_ivFinishTarget;
            [_hit isEqualTo [] || {{!((_hit select 1) in ["catheter","removeLock","removeDressing"])}},
                "assembled field IV exposed a protected primary pull target"] call _check;
        }} forEach [_primary,_lock,_film];
        _row set [15,[false,false,false,false,true,0,true]];
        _patient setVariable ["ACME_IV_Marks",[_row]];
        private _after=[_primary select 0,_primary select 1,"",true] call ACME_fnc_ivFinishTarget;
        [count _after==3 && {{(_after select 1)=="catheter"}},
            "secondary removal did not restore the primary pull target"] call _check;
    ''')


def test_owner_rechecks_a_lock_removal_if_secondary_appears_before_completion():
    execute(owner_fixture() + r'''
        _row set [15,[false,false,false,false,true,0,true]];
        _patient setVariable ["ACME_IV_Marks",[_row]];
        ["begin","removeLock","lock"] call _invoke;
        private _current=+(call _getRow);private _state=+(_current select 15);
        _state set [5,16];_current set [15,_state];
        _patient setVariable ["ACME_IV_Marks",[_current]];
        _serverTime=101;["finish","removeLock","lock"] call _invoke;
        [(call _getState) isEqualTo [false,false,false,false,true,16,true],
            "stale lock completion removed a newly assembled secondary"] call _check;
        [_unplug isEqualTo [] && {_removed isEqualTo []} && {_hasIV},
            "stale lock completion disconnected the retained assembly"] call _check;
    ''')


def test_owner_rechecks_outer_film_removal_before_it_can_peel_the_primary_film():
    execute(owner_fixture() + r'''
        _row set [15,[true,true,true,true,true,16,true]];
        _patient setVariable ["ACME_IV_Marks",[_row]];
        ["begin","removeDressing","film"] call _invoke;
        private _current=+(call _getRow);private _state=+(_current select 15);
        _state set [2,false];_current set [15,_state];
        _patient setVariable ["ACME_IV_Marks",[_current]];
        _serverTime=101;["finish","removeDressing","film"] call _invoke;
        [(call _getState) isEqualTo [true,true,false,true,true,16,true],
            "stale outer-film pull peeled the protected base film"] call _check;
    ''')


def test_secondary_pull_moves_only_secondary_and_its_downstream_layers():
    execute(SETUP + rules() + 'ACME_fnc_ivFieldPullLayers={' + ui_source("ivFieldPullLayers") + r'''};
        private _writes=[];private _write={_writes pushBack _this;};
        _row set [15,[true,true,true,true,true,16,true]];
        _d setVariable ["ACME_IV_FinishCtrls",[["ivhub:7:1",2,3,4,5,6]]];
        private _layers=[_d,_row,"removeSecondary",1] call ACME_fnc_ivFieldPullLayers;
        [(_layers select 0) isEqualTo [5,2,3] && {(_layers select 1)==5},
            "secondary pull moved primary catheter, saline lock or base film"] call _check;
    ''')


def test_stale_primary_ui_drag_stops_when_current_assembly_has_secondary():
    execute(owner_fixture() + 'ACME_fnc_ivMinigamePullStop={' + ui_source("ivMinigamePullStop") + r'''};
        private _deleted=[];private _clicks=0;
        ACME_fnc_ivUiValid={true};
        _row set [15,[true,true,true,true,true,16,true]];
        _patient setVariable ["ACME_IV_Marks",[_row]];
        uiNamespace setVariable ["ACME_IV_Patient",_patient];
        uiNamespace setVariable ["ACME_IV_PullIdx",0];
        uiNamespace setVariable ["ACME_IV_PullUID","ivhub:7:1"];
        uiNamespace setVariable ["ACME_IV_PullKind","catheter"];
        uiNamespace setVariable ["ACME_IV_PullExtra",objNull];
        [true] call ACME_fnc_ivMinigamePullStop;
        [_events isEqualTo [] && {_removed isEqualTo []} && {_renders==1},
            "stale primary drag dispatched removal despite a secondary"] call _check;
        [(uiNamespace getVariable ["ACME_IV_PullIdx",0])==-1,
            "blocked primary drag retained its input session"] call _check;
    ''')
