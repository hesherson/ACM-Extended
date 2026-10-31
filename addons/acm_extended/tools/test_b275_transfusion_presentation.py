"""Production bag labels and warmer/service state with explicit UI boundaries."""
import pytest

from test_b275_piggyback import delivery_setup, fn, helpers
from test_b227_line_service_and_assessments import src
from test_menu_death_lifecycle import execute
from test_b273_transfusion_actions import setup as native_ui_setup


def presentation_setup():
    return delivery_setup() + r'''
        private _co=5;private _cpr=false;
        ace_medical_status_fnc_getCardiacOutput={_co};
        ACM_core_fnc_cprActive={_cpr};
        CBA_fnc_replace={params ["_value","_search","_replacement"];
            private _at=_value find _search;
            while {_at>=0} do {_value=(_value select [0,_at])+_replacement+(_value select [_at+count _search]);_at=_value find _search;};
            _value
        };
    ''' + "".join(fn(name) for name in (
        "isYLineAccess", "yServiceState", "fluidLabelVolume", "transfusionBagPresentation",
    ))


def test_connected_piggyback_rows_keep_role_labels_but_only_the_flowing_branch_is_orange():
    execute(presentation_setup() + r'''
        private _before=str (_patient getVariable "ACM_circulation_IV_Bags");
        private _a=[_patient,"leftarm",_primary,"Saline (500 mL)"] call ACME_fnc_transfusionBagPresentation;
        private _b=[_patient,"leftarm",_secondary,"Saline (100 mL)"] call ACME_fnc_transfusionBagPresentation;
        [(_a select 0) find "[PiB] · Primary">=0 && {(_b select 0) find "[PiB] · Secondary">=0},"connected roles missing from Fluids"] call _check;
        [(_a select 1) isEqualTo [0.79,0.73,0.89,1] && {!(_a select 4)},"held primary looked as though warming"] call _check;
        [(_b select 1) isEqualTo [1,.55,.13,1] && {_b select 4},"secondary temperature did not override purple fluid text"] call _check;
        [(_a select 2)=="LW Quantum · Inline" && {(_b select 2) find "LW Quantum · Warming"==0},"shared downstream warmer not shown on both roles"] call _check;
        [_before==str (_patient getVariable "ACM_circulation_IV_Bags"),"presentation mutated fluid custody"] call _check;
        _secondary set [1,0];
        _a=[_patient,"leftarm",_primary,"Saline"] call ACME_fnc_transfusionBagPresentation;
        _b=[_patient,"leftarm",_secondary,"Saline"] call ACME_fnc_transfusionBagPresentation;
        [_a select 4 && {!(_b select 4)},"completed secondary never transferred warming to primary"] call _check;
        [(_a select 1) isEqualTo [1,.55,.13,1] && {(_b select 1) isEqualTo [.79,.73,.89,1]},"temperature colors did not follow active branch"] call _check;
    ''')


@pytest.mark.parametrize("blocker", ["paused", "clamp", "zero-co", "arrest", "fraction", "detached", "unplugged"])
def test_warming_indicator_requires_real_usable_admitted_flow(blocker):
    change = {
        "paused": '(_patient getVariable "ACM_circulation_FluidBagsFlow_IV" select 2) set [0,0];',
        "clamp": 'private _entry=[];_entry set [20,20];_entry set [21,0];_entry set [22,-1];_entry set [23,"secondary"];_patient setVariable ["ACME_infusion_BagMedications",[_entry]];',
        "zero-co": "_co=0;",
        "arrest": '_patient setVariable ["ace_medical_inCardiacArrest",true];',
        "fraction": "_fraction=0;",
        "detached": '_patient setVariable ["ACME_detachedBags",["secondary"]];',
        "unplugged": '_patient setVariable ["ACME_IV_DisconnectedBagUIDs",["secondary"]];',
    }[blocker]
    execute(presentation_setup() + change + r'''
        private _row=[_patient,"leftarm",_secondary,"Saline"] call ACME_fnc_transfusionBagPresentation;
        [!(_row select 4) && {(_row select 2)=="LW Quantum · Inline"},"blocked fluid claimed active warming"] call _check;
        [(_row select 1) isEqualTo [.79,.73,.89,1],"blocked piggyback fluid stayed orange"] call _check;
    ''')


@pytest.mark.parametrize("second,tail", [(30,"."),(30.9,"."),(31,".."),(31.9,".."),(32,"..."),(33,".")])
def test_ellipsis_changes_only_on_whole_one_second_boundaries(second, tail):
    execute(presentation_setup() + f'''
        _nowTime={second};
        private _row=[_patient,"leftarm",_secondary,"Saline"] call ACME_fnc_transfusionBagPresentation;
        [(_row select 2)=="LW Quantum · Warming{tail}","warming dots cadence changed"] call _check;
    ''')


