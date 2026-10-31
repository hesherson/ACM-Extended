"""B304 executes compact production card layout and volume-anchored pump logic."""
import pytest
from test_menu_death_lifecycle import execute, read, ROOT
from test_b278_transfusion_geometry import renderer_setup
from test_b227_line_service_and_assessments import basic, fn, pump_setup

@pytest.mark.parametrize('pane,group,prepared',[(86004,86500,False),(86145,86530,True),(86127,86540,False)])
@pytest.mark.parametrize('offset',[0,1,3,99])
def test_five_compact_cards_scroll_with_exact_identity_and_stable_controls(pane,group,prepared,offset):
    execute(renderer_setup()+f'''
        uiNamespace setVariable ["ACME_preparedListMode",{str(prepared).lower()}];
        [missionNamespace] call ACME_fnc_updateTransfusionCards;
        missionNamespace setVariable ["ACME_txCardOffset_{pane}",{offset}];
        [missionNamespace] call ACME_fnc_updateTransfusionCards;
        private _window=[8,5,{offset}] call ACME_fnc_transfusionCardWindow;
        private _last=0;
        for "_slot" from 0 to 4 do {{
            private _group={group}+_slot;
            private _rect=_controlValues get format["%1:position",_group];
            private _id=[[_group,9],["ACME_txIdentity",[]]] call _controlRead;
            [_controlValues get format["%1:show",_group],"compact slot hidden"] call _check;
            [(_id select 2)==((_window select 1) select _slot),"scrolled slot targets wrong bag"] call _check;
            [(_rect select 1)>=_last,"compact cards overlap"] call _check;
            _last=(_rect select 1)+(_rect select 3);
            [(_rect select 3)<.05,"compact row still oversized"] call _check;
        }};
        private _viewport=_positions get {pane};
        [_last<=(_viewport select 1)+(_viewport select 3)+.00001,"fifth card escaped list"] call _check;
        private _before=count _writes;private _created=_creationCount;
        [missionNamespace] call ACME_fnc_updateTransfusionCards;
        [count _writes==_before && {{_creationCount==_created}},"identical update resized or rebuilt cards"] call _check;
    ''')

@pytest.mark.parametrize('pressure',[.04,.25,.5,1])
@pytest.mark.parametrize('remaining',[1000,900,500,1,0])
def test_pressure_tracks_actual_volume_and_retains_low_pressure(pressure,remaining):
    execute(basic()+fn('pressureLevel')+f'''
        private _cuff=[100,{pressure},"server",1000];
        private _level=[_cuff,{remaining}] call ACME_fnc_pressureLevel;
        [abs (_level-{pressure*remaining/1000})<.000001,"pressure not proportional to bag volume"] call _check;
        _serverTime=999999;CBA_missionTime=99999;
        [([_cuff,{remaining}] call ACME_fnc_pressureLevel)==_level,"held bag lost pressure on clock"] call _check;
        [([_cuff,1200] call ACME_fnc_pressureLevel)=={pressure},"adding fluid invented extra pressure"] call _check;
    ''')

def test_repump_uses_remaining_pressure_reanchors_and_ignores_replay():
    execute(pump_setup()+'''
        ["one"] call _pump;["two"] call _pump;
        private _bags=_patient getVariable "ACM_circulation_IV_Bags";
        ((_bags get "body") select 0) set [1,250];
        ["three"] call _pump;["three"] call _pump;
        private _c=(_patient getVariable "ACME_piCuffs") get "bag";
        [(_c select 1)==.5 && {(_c select 3)==250},"repump failed to reanchor or replay added pressure"] call _check;
        [abs (([_c,125] call ACME_fnc_pressureLevel)-.25)<.000001,"repumped bag decay wrong"] call _check;
    ''')

