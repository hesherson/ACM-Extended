"""B227 production SQF execution: owner-serialized Y servicing, measured delivery,
line-specific warming, pump decay, monotonic countdown and compact annotation layout.
Arma UI, physiology admission and object commands are explicit engine-boundary fixtures.
These are not live Arma presentation or dedicated-server validation.
"""
import math
import re
import pytest
from test_menu_death_lifecycle import ROOT, F, read, adapt, execute
from test_b156_procedure_supplies import primitives
from test_b222_suction_input import block
from test_historical_medication_rows import iteration_scopes


def src(name):
    s=read(name).replace('serverTime','_serverTime')
    # SQF-VM has no finite command; emulate finite scalar samples at the engine boundary.
    s=re.sub(r'\bfinite (\(_job select _x\)|_\w+)',r'(\1 call _finite)',s)
    if name=='pressureInfuserCommit':
        # SQF-VM lacks Arma's forEach HASHMAP overload. Preserve key/value iteration,
        # body and exitWith, only adapting the container enumeration engine boundary.
        s=s.replace('private _i = _y findIf', 'private _y = (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) get _x; private _i = _y findIf')
        s=s.replace('forEach (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]);', 'forEach keys (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]);')
    # Handled by the running game; fixtures only emulate finite namespace/object commands.
    s=s.replace('objNull,[objNull]','objNull,[profileNamespace]')
    return primitives(adapt(iteration_scopes(s)))


def fn(name):
    return 'ACME_fnc_'+name+'={'+src(name)+'};'


def basic():
    return '''
    private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
    private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
    private _serverTime=100;
    private _liveEpoch=1;private _accessValid=true;private _hasY=true;private _notices=[];
    ACME_fnc_clinicalEpoch={_liveEpoch};
    ACME_fnc_patientInteractionDistance={_distance};
    ACME_fnc_setVarNet={params ["_unit","_key","_value"];_unit setVariable [_key,_value];};
    ACME_fnc_clinicalNotice={_notices pushBack _this;};
    ACME_fnc_transfusionAccessValid={_accessValid};
    ACME_fnc_isYLineAccess={_hasY};
    '''+fn('yServiceJobValid')


@pytest.mark.parametrize('elapsed,duration,previous,want',[
    (0,8,[-1,0],8),(2,8,[8,0],6),(4,7,[5,.2],3),
    (4,9,[3,.5],3),(5,10,[3,.5],3),(20,21,[2,.9],1),
    (9,8,[1,.9],1),(5,8,[2,.7],2)])
def test_airway_readout_never_restarts_or_moves_progress_backward(elapsed,duration,previous,want):
    execute(fn('assessmentReadout')+f'''
      private _r=[{elapsed},{duration},{previous},false] call ACME_fnc_assessmentReadout;
      [(_r select 0)=={want},"remaining time restarted"] call _check;
      [(_r select 1)>={previous[1]} && {{(_r select 1)<1}},"progress regressed/finished early"] call _check;
      [[{elapsed},{duration},_r,true] call ACME_fnc_assessmentReadout isEqualTo [0,1],"completion never settled"] call _check;
    ''')


@pytest.mark.parametrize('available,dirty,primed,blood,running,mode,reserved,allowed,amount',[
    (500,False,False,True,'','prime',0,True,25),
    (24,False,False,False,'','prime',0,False,0),
    (25,False,False,False,'','prime',0,True,25),
    (500,False,True,False,'','prime',0,False,0),
    (500,False,False,False,'prime','prime',25,False,0),
    (500,False,False,False,'','flush',0,False,0),
    (500,True,True,True,'','flush',0,False,0),
    (24,True,True,False,'','flush',0,False,0),
    (25,True,True,False,'','flush',0,True,25),
    (49,True,True,False,'','flush',0,True,25),
    (50,True,True,False,'','flush',0,True,50),
    (49,False,True,False,'','flush',0,False,0),
    (100,False,True,False,'flush','flush',50,True,50),
    (99,True,True,False,'flush','flush',50,False,0),
    (500,True,True,False,'prime','flush',25,False,0),
    (500,True,True,False,'','bad',0,False,0)])
