"""Exercise the server clock, shared blood Y warmer and physical IV kit."""
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


def test_opening_a_kit_debits_one_and_gives_matching_catheter_and_flush():
    kit = adapt(read("ivStartKitOpen")).replace("local _unit","true").replace("alive _unit","true")
    execute("private _open={" + kit + "};" + '''
        private _stock=1;private _supplies=[];private _commits=0;
        ACME_fnc_treatmentSupplyTake={if (_stock==0) exitWith {[]};_stock=0;[_patient,"ACME_IVStartKit_18g",objNull,"kit"]};
        ACME_fnc_treatmentSupplyRefund={if (_this select 1) exitWith {false};_commits=_commits+1;true};
        ace_common_fnc_addToInventory={_supplies pushBack (_this select 1);};
        [[_patient,"ACME_IVStartKit_18g"] call _open,"kit was not opened"] call _check;
        [!([_patient,"ACME_IVStartKit_18g"] call _open) && {_commits==1},"kit supplied duplicates"] call _check;
        [_supplies isEqualTo ["ACM_IV_18g","ACME_NARBOA","ACME_Tegaderm","ACME_SalineLock","ACME_IVExtension","ACME_IVLine","ACM_SalineFlush_10"],"kit contents are incomplete"] call _check;
    ''')