@pytest.mark.parametrize("primed,service,blood_flow,saline_flow", [
    (False,"",False,False), (False,"prime",False,True),
    (True,"",True,False), (True,"flush",False,True),
])
def test_y_warmer_tracks_primary_or_service_reserve_without_double_warming(primed, service, blood_flow, saline_flow):
    job = '[]' if not service else f'["leftarm",true,0,"secondary",25,5,100,_medic,1,[],"{service}",25,0,"service1"]'
    execute(presentation_setup() + f'''
        _patient setVariable ["ACME_PiggybackLines",createHashMap];
        _primary set [0,"Blood"];_secondary set [0,"ACME_SalineY"];
        _patient setVariable ["ACME_YLines",[_key]];
        _patient setVariable ["ACME_YLinePrimed",createHashMapFromArray [[_key,{str(primed).lower()}]]];
        _patient setVariable ["ACME_yFlushJobs",createHashMapFromArray [[_key,{job}]]];
        private _a=[_patient,"leftarm",_primary,"Blood 500 mL [Y] [Warmed]"] call ACME_fnc_transfusionBagPresentation;
        private _b=[_patient,"leftarm",_secondary,"Saline"] call ACME_fnc_transfusionBagPresentation;
        [(_a select 4) isEqualTo {str(blood_flow).lower()} && {{(_b select 4) isEqualTo {str(saline_flow).lower()}}},"wrong Y branch claimed flow"] call _check;
        [(_a select 0) find "[Y] [Y]"<0 && {{(_a select 0) find "[Y]">=0}} && {{(_b select 0) find "[Y]">=0}},"native Y labels missing or duplicated"] call _check;
        [count (_patient getVariable "ACME_lineWarmers")==1,"Y presentation fitted duplicate warmer"] call _check;
    ''')


def warmer_state_setup():
    return helpers() + r'''
        private _available=1;private _personal=1;
        ACME_fnc_treatmentSupplyCount={_available};
        ACME_fnc_itemCount={_personal};
        ace_common_fnc_getCountOfItem={_personal};
        ACME_fnc_carrierInventoryGet={objNull};
        uiNamespace setVariable ["ACME_lineWarmerConfirm",[]];
    ''' + fn("lineWarmerActionState")


@pytest.mark.parametrize("personal", [0,1,2])
def test_last_spare_confirmation_belongs_to_one_physical_uid_and_does_not_consume_stock(personal):
    execute(warmer_state_setup() + f'''
        _personal={personal};_available={personal};
        private _context=[_patient,_medic,1,"leftarm",true,0,"secondary"];
        uiNamespace setVariable ["ACME_lineWarmerConfirm",_context];
        private _state=[_patient,"leftarm",true,0,"secondary",_medic] call ACME_fnc_lineWarmerActionState;
        [_state isEqualTo [true,false,{personal},{str(personal == 1).lower()},true],"last-spare state wrong"] call _check;
        [count (_patient getVariable ["ACME_lineWarmers",createHashMap])==0 && {{_personal=={personal}}},"presentation spent or fitted warmer"] call _check;
        [_patient,"leftarm",true,0,"primary",_medic] call ACME_fnc_lineWarmerActionState;
        [(uiNamespace getVariable "ACME_lineWarmerConfirm") isEqualTo [],"bag selection retained someone else's confirmation"] call _check;
    ''')


def test_empty_connected_bag_still_offers_removal_of_the_single_fitted_warmer():
    execute(warmer_state_setup() + r'''
        _secondary set [1,0];
        _patient setVariable ["ACME_lineWarmers",createHashMapFromArray [[_key,true]]];
        private _state=[_patient,"leftarm",true,0,"secondary",_medic] call ACME_fnc_lineWarmerActionState;
        [_state select 0 && {_state select 1} && {(_state select 2)==0},"empty connected bag stranded downstream warmer"] call _check;
    ''')


def flush_click_setup():
    source = src("transfusionFlushLine").replace("findDisplay 86000", "_displayFixture")
    source = source.replace("isNull (_displayFixture)", "(_displayFixture isEqualTo objNull)")
    source = source.replace("isNull ACE_player", "(ACE_player isEqualTo objNull)")
    source = source.replace("netId ACE_player", '"provider"')
    return presentation_setup() + r'''
        private _displayFixture=missionNamespace;
        _patient setVariable ["ACME_PiggybackLines",createHashMap];
        _primary set [0,"ACME_Empty"];_primary set [1,0];
        _secondary set [0,"ACME_SalineY"];
        _patient setVariable ["ACME_YLines",[_key]];
        _patient setVariable ["ACME_YLinePrimed",createHashMapFromArray [[_key,true]]];
        ACM_circulation_TransfusionMenu_Target=_patient;
        ACM_circulation_TransfusionMenu_Selected_BodyPart="leftarm";
        ACM_circulation_TransfusionMenu_SelectIV=true;
        ACM_circulation_TransfusionMenu_Selected_AccessSite=0;
        private _selected=[_patient,"leftarm",1,"ACME_SalineY",100,0,true,-1,100,-1,-1,"secondary",""];
        ACME_fnc_getSelectedActiveBagContext={_selected};
        _patient setVariable ["ACME_yFlushJobs",createHashMap];
    ''' + fn("yServicePlan") + "ACME_fnc_transfusionFlushLine={" + source + "};"