def test_service_planner_same_predicate_for_ui_and_owner(available,dirty,primed,blood,running,mode,reserved,allowed,amount):
    execute(fn('yServicePlan')+f'''
      private _r=["{mode}",{available},{reserved},{str(blood).lower()},{str(dirty).lower()},{str(primed).lower()},"{running}"] call ACME_fnc_yServicePlan;
      [(_r select 0) isEqualTo {str(allowed).lower()} && {{(_r select 1)=={amount}}},"wrong service quantity/eligibility"] call _check;
    ''')


def service_setup():
    return basic()+'''
      ACME_infusion_bodyParts=["head","body","leftarm","rightarm","leftleg","rightleg"];
      private _ioCalls=0;ACME_fnc_ioPainResponse={_ioCalls=_ioCalls+1;};private _credited=0;private _waste=0;private _admissionRate=1;private _fraction=1; private _co=5; private _cpr=false;
      ace_medical_status_fnc_getCardiacOutput={_co}; ACM_core_fnc_cprActive={_cpr};
      ACM_circulation_fnc_getIVFlowRate={_admissionRate};ACME_fnc_medicationLineFraction={_fraction};
      ACME_fnc_fluidCommit={_credited=_credited+(_this select 5);};
      ACM_circulation_fnc_setRuntimeState={params ["_p","_rows"];{_p setVariable ["ACM_circulation_Saline_Volume",_x select 1];} forEach _rows;};
      ACME_fnc_ivBagsCommit={params ["_p","_map"];_p setVariable ["ACM_circulation_IV_Bags",_map];};
      ACME_fnc_bagIdentity={"reserve"};
      private _key="body#false#0";
      private _stock={((_patient getVariable "ACM_circulation_IV_Bags") get "body") select 0 select 1};
      private _init={params ["_amount",["_dirty",true],["_primed",true],["_blood",0]];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[
          ["ACME_SalineY",_amount,0,0,false,-1,500,-1,"reserve"],
          ["Blood",_blood,0,0,false,-1,500,-1,"blood"],
          ["Saline",99,0,1,true,-1,100,-1,"other-site"]
        ]]]];
        _patient setVariable ["ACME_YLineDirty",createHashMapFromArray [[_key,_dirty]]];
        _patient setVariable ["ACME_YLinePrimed",createHashMapFromArray [[_key,_primed]]];
        _patient setVariable ["ACME_yFlushJobs",createHashMap];
        _patient setVariable ["ACME_yServiceReceipts",createHashMap];
        _patient setVariable ["ACM_circulation_Saline_Volume",0];
      };
      private _request={params ["_mode","_id"];private _j=(_patient getVariable "ACME_yFlushJobs") get _key; private _jid=if (isNil "_j") then {""} else {_j param [13,""]}; [_patient,_medic,"body",false,0,_liveEpoch,_mode,_id,_serverTime,"reserve",_jid] call ACME_fnc_yFlushStart;};
      private _advance={params ["_seconds"];for "_i" from 1 to _seconds do {
        _serverTime=_serverTime+1;_nowTime=_nowTime+1;[_patient] call ACME_fnc_yFlushTick;
      };};
    '''+fn('yServicePlan')+fn('yServiceState')+fn('yFlushStart')+fn('yFlushTick')


@pytest.mark.parametrize('clicks',[1,2,3,5])
def test_each_flush_click_reserves_fifty_and_native_owner_delivers_exactly_once(clicks):
    execute(service_setup()+f'''
      [500] call _init;
      for "_n" from 1 to {clicks} do {{["flush",str _n] call _request;}};
      private _job=(_patient getVariable "ACME_yFlushJobs") get _key;
      [1+count (_job select 9)=={clicks},"click queue not retained"] call _check;
      [{clicks*5+3}] call _advance;
      [abs (call _stock-(500-{clicks*50}))<.01,"saline debit incorrect"] call _check;
      [abs (_credited-{clicks*50})<.01,"patient fluid credited wrong/doubled"] call _check;
      [abs ((_patient getVariable "ACM_circulation_Saline_Volume")-{clicks*.05})<.0001,"saline compartment not matched"] call _check;
      [count (_patient getVariable "ACME_yFlushJobs")==0,"finished service orphaned"] call _check;
      [!((_patient getVariable "ACME_YLineDirty") get _key),"completed flush still dirty"] call _check;
      [((_patient getVariable "ACM_circulation_IV_Bags") get "body" select 2 select 1)==99,"other site altered"] call _check;
    ''')


