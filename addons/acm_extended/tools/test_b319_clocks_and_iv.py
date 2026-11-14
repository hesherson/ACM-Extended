"""Exercise the server clock, shared blood Y warmer and physical IV kit."""
import pytest

from test_menu_death_lifecycle import adapt, execute, read


def test_server_clinical_clock_preserves_age_across_rate_changes():
    tick = adapt(read("clinicalClockTick"))
    tick = tick.replace("serverTime", "_nowTime").replace("timeMultiplier", "_multiplier")
    tick = tick.replace("accTime", "1").replace("isMultiplayer", "true")
    tick = tick.replace('_next remoteExecCall ["ACME_fnc_clinicalTimingSync",-2,"ACME_clinicalClockAnchor"]', "_publications pushBack +_next")
    execute("private _tick={" + tick + "};" + '''
        private _publications=[];private _multiplier=4;
        CBA_missionTime=10;_nowTime=100;
        missionNamespace setVariable ["ACME_clinicalTiming",[1,true,true,true,24,24,48,4,24,4,21,1]];
        call _tick;
        private _blood=[] call ACME_fnc_clinicalClock;
        private _med=[true] call ACME_fnc_clinicalClock;
        _nowTime=130;CBA_missionTime=40;
        [([] call ACME_fnc_clinicalClock)-_blood==120 && {([true] call ACME_fnc_clinicalClock)-_med==120},"4x did not apply to both domains"] call _check;
        _multiplier=2;call _tick;call _tick;
        [([] call ACME_fnc_clinicalClock)-_blood==120 && {count _publications==2},"rate transition jumped time or republished"] call _check;
        _nowTime=160;
        [([] call ACME_fnc_clinicalClock)-_blood==180 && {([true] call ACME_fnc_clinicalClock)-_med==180},"new rate did not carry prior age"] call _check;
        missionNamespace setVariable ["ACME_clinicalTiming",[]];
        call _tick;_nowTime=170;
        [([] call ACME_fnc_clinicalClock)-_blood==190,"wall time did not advance one second per second"] call _check;
    ''')


def test_automatic_y_warmer_requires_blood_and_stays_for_the_saline_flush():
    execute('''
        ACME_fnc_isYLineAccess={(_this select 3)==0};
        ACME_fnc_setVarNet={params ["_unit","_name","_value"];_unit setVariable [_name,_value];};
        private _saline=["ACME_SalineY",100,1,0,true,-1,500,-1,"saline"];
        private _blood=["Blood",300,1,0,true,0,500,-1,"blood"];
        private _rows=createHashMapFromArray [["leftarm",[_saline]]];
        _patient setVariable ["ACM_circulation_IV_Bags",_rows];
        [!([_patient,"leftarm",true,0,true] call ACME_fnc_yAutoWarmer),"saline-only set installed automatic warmer"] call _check;
        _rows set ["leftarm",[_saline,_blood]];
        [!([_patient,"leftarm",true,1,true] call ACME_fnc_yAutoWarmer),"warmer appeared on a neighboring access"] call _check;
        [[_patient,"leftarm",true,0,true] call ACME_fnc_yAutoWarmer,"blood Y did not install a warmer"] call _check;
        _rows set ["leftarm",[_saline]];
        [[_patient,"leftarm",true,0] call ACME_fnc_yAutoWarmer,"saline lost its shared warmer after the blood bag came out"] call _check;
        ACME_fnc_isYLineAccess={false};
        [!([_patient,"leftarm",true,0] call ACME_fnc_yAutoWarmer),"disconnected Y still warmed"] call _check;
    ''')