def test_pressure_popovers_remain_open_and_all_physical_readers_pass_volume():
    source=read('layoutTransfusionMenu')
    assert '} forEach [86007,86146,86120,86147,86134,86132,86133];' in source
    for name in ['pressureInfuserAttach','pressureInfuserCommit','pressureInfuserAck']:
        assert 'ACME_txActionMenu' not in read(name)
    assert 'serverTime' not in read('pressureLevel').split('params',1)[1]
    assert '[_cuff, _bag param [1,0]] call ACME_fnc_pressureLevel' in read('pressureInfuserPaint')
    assert '[_cuff, _x param [1,0]] call ACME_fnc_pressureLevel' in read('updateTransfusionLineDetails')
    assert ', _found select 1] call ACME_fnc_pressureLevel' in read('pressureInfuserCommit')
    for file in ['fnc_getIVFlowRate.sqf','fnc_getBloodVolumeChange.sqf']:
        s=(ROOT/'addons/circulation/functions'/file).read_text()
        assert '[_cuff] call ACME_fnc_pressureLevel' not in s

@pytest.mark.parametrize('row,valid',[
    ('[1,.5]',True),('[1,.5,"server"]',True),('[1,.5,"cba",500]',True),
    ('[1,.5,"server",1000]',True),('[1,.5,"server",0]',False),
    ('[1,.5,"server",-100]',False),('[1,.5,"server","500"]',False),
    ('[1,2,"server",500]',False),('[1,.5,"other",500]',False)])
def test_snapshot_validator_accepts_volume_anchor_and_rejects_malformed_record(row,valid):
    from test_historical_medication_rows import iteration_scopes
    from test_menu_death_lifecycle import adapt
    block=read('clinicalValidate').split('case "ACME_piCuffs": {',1)[1].split('case "ACME_infusion_BagMedications"',1)[0].rsplit('};',1)[0]
    execute('private _number={(_this select 0) isEqualType 0};private _bad=false;private _v=createHashMapFromArray [["bag",'+row+']];'+adapt(iteration_scopes(block))+f'[(!_bad) isEqualTo {str(valid).lower()},"bad cuff snapshot acceptance"] call _check;')

@pytest.mark.parametrize('remaining',[500,250])
def test_full_snapshot_roundtrip_retains_volume_anchor_across_clock_rebase(remaining):
    from test_b271_ptx_stability import restore_setup,function,execute as ptx_execute
    from test_historical_medication_rows import iteration_scopes
    from test_b288_clinical_persistence import ref_setup
    ptx_execute(restore_setup()+ref_setup()+iteration_scopes(function('clinicalSnapshot').replace('_clock - _at','_serverNow - _at'))+fn('pressureLevel')+f'''
        _patient setVariable ["ACME_piCuffs",createHashMapFromArray [["bag",[100,.8,"server",1000]]]];
        private _serverNow=100;private _snapshot=[_patient] call ACME_fnc_clinicalSnapshot;
        private _rows=_snapshot select 1;
        private _entry=(_rows select (_rows findIf {{(_x select 0)=="ACME_piCuffs"}})) select 1;
        private _decoded=[_entry,false] call ACME_fnc_clinicalCodec;
        private _cuff=_decoded get "bag";
        [count _cuff==4 && {{(_cuff select 3)==1000}},"save codec lost volume anchor"] call _check;
        [abs (([_cuff,{remaining}] call ACME_fnc_pressureLevel)-{.8*remaining/1000})<.00001,"clock rebase altered physical pressure"] call _check;
    ''')