@pytest.mark.parametrize('available,expected',[(24,0),(25,25),(49,25),(50,50),(75,50)])
def test_required_post_two_unit_flush_minimum_and_preference(available,expected):
    execute(service_setup()+f'''
      [{available}] call _init;["flush","one"] call _request;[8] call _advance;
      [abs (_credited-{expected})<.01,"required clearing quantity incorrect"] call _check;
      [abs (call _stock-({available}-{expected}))<.01,"minimum flush drained wrong amount"] call _check;
      [((_patient getVariable "ACME_YLineDirty") get _key) isEqualTo {str(expected==0).lower()},"dirty flag inconsistent with actual minimum"] call _check;
    ''')


@pytest.mark.parametrize('cancel',[0,1,2,3])
def test_right_click_cancels_only_unstarted_tail_and_never_refunds_delivered_fluid(cancel):
    execute(service_setup()+f'''
      [500] call _init;
      {{["flush",_x] call _request;}} forEach ["one","two","three"];
      [2] call _advance;
      for "_i" from 1 to {cancel} do {{["cancel",format ["c%1",_i]] call _request;}};
      [{20}] call _advance;
      [abs (_credited-{max(1,3-cancel)*50})<.01,"cancel modified active/repaid saline"] call _check;
      [abs (call _stock-(500-_credited))<.01,"cancel refunded drained stock"] call _check;
    ''')


@pytest.mark.parametrize('blood',[0,500])
def test_prime_credits_twenty_five_to_patient_and_cannot_be_repeated(blood):
    execute(service_setup()+f'''
      [100,false,false,{blood}] call _init;
      ["prime","prime1"] call _request;["prime","prime2"] call _request;
      [7] call _advance;
      [(_patient getVariable "ACME_YLinePrimed") get _key,"priming did not finish"] call _check;
      [abs (call _stock-75)<.01 && {{_credited==25}},"prime patient credit or debit incorrect"] call _check;
      ["prime","prime3"] call _request;[7] call _advance;
      [abs (call _stock-75)<.01,"primed line drained again"] call _check;
    ''')


@pytest.mark.parametrize('reject',['duplicate','expired','epoch','distant','down','noaccess','noy','refill'])
def test_invalid_or_duplicate_service_does_not_mutate_queue(reject):
    change={
      'duplicate':'["flush","id"] call _request;',
      'expired':'_issued=80;',
      'epoch':'_sendEpoch=0;',
      'distant':'_distance=8;',
      'down':'_medic setVariable ["ACE_isUnconscious",true];',
      'noaccess':'_accessValid=false;',
      'noy':'_hasY=false;',
      'refill':'_patient setVariable ["ACME_yRefillClaims",createHashMapFromArray [[_key,[_medic,"refill","blood",_serverTime,_liveEpoch]]]];'
    }[reject]
    execute(service_setup()+f'''
      [500] call _init;private _issued=_serverTime;private _sendEpoch=_liveEpoch;{change}
      [_patient,_medic,"body",false,0,_sendEpoch,"flush","id",_issued,"reserve"] call ACME_fnc_yFlushStart;
      [8] call _advance;
      [_credited=={50 if reject=='duplicate' else 0},"invalid/duplicate request delivered extra fluid"] call _check;
    ''')


@pytest.mark.parametrize('cause',['paused','occluded','blood','epoch','removed','dead','bag-changed'])
def test_owner_tick_honors_flow_and_lifecycle_after_queueing(cause):
    change={
      'paused':'_patient setVariable ["ACM_circulation_FluidBagsFlow_IO",[1,0,1,1,1,1]];',
      'occluded':'_admissionRate=0;',
      'blood':'private _m=_patient getVariable "ACM_circulation_IV_Bags";(_m get "body" select 1) set [1,500];',
      'epoch':'_liveEpoch=2;',
      'removed':'_accessValid=false;',
      'dead':'_patientAlive=false;',
      'bag-changed':'private _m=_patient getVariable "ACM_circulation_IV_Bags";(_m get "body" select 0) set [8,"replacement"];'
    }[cause]
    execute(service_setup()+f'''
      [500] call _init;["flush","one"] call _request;{change}[6] call _advance;
      [call _stock==500 && {{_credited==0}},"blocked/stale line was flushed"] call _check;
      [(_patient getVariable "ACME_YLineDirty") get _key,"unflushed line marked clean"] call _check;
    ''')