def kit_runtime(stock):
    kit = adapt(read("ivStartKitUnpack")).replace("local _unit", "true").replace("alive _unit", "true")
    for native, fixture in (
        ("is3DEN", "false"), ("items _unit", "+_stock"),
        ("uniformContainer _unit", "_medic"), ("vestContainer _unit", "objNull"),
        ("backpackContainer _unit", "objNull"), ("itemCargo _container", "+_stock"),
        ("itemCargo _x", "+_stock"),
        ("_container canAdd [_class,_count]", "([_class,_count] call _canAdd)"),
        ('_container addItemCargoGlobal [_kit,-1]', '[_kit,-1] call _adjust'),
        ('_container addItemCargoGlobal [_class,_count]', '[_class,_count] call _adjust'),
        ('_container addItemCargoGlobal _x', '_x call _adjust'),
        ('_container addItemCargoGlobal [_kit,1]', '[_kit,1] call _adjust'),
    ):
        kit = kit.replace(native, fixture)
    runtime = adapt(read("registerIVStartKitRuntime"))
    runtime = runtime.replace("local _unit", "true").replace("is3DEN", "false").replace("ACE_player", "_patient")
    return "private _stock=" + stock + ";" + r'''
        private _queued=[];private _take={};private _close={};
        private _cannotFit="";private _partialIssue=false;
        private _canAdd = {(_this select 0) != _cannotFit};
        private _adjust = {
            params ["_class","_amount"];
            if (_partialIssue && {_class=="ACM_IV_18g"} && {_amount==2}) then {_amount=1;};
            if (_amount < 0) then {
                for "_i" from 1 to (-_amount) do {_stock deleteAt (_stock find _class);};
            } else {
                for "_i" from 1 to _amount do {_stock pushBack _class;};
            };
        };
        private _runQueued={{(_x select 1) call (_x select 0);} forEach _queued;_queued=[];};
        CBA_fnc_addClassEventHandler={switch (_this select 1) do {
            case "Take": {_take=_this select 2;};
            case "InventoryClosed": {_close=_this select 2;};
        }};
        CBA_fnc_addEventHandler={};
        CBA_fnc_addPlayerEventHandler={};
        BIS_fnc_addScriptedEventHandler={};
        CBA_fnc_execNextFrame={_queued pushBack _this;};
    ''' + "ACME_fnc_ivStartKitUnpack={" + kit + "}; call {" + runtime + "};"


CONTENTS = '["ACM_IV_18g","ACM_IV_18g","ACME_NARBOA","ACME_Tegaderm","ACME_SalineLock","ACM_SalineFlush_10"]'


@pytest.mark.parametrize("gauge", [14, 16, 18, 20])
def test_pickup_replaces_one_kit_with_standard_supplies_even_on_replay(gauge):
    execute(kit_runtime("[]") + f'''
        private _selected="ACME_IVStartKit_{gauge}g";
        [_patient,objNull,"ACME_Tegaderm"] call _take;
        [count _queued==0,"unrelated inventory item queued an unpack"] call _check;
        _stock pushBack _selected;
        [_patient,objNull,_selected] call _take;
        [_patient,objNull,_selected] call _take;
        [count _queued==2 && {{_stock isEqualTo [_selected]}},"pickup did not defer until inventory settled"] call _check;
        call _runQueued;
        [_stock isEqualTo {CONTENTS},"kit contents were lost, changed or duplicated"] call _check;
    ''')


@pytest.mark.parametrize("failure", ['_cannotFit="ACM_SalineFlush_10";', '_partialIssue=true;'])
def test_unpack_failure_keeps_kit_and_existing_supplies_and_retries_on_inventory_close(failure):
    execute(kit_runtime('["ACM_IV_18g","ACME_IVStartKit_18g"]') + failure + f'''
        [_patient,objNull,"ACME_IVStartKit_18g"] call _take;
        call _runQueued;
        [_stock isEqualTo ["ACM_IV_18g","ACME_IVStartKit_18g"],"failed unpack lost the kit or changed loose stock"] call _check;
        _cannotFit="";_partialIssue=false;
        [_patient,objNull] call _close;
        call _runQueued;
        [_stock isEqualTo (["ACM_IV_18g"] + {CONTENTS}),"inventory close did not restore all supplies"] call _check;
    ''')