@pytest.mark.parametrize('legacy',['[10,.75]','[10,.75,"server"]','[10,.75,"cba"]'])
def test_owner_migrates_legacy_cuff_once_and_does_not_publish_on_idle_ticks(legacy):
    from test_b227_line_service_and_assessments import src
    s=src('pressureInfuserTick')
    s=s.replace('{_x params ["_type", "_remaining"];','private _y=(_patient getVariable "ACM_circulation_IV_Bags") get _x;{_x params ["_type", "_remaining"];')
    s=s.replace('forEach (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]);','forEach keys (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]);')
    s=s.replace('    if (!(_x in _live))','    private _y=_cuffs get _x; if (!(_x in _live))').replace('forEach _cuffs;','forEach keys _cuffs;')
    execute(basic()+fn('pressureLevel')+'ACME_fnc_pressureInfuserTick={'+s+'};'+f'''
        private _writes=0;ACME_fnc_lineWarmerReturnsTick={{}};
        ACME_fnc_pressureInfuserStateCommit={{params ["_p","_kind","_value"];_writes=_writes+1;_p setVariable ["ACME_piCuffs",_value];}};
        _patient setVariable ["ACME_piCuffs",createHashMapFromArray [["bag",{legacy}],["gone",[0,1]]]];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[["Blood",500,0,0,false,-1,500,-1,"bag"]]]]];
        [_patient] call ACME_fnc_pressureInfuserTick;
        private _cuffs=_patient getVariable "ACME_piCuffs";private _c=_cuffs get "bag";
        [count _c==4 && {{(_c select 1)==.75}} && {{(_c select 3)==500}} && {{!("gone" in _cuffs)}},"legacy migration changed pressure or retained orphan"] call _check;
        [_patient] call ACME_fnc_pressureInfuserTick;
        [_writes==1,"idle maintenance rebroadcast unchanged cuff"] call _check;
    ''')

@pytest.mark.parametrize('remaining',[1000,500,100,0])
def test_real_access_rate_reads_only_the_named_bag_volume(remaining):
    from test_menu_death_lifecycle import adapt
    from test_b156_procedure_supplies import primitives
    s=(ROOT/'addons/circulation/functions/fnc_getIVFlowRate.sqf').read_text()
    execute(basic()+fn('pressureLevel')+'private _flow={'+primitives(adapt(s))+'};'+f'''
        ACME_fnc_aajtOccludes={{false}};
        _patient setVariable ["ACM_circulation_IO_Placement",[0,1,0,0,0,0]];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[["Saline",{remaining},0,0,false,-1,1000,-1,"bag"],["Saline",1000,0,0,false,-1,1000,-1,"other"]]]]];
        _patient setVariable ["ACME_piCuffs",createHashMapFromArray [["bag",[0,.8,"server",1000]]]];
        [abs (([_patient,1,false,0,-1,"bag"] call _flow)-{4.1667*(1+1.5*.8*remaining/1000)})<.00001,"access rate used stale pressure or another bag"] call _check;
        [abs (([_patient,1,false,0,-1,"other"] call _flow)-4.1667)<.00001,"cuff boosted a different bag"] call _check;
        [abs (([_patient,1,false,0,-1,"bag",true] call _flow)-4.1667)<.00001,"gravity-only secondary gained cuff boost"] call _check;
    ''')

@pytest.mark.parametrize('remaining,rate',[(1000,300),(500,200),(100,120),(0,0)])
def test_real_blood_envelope_tracks_volume_anchored_pressure(remaining,rate):
    from test_menu_death_lifecycle import adapt
    from test_b156_procedure_supplies import primitives
    s=(ROOT/'addons/circulation/functions/fnc_getBloodVolumeChange.sqf').read_text().split('// Blood has an explicit device/temperature flow envelope',1)[1].split('// Final perfusion gate',1)[0]
    s=primitives(adapt('//'+s)).replace('_unit getVariable','_patient getVariable')
    execute(basic()+fn('pressureLevel')+fn('lineWarmer')+fn('lineWarmerRate')+f'''
        private _unit=_patient;private _targetBodyPart="body";private _iv=false;private _accessSite=0;private _piggybackSecondary=false;
        private _type="Blood";private _coldFlag=true;private _warmedFlag=false;
        private _bagUid="bag";private _deltaT=1;private _bagVolumeRemaining={remaining};private _bagChange=2;
        _patient setVariable ["ACME_piCuffs",createHashMapFromArray [["bag",[100,1,"server",1000]]]];
        {s}
        [abs (_bagChange-{rate}/60)<.0001,"blood envelope disagrees with actual cuff volume"] call _check;
    ''')