@pytest.mark.parametrize('fraction',[0,.25,.75,1])
def test_flush_accounting_uses_actual_patient_admission_not_nominal_reserve_drain(fraction):
    execute(service_setup()+f'''
      [100] call _init;_fraction={fraction};["flush","one"] call _request;[6] call _advance;
      [abs (_credited-{50*fraction})<.01,"admission not applied"] call _check;
      [call _stock==50,"reserve should drain actual tubing amount"] call _check;
    ''')


@pytest.mark.parametrize('pump,age',[ (p,t) for p in [0,.25,.5,.75,1] for t in [0,60,120,240]])
def test_pressure_bar_and_drainer_share_the_same_decaying_level(pump,age):
    expected=pump*2**(-age/60)
    if expected<.08:expected=0
    execute(basic()+fn('pressureLevel')+f'''
      private _p=[[100-{age},{pump},"server"],60] call ACME_fnc_pressureLevel;
      [abs (_p-{expected})<.0001,"pressure level disagrees with decay"] call _check;
      CBA_missionTime=5000;
      [abs (([[100-{age},{pump},"server"],60] call ACME_fnc_pressureLevel)-_p)<.0001,"owner-local clock changed pressure"] call _check;
    ''')


@pytest.mark.parametrize('name,want',[
    ('Amiodarone','Ami'),('Epinephrine','Epi'),('Norepinephrine','Norepi'),
    ('CalciumChloride','CaCl'),('CalciumGluconate','CaGlu'),('Lidocaine','Lido'),
    ('Magnesium','Mag'),('Fentanyl','Fent'),('Ketamine','Ket'),('Propofol','Prop'),('Rocuronium','Roc')])
def test_clinical_keys_unchanged_but_infusion_displays_use_requested_aliases(name,want):
    execute(fn('infusionName')+f'[["{name}"] call ACME_fnc_infusionName=="{want}","wrong infusion shorthand"] call _check;')


@pytest.mark.parametrize('left,right',[(.48,.5),(.49,.49),(.01,.02),(.94,.95)])
@pytest.mark.parametrize('width',[.06,.12,.18])
def test_bilateral_tags_keep_compact_rectangles_inside_canvas_without_overlap(left,right,width):
    execute(fn('transfusionTagRect')+f'''
      private _first=[[{left},.2,.02,.02],[{width},.03],[0,0,1,1],[],.005,true] call ACME_fnc_transfusionTagRect;
      private _second=[[{right},.2,.02,.02],[{width},.03],[0,0,1,1],[_first],.005,false] call ACME_fnc_transfusionTagRect;
      [count _first==4 && {{count _second==4}},"labels disappeared with ample room"] call _check;
      {{[_x select 0>=0 && {{(_x select 0)+(_x select 2)<=1.001}},"tag outside map"] call _check;}} forEach [_first,_second];
      [((_first select 0)+{width}<=(_second select 0)) || {{(_second select 0)+{width}<=(_first select 0)}} || {{abs ((_first select 1)-(_second select 1))>=.03}},"bilateral labels overlap"] call _check;
    ''')


@pytest.mark.parametrize('site,iv',[(0,False),(0,True),(1,True),(2,True)])
def test_inline_warmer_persists_across_bags_but_not_other_sites(site,iv):
    execute(basic()+fn('lineWarmer')+f'''
      private _supply=1;ACME_fnc_treatmentSupplyCount={{_supply}};
      [[_patient,"body",{str(iv).lower()},{site},true,_medic] call ACME_fnc_lineWarmer,"warm fitting failed"] call _check;
      _supply=0;_patient setVariable ["ACME_warmedBlood",false];
      [[_patient,"body",{str(iv).lower()},{site}] call ACME_fnc_lineWarmer,"warmer lost between bags"] call _check;
      [!([_patient,"body",{str(iv).lower()},{site+1}] call ACME_fnc_lineWarmer),"other access inherited warmth"] call _check;
    ''')