@pytest.mark.parametrize("selected,allow", [("reserve",True),("blood",False),("foreign-uid",False),("neighbor",False)])
def test_flush_click_is_guarded_by_the_exact_selected_reserve_uid(selected, allow):
    change = {
        "reserve":"",
        "blood":'_selected set [2,0];_selected set [3,"Blood"];',
        "foreign-uid":'_secondary set [8,"replacement"];_selected set [2,0];_selected set [3,"Saline"];',
        "neighbor":'_selected set [5,1];',
    }[selected]
    execute(flush_click_setup() + change + f'''
        private _allowed=["auto"] call ACME_fnc_transfusionFlushLine;
        [_allowed isEqualTo {str(allow).lower()} && {{count _events=={int(allow)}}},"non-reserve click reached owner service route"] call _check;
    ''')


@pytest.mark.parametrize("change,allowed,index", [
    ("reorder", True, 4), ("missing", False, -1),
    ("replacement", False, -1), ("access", False, -1),
    ("io", False, -1), ("legacy-volume", True, 1), ("legacy-replaced", False, -1),
])
def test_selected_bag_re_resolves_uid_and_latest_volume_without_retargeting_an_access(change, allowed, index):
    mutation = {
        "reorder": '_physical=[_physical select 0,_physical select 4,_physical select 2,_physical select 3,_physical select 1];(_physical select 4) set [1,123];',
        "missing": '_physical deleteAt 1;',
        "replacement": '(_physical select 1) set [8,"replacement"];',
        "access": '(_physical select 1) set [3,1];',
        "io": '(_physical select 1) set [4,false];',
        "legacy-volume": '(_selection select 0) resize 9;(_physical select 1) set [1,123];',
        "legacy-replaced": '(_selection select 0) resize 9;(_physical select 1) set [0,"Plasma"];',
    }[change]
    execute(native_ui_setup() + r'''
        (_selection select 0) set [9,"blood"];
    ''' + mutation + f'''
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",_physical]]];
        private _context=["transfusion"] call ACME_fnc_getSelectedActiveBagContext;
        [(_context isNotEqualTo []) isEqualTo {str(allowed).lower()},"stale bag selection retargeted a replacement/access"] call _check;
        if ({str(allowed).lower()}) then {{
            [(_context select 2)=={index} && {{(_context select 3)=="Blood"}} && {{(_context select 10)==123}},"resolver retained stale index or volume"] call _check;
        }};
        [_selectionWrites isEqualTo [],"context read changed UI selection"] call _check;
    ''')


@pytest.mark.parametrize("changed", ["selection", "successor", "cancel-successor"])
def test_native_move_progress_keeps_captured_destination_and_cannot_consume_a_successor(changed):
    execute(native_ui_setup() + r'''
        private _progress=[];private _reopened=[];
        ACM_core_fnc_progressBarAction={_progress=_this;};
        ACM_circulation_fnc_formatFluidBagName={"Fixture"};
        ACM_circulation_fnc_getFluidBagString={"Fixture"};
        ACM_core_fnc_getBodyPartString={"Fixture"};
        ace_common_fnc_getName={"Provider"};
        ace_medical_treatment_fnc_addToLog={};
        ACME_fnc_reopenTransfusion={_reopened pushBack _this;};
        [] call ACM_circulation_fnc_TransfusionMenu_MoveBag;
        ACM_circulation_TransfusionMenu_Selected_BodyPart="rightarm";
        ACM_circulation_TransfusionMenu_Selected_AccessSite=2;
        [] call ACM_circulation_fnc_TransfusionMenu_MoveBag;
        private _args=_progress select 0;
        _events=[];
        ACM_circulation_TransfusionMenu_Selected_BodyPart="head";
        ACM_circulation_TransfusionMenu_Selected_AccessSite=1;
    ''' + ('missionNamespace setVariable ["ACME_moveToken","successor"];' if changed != "selection" else "") + f'''
        _args call (_progress select {2 if changed == "cancel-successor" else 1});
    ''' + (r'''
        [count _events==1 && {(_events select 0 select 2 select 4)=="rightarm"} && {(_events select 0 select 2 select 6)==2},"progress callback used later UI destination"] call _check;
        [count _reopened==1 && {(_reopened select 0 select 0 select 2)=="rightarm"},"progress return opened wrong access"] call _check;
    ''' if changed == "selection" else r'''
        [count _events==0 && {count _reopened==0},"old completion consumed/reopened successor move"] call _check;
    ''' if changed == "successor" else r'''
        [count _events==1 && {(_events select 0 select 2 select 3)=="cancel"} && {(_events select 0 select 2 select 8)==(_args select 8)},"cancel did not carry original token"] call _check;
        [count _reopened==0 && {missionNamespace getVariable "ACME_moveToken"=="successor"},"old cancel overwrote successor intent"] call _check;
    '''))