def test_actual_marker_snapshot_codec_preserves_server_clock_age_on_save():
    s=read('clinicalSnapshot')
    assert 'CBA_missionTime - ((serverTime - _at) max 0)' in s
    assert '_entry set [2, ["cba", true]' in s
    assert '_j set [6, if (count _j >= 13) then {serverTime}' in read('clinicalRestore')
    assert 'count _c in [2,3]' in read('clinicalValidate')


def test_no_obsolete_catheter_inspection_actions_are_advertised():
    s=(ROOT/'addons/core/ACE_Medical_Treatment_Actions.hpp').read_text()
    assert not re.search(r'class\s+InspectIV_(Upper|Middle|Lower)\b',s)
    # Retain callable compatibility functions rather than making external calls nil.
    assert (ROOT/'addons/circulation/functions/fnc_inspectIV.sqf').exists()


def test_clamp_uses_persistent_change_only_text_not_rebuilt_mouse_tooltips_or_dose_rate():
    s=read('updateClampDialog')
    assert 'RscText' in s and '86210' in s
    assert 'ctrlSetTooltip _hint' not in s
    assert 'nominal' not in s.lower() and 'mg/min' not in s
    rate=read('formatRate')
    assert 'mg/min' not in rate and 'nominal' not in rate.lower()
    assert 'ctrlText _ctrlInfo' in s or 'ctrlText _readout' in s


def test_crouch_return_flag_is_consumed_before_old_menu_pose_clears_it():
    s=read('menuPoseStart')
    assert s.index('private _requestedAfterTreatment') < s.index('[_medic, true] call ACME_fnc_menuPoseStop;', s.index('private _oldState'))
    assert 'private _afterTreatment = _requestedAfterTreatment;' in s
    assert '"ACM_GenericContinuous"' in read('assessmentStop')
    assert '"ACM_GenericContinuous"' in read('assessmentReopen')


def test_flush_placement_mouse_semantics_and_disabled_styles():
    s=read('updateTransfusionControls')
    assert 'then{[_ctrlFlush]}' in s.replace(' ','')
    assert 'private _ctrlPrime' not in s
    assert '_stack append [_ctrlMove,_ctrlPullBag' in s
    assert '_bagRowSelected' in s[s.index('if (!isNull _ctrlMove) then {',s.index('// ACM\'s native move')):]
    cfg=(ROOT/'addons/acm_extended/config.cpp').read_text()
    pull=block(cfg,'class ACME_PullBagButton:')
    assert 'colorDisabled[]' in pull and 'colorBackgroundDisabled[]' in pull
    paint=read('transfusionServicePaint')
    assert 'Flush In Progress... (%1)' in paint and 'MouseButtonDown' in paint and 'cancel' in paint


def test_debug_layout_unchanged_from_b226():
    import subprocess
    p='addons/acm_extended/functions/fn_debugMenuClinical.sqf'
    base=subprocess.check_output(['git','show','78479131fbce624659e83e8132034dd778ef17cc:'+p],cwd=ROOT)
    assert (ROOT/p).read_bytes()==base


def pump_setup():
    return basic()+fn('pressureLevel')+fn('pressureInfuserCommit')+'''
      private _supply=1; private _acks=[];
      ACME_fnc_treatmentSupplyCount={_supply};
      CBA_fnc_targetEvent={_acks pushBack _this;};
      ACME_fnc_pressureInfuserStateCommit={params ["_p","_kind","_value"];_p setVariable [["ACME_piCuffs","ACME_piReceipts"] select (_kind=="receipts"),_value];};
      _patient setVariable ["ACM_circulation_IV_Bags", createHashMapFromArray [["body",[["Blood",500,0,0,false,-1,500,-1,"bag"]]]]];
      _patient setVariable ["ACME_piReceipts",createHashMap];
      _patient setVariable ["ACME_piCuffs",createHashMap];
      private _pump={params ["_id"];[_patient,_medic,"bag",1,_id,_serverTime,true,false,"pump-b227"] call ACME_fnc_pressureInfuserCommit;};
      private _level={private _c=(_patient getVariable "ACME_piCuffs") getOrDefault ["bag",[]];[_c] call ACME_fnc_pressureLevel;};
    '''.replace('(_patient getVariable "ACME_piCuffs") getOrDefault ["bag",[]]', '[_patient getVariable "ACME_piCuffs",["bag",[]]] call _mapDefault')


@pytest.mark.parametrize('count',[1,2,3,4,6])
def test_owner_pump_commit_increments_once_per_click_and_clamps_at_full(count):
    execute(pump_setup()+f'''
      for "_i" from 1 to {count} do {{[str _i] call _pump;[str _i] call _pump;}};
      [abs (call _level-{min(count*.25,1)})<.0001,"duplicate pumping or wrong increment"] call _check;
      _serverTime=160;[abs (call _level-{min(count*.25,1)*.5})<.0001,"pressure did not fall with clock"] call _check;
      _supply=0;["repump"] call _pump;
      [abs (call _level-{min(min(count*.25,1)*.5+.25,1)})<.0001,"existing cuff required second physical item"] call _check;
    ''')


@pytest.mark.parametrize('case',['expired','future','wrong-epoch','distant','down','no-cuff','missing-bag'])
def test_owner_rejects_invalid_modern_pump_requests(case):
    setup={
      'expired':'_issued=80;', 'future':'_issued=104;', 'wrong-epoch':'_liveEpoch=2;',
      'distant':'_distance=8;', 'down':'_medic setVariable ["ACE_isUnconscious",true];',
      'no-cuff':'_supply=0;', 'missing-bag':'_patient setVariable ["ACM_circulation_IV_Bags",createHashMap];'
    }[case]
    execute(pump_setup()+f'''
      private _issued=_serverTime;{setup}
      [_patient,_medic,"bag",1,"bad",_issued,true,false,"pump-b227"] call ACME_fnc_pressureInfuserCommit;
      [call _level==0,"invalid pump changed physical pressure"] call _check;
    ''')


@pytest.mark.parametrize('cold,warm,p,rate',[
    (True,False,0,100),(True,False,.25,150),(True,False,.5,200),(True,False,1,300),
    (False,True,0,200),(False,True,.25,225),(False,True,.5,250),(False,True,1,300)])
def test_real_blood_drainer_interpolates_tier_instead_of_binary_infinite_pressure(cold,warm,p,rate):
    original=(ROOT/'addons/circulation/functions/fnc_getBloodVolumeChange.sqf').read_text()
    work=original.split('// Blood has an explicit device/temperature flow envelope',1)[1].split('// Final perfusion gate',1)[0]
    work=primitives(adapt('//' + work)).replace('_unit getVariable','_patient getVariable')
    execute(basic()+fn('pressureLevel')+f'''
      private _type="Blood";private _coldFlag={str(cold).lower()};private _warmedFlag={str(warm).lower()};
      private _bagUid="bag";private _deltaT=1;private _bagVolumeRemaining=500;private _bagChange=2;
      _patient setVariable ["ACME_piCuffs",createHashMapFromArray [["bag",[100,{p},"server"]]]];
      {work}
      [abs (_bagChange-{rate}/60)<.0001,"blood pressure tier disagrees with displayed pressure"] call _check;
    ''')


@pytest.mark.parametrize('p',[0,.25,.5,1])
def test_rate_readout_exposes_observable_fluid_and_drops_but_never_nominal_drug_delivery(p):
    execute(fn('formatRate')+f'''
      private _s=[12345,100,20,40,{p}] call ACME_fnc_formatRate;
      [_s find "mg/min"<0 && {{_s find "nominal"<0}} && {{_s find "12345"<0}},"hidden dose/rate exposed"] call _check;
      [_s find "gtt/min">=0 && {{_s find "mL/min">=0}} && {{_s find "% open">=0}},"observable flow or percentage missing"] call _check;
    ''')


def test_new_line_maps_require_boolean_snapshot_values_and_used_blood_cannot_bypass_dirty_gate():
    s=read('clinicalValidate')
    for field in ['ACME_lineWarmers','ACME_YLinePrimed']:
        assert f'["{field}","HASHMAP"]' in s
        assert f'case "{field}"' in s
    assert 'Flush this Y line before hanging more blood.' in read('rehangUsedBagCommit')


def test_new_y_line_explicit_empty_map_does_not_revive_expired_global_warmer():
    execute(basic()+fn('lineWarmer')+'''
      _patient setVariable ["ACME_lineWarmers",createHashMap];
      _patient setVariable ["ACME_warmedBlood",true];
      [!([_patient,"body",false,0] call ACME_fnc_lineWarmer),"legacy warm flag leaked onto explicitly tracked empty map"] call _check;
    ''')
