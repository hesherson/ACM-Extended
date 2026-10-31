"""Execute B212 surgical/traumatic drainage in production SQF.

Only Arma object/locality/clock/network/UI boundaries and native setter dispatch
are fixtures. Drain arithmetic, replay fences, eligibility and ordering execute.
The native model has a single pleural reservoir; these tests do not invent sides.
"""
import pytest
from test_historical_cardiac_execution import F, code, function, setup
from test_menu_death_lifecycle import execute as run_sqf


def execute(source):
    # This VM has no synchronized server clock. The fixture supplies that clock.
    run_sqf(source.replace('serverTime', '_serverTime'))


def drain_setup():
    return setup()+function('thoraDrainBloodLocal', extended=True)+function('thoraAftercareLocal', extended=True)+'''
        serverTime=100;
        private _effects=[]; private _logs=[]; private _nativeStarts=0; private _lungUpdates=0;
        private _permitted=true; private _nativeChanges=[];
        ACME_fnc_procedureAllowed={_permitted};
        ACME_fnc_thoraSideStateCommit={params ["_patient","_side","_field","_value"]; _patient setVariable [format ["ACME_thora_%1_%2",_field,_side],_value];};
        ACME_fnc_thoraBumpVer={};
        ACME_fnc_chestSealBurpReady={true};
        ACME_fnc_thoraOutputStateCommit={params ["_patient","_field","_value"]; _patient setVariable ["ACME_thora_fluidSeen",_value];};
        ACM_breathing_fnc_setRuntimeState={params ["_patient","_changes"];
            _nativeChanges append _changes;
            { _x params ["_key","_value"];
                private _variable=switch (_key) do {
                    case "hemothoraxFluid":{"ACM_breathing_Hemothorax_Fluid"};
                    case "thoracostomyState":{"ACM_breathing_Thoracostomy_State"};
                    case "thoracostomyUsedKit":{"ACM_breathing_Thoracostomy_UsedKit"};
                    default {"fixture_unused"};
                }; _patient setVariable [_variable,_value];
            } forEach _changes;
        };
        ACME_fnc_ptxTreat={_effects pushBack _this; _patient setVariable ["ACME_ptx_state",[1,1,1,0,0,0,1,1,0.5]];};
        ACM_breathing_fnc_updateLungState={_lungUpdates=_lungUpdates+1;};
        ACM_breathing_fnc_Thoracostomy_startLocal={_nativeStarts=_nativeStarts+1; _patient setVariable ["ACM_breathing_Thoracostomy_State",1];};
        ACME_fnc_chestSealLogOnce={_logs pushBack _this;true};
        ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
        _patient setVariable ["ACM_breathing_Hemothorax_Fluid",1.1];
        _patient setVariable ["ACM_breathing_Hemothorax_State",8];
        _patient setVariable ["ACM_breathing_Hemothorax_PFH",44];
        _patient setVariable ["ACME_ptx_state",[1,3,0.8,0,0.5,0,1,3,0.5]];
        _patient setVariable ["ACME_thora_incision_left",[[0.3,0.4],1,2]];
        _patient setVariable ["ACME_thora_open_left","kelly"];
        _patient setVariable ["ACME_thora_sealed_left",false];
        _patient setVariable ["ACME_thora_closed_left",false];
        _patient setVariable ["ACM_breathing_Thoracostomy_State",0];
    '''


@pytest.mark.parametrize('fluid',[0,0.0001,0.2,1.1,1.5])
@pytest.mark.parametrize('operation',['widen','sweep'])
def test_finger_drains_the_entire_current_pool_once_and_does_not_stop_hemorrhage(fluid,operation):
    prepare='_patient setVariable ["ACME_thora_open_left","finger"];' if operation=='sweep' else ''
    execute(drain_setup()+prepare+f'_patient setVariable ["ACM_breathing_Hemothorax_Fluid",{fluid}];'+f'''
        [_patient,_medic,"left","{operation}",1,[7,1,100]] call ACME_fnc_thoraAftercareLocal;
        [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==0,"finger left retained blood"] call _check;
        [(_patient getVariable "ACM_breathing_Hemothorax_State")==8,"finger cured hemorrhage"] call _check;
        [(_patient getVariable "ACM_breathing_Hemothorax_PFH")==44,"finger removed bleeding worker"] call _check;
        [(_patient getVariable "ace_medical_bloodVolume")==6,"draining changed circulating blood twice"] call _check;
        [count _events==1,"drain result missing/duplicated"] call _check;
        private _result=((_events select 0) select 1) select 0;
        [(_result select 2)==(round ({fluid}*10000))/10,"popup does not show actual mL"] call _check;
        _patient setVariable ["ACM_breathing_Hemothorax_Fluid",0.2];
        [_patient,_medic,"left","{operation}",1,[7,1,100]] call ACME_fnc_thoraAftercareLocal;
        [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==0.2,"replayed click drained reaccumulated blood"] call _check;
        [count _events==1,"replayed click displayed new result"] call _check;
        [_patient,_medic,"left","sweep",1,[7,2,100]] call ACME_fnc_thoraAftercareLocal;
        [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==0,"fresh sweep cannot drain new pool"] call _check;
    ''')


@pytest.mark.parametrize('operation',['burp','peel'])
@pytest.mark.parametrize('fluid,pressure,expected',[(0,1,0),(0.12,0,0.012),(0.6,0,0.3),(0.6,0.8,0.48),(1.2,0,1.2),(1.5,1,1.5)])
def test_seal_lift_scales_with_hemo_or_ptx_pressure_before_relief(operation,fluid,pressure,expected):
    execute(drain_setup()+f'''
        _patient setVariable ["ACME_thora_open_left","sealed"];
        _patient setVariable ["ACME_thora_sealed_left",true];
        _patient setVariable ["ACME_thora_closed_left",true];
        _patient setVariable ["ACM_breathing_Hemothorax_Fluid",{fluid}];
        _patient setVariable ["ACME_ptx_state",[1,3,0.8,0,{pressure},0,1,3,0.5]];
        [_patient,_medic,"left","{operation}",1,[7,1,100]] call ACME_fnc_thoraAftercareLocal;
        [abs ((_patient getVariable "ACM_breathing_Hemothorax_Fluid")-({fluid}-{expected}))<0.000001,"pressure-scaled volume wrong"] call _check;
        [(_patient getVariable "ACM_breathing_Hemothorax_State")==8,"seal lift cured hemorrhage"] call _check;
        [count _effects==1,"pressure not relieved"] call _check;
        [((((_events select 0) select 1) select 0) select 2)==(round ({expected}*10000))/10,"seal popup mL wrong"] call _check;
        [(_patient getVariable "ACME_thora_sealed_left") isEqualTo {str(operation=='burp').lower()},"wrong seal retention"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patientLocal=false;', '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_alive=false;', '_medic setVariable ["ACE_isUnconscious",true];', '_distance=6;', '_permitted=false;',
    '_patient setVariable ["ACME_thora_tube_left",true];', '_patient setVariable ["ACME_thora_incision_left",[]];',
    '_patient setVariable ["ACME_thora_open_left","split"];', '_patient setVariable ["ACME_thora_sealed_left",true];',
    '_patient setVariable ["ACME_thora_closed_left",true];', 'serverTime=116;', 'serverTime=97;',
])
def test_invalid_or_stale_widening_does_not_change_blood_tract_or_popup(change):
    execute(drain_setup()+change+'''
        private _before=_patient getVariable "ACME_thora_open_left";
        [_patient,_medic,"left","widen",1,[7,1,100]] call ACME_fnc_thoraAftercareLocal;
        [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==1.1,"invalid widening drained blood"] call _check;
        [(_patient getVariable "ACME_thora_open_left")==_before,"invalid widening opened tract"] call _check;
        [count _events==0 && {count _effects==0} && {_nativeStarts==0},"invalid widening emitted effects"] call _check;
    ''')


def test_second_side_finger_preserves_opposite_tube_and_aggregate_state():
    execute(drain_setup()+'''
        _patient setVariable ["ACME_thora_tube_right",true];
        _patient setVariable ["ACME_thora_open_right","finger"];
        _patient setVariable ["ACM_breathing_Thoracostomy_State",2];
        [_patient,_medic,"left","widen",1,[7,1,100],true] call ACME_fnc_thoraAftercareLocal;
        [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==0,"second-side finger failed"] call _check;
        [(_patient getVariable "ACM_breathing_Thoracostomy_State")==2 && {_nativeStarts==0},"finger replaced aggregate tube"] call _check;
        [_patient getVariable "ACME_thora_tube_right","finger removed opposite tube"] call _check;
        [(_patient getVariable "ACME_thora_open_right")=="finger","finger changed opposite tract"] call _check;
        [(_patient getVariable "ACME_thora_fluidSeen")==0,"opposite tube observer did not see debit"] call _check;
    ''')


def test_corpse_can_be_drained_without_restarting_physiology():
    execute(drain_setup()+'''
        _patientAlive=false;
        [_patient,_medic,"left","widen",1,[0,1,100],true] call ACME_fnc_thoraAftercareLocal;
        [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==0,"corpse widening did not drain"] call _check;
        [count _effects==0 && {_nativeStarts==0} && {_lungUpdates==0},"corpse physiology restarted"] call _check;
        [(_patient getVariable "ACM_breathing_Thoracostomy_State")==1,"corpse tract not registered"] call _check;
    ''')


def test_late_lower_sequence_cannot_drain_after_handoff_and_receipts_reset_with_epoch():
    execute(drain_setup()+'''
        [_patient,_medic,"finger",1,[7,2,100]] call ACME_fnc_thoraDrainBloodLocal;
        _patient setVariable ["ACM_breathing_Hemothorax_Fluid",0.2];
        _patientLocal=false;
        [([_patient,_medic,"finger",1,[7,3,100]] call ACME_fnc_thoraDrainBloodLocal)==-1,"old owner drained"] call _check;
        _patientLocal=true;
        [([_patient,_medic,"finger",1,[7,1,100]] call ACME_fnc_thoraDrainBloodLocal)==-1,"reordered packet drained"] call _check;
        [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==0.2,"handoff replay lost fresh blood"] call _check;
        _patient setVariable ["ACME_clinicalEpoch",2];
        [([_patient,_medic,"finger",1,[7,3,100]] call ACME_fnc_thoraDrainBloodLocal)==-1,"old epoch accepted"] call _check;
        [abs (([_patient,_medic,"finger",2,[7,1,100]] call ACME_fnc_thoraDrainBloodLocal)-0.2)<0.000001,"fresh epoch rejected"] call _check;
    ''')


def test_expired_high_water_mark_allows_fresh_reconnected_origin_but_not_old_packet():
    execute(drain_setup()+'''
        [_patient,_medic,"finger",1,[7,200,100]] call ACME_fnc_thoraDrainBloodLocal;
        _patient setVariable ["ACM_breathing_Hemothorax_Fluid",0.3];
        serverTime=116;
        [([_patient,_medic,"finger",1,[7,200,100]] call ACME_fnc_thoraDrainBloodLocal)==-1,"expired packet accepted"] call _check;
        [abs (([_patient,_medic,"finger",1,[7,1,116]] call ACME_fnc_thoraDrainBloodLocal)-0.3)<0.000001,"fresh sequence was blocked by expired origin record"] call _check;
    ''')


def test_normal_chest_seal_burp_uses_current_pressure_and_replay_fence():
    execute(drain_setup()+function('chestSealBurp',extended=True)+'''
        _patient setVariable ["ACM_breathing_ChestSeal_State",true];
        _patient setVariable ["ACME_CS_ProcedureTokens",["panel-1"]];
        _patient setVariable ["ACM_breathing_Hemothorax_Fluid",0.6];
        _patient setVariable ["ACME_ptx_state",[1,3,0.8,0,0.8,0,1,3,0.5]];
        [_medic,_patient,"body",1,[7,1,100],"panel-1"] call ACME_fnc_chestSealBurp;
        [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==0.6,"normal seal drained retained blood"] call _check;
        [count _effects==1 && {count _events==0},"normal seal lost air relief or showed a drainage popup"] call _check;
        _patient setVariable ["ACM_breathing_Hemothorax_Fluid",0.3];
        [_medic,_patient,"body",1,[7,1,100],"panel-1"] call ACME_fnc_chestSealBurp;
        [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==0.3,"normal burp replay drained again"] call _check;
        [count _effects==1,"normal burp replay treated again"] call _check;
    ''')


def test_normal_unsealed_chest_cannot_drain_by_burp_call():
    execute(drain_setup()+function('chestSealBurp',extended=True)+'''
        _patient setVariable ["ACME_CS_ProcedureTokens",["panel-1"]];
        [_medic,_patient,"body",1,[7,1,100],"panel-1"] call ACME_fnc_chestSealBurp;
        [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==1.1 && {count _events==0},"unsealed burp drained"] call _check;
    ''')


def test_first_ui_finger_click_sends_one_owner_transaction_without_redebiting_kit():
    execute(drain_setup()+function('thoraAftercareRequest',extended=True)+function('thoraMouseDown',extended=True)+'''
        private _kitUses=0;
        ACME_fnc_minigameInputMouse={false}; ACME_fnc_thoraCanSweep={false};
        ACME_fnc_thoraKitItem={"ACM_ThoracostomyKit"};
        ACME_fnc_thoraCursorUV={[0.3,0.4]};
        ACME_fnc_treatmentSupplyTake={_kitUses=_kitUses+1; ["receipt"]};
        ACME_fnc_treatmentSupplyRefund={};
        uiNamespace setVariable ["ACME_Thora_Held","finger"];
        uiNamespace setVariable ["ACME_Thora_Medic",_medic];
        uiNamespace setVariable ["ACME_Thora_Patient",_patient];
        uiNamespace setVariable ["ACME_Thora_Side","left"];
        [objNull,0] call ACME_fnc_thoraMouseDown;
        [objNull,0] call ACME_fnc_thoraMouseDown;
        [_kitUses==1 && {count _events==1},"pending widening consumed duplicate kit/sent duplicate action"] call _check;
        [(_patient getVariable "ACME_thora_open_left")=="kelly","UI mutated owner state"] call _check;
        private _args=(_events select 0) select 2; _events=[];
        _args call ACME_fnc_thoraAftercareLocal;
        [(_patient getVariable "ACME_thora_open_left")=="finger","owner did not complete widening"] call _check;
        [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==0,"first UI click failed to drain"] call _check;
    ''')


def owner_receipt_setup():
    from test_b205_thora_network_execution import block
    owner = block((F/'fn_ownerDispatch.sqf').read_text(), 'case "thoraAftercare":')
    refund = function('treatmentSupplyRefund',extended=True).replace('_pending getOrDefault [_id, []]', '[_pending,_id,[]] call _getDefault')
    return drain_setup()+function('thoraAftercareAck',extended=True)+refund+'''
        private _getDefault={params ["_map","_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
        private _refunds=0;
        ace_common_fnc_addToInventory={_refunds=_refunds+1;};
        private _receipt=[_medic,"ACM_ThoracostomyKit",objNull,"kit1"];
        missionNamespace setVariable ["ACME_supplyReceipts",createHashMapFromArray [["kit1",_receipt]]];
        private _args=[_patient,_medic,"left","widen",1,[7,1,100],true,_receipt];
        uiNamespace setVariable ["ACME_Thora_WidenPending",[_patient,"left",1,10,[7,1,100]]];
    '''+'private _ownerWiden={params ["_patient","_args"];'+code(owner)+'};'


@pytest.mark.parametrize('accepted',[True,False])
def test_owner_decision_commits_or_refunds_exact_reserved_kit_once(accepted):
    change='' if accepted else '_patient setVariable ["ACME_thora_tube_left",true];'
    execute(owner_receipt_setup()+change+f'''
        [_patient,_args] call _ownerWiden;
        private _reply=(_events select ((count _events)-1)) select 1;
        [(_reply select 5) isEqualTo {str(accepted).lower()},"owner decision incorrect"] call _check;
        [((_events select ((count _events)-1)) select 2)==7,"ACK did not target original request machine"] call _check;
        _reply call ACME_fnc_thoraAftercareAck;
        _reply call ACME_fnc_thoraAftercareAck;
        [_refunds=={int(not accepted)},"kit not settled exactly once"] call _check;
        [count (missionNamespace getVariable "ACME_supplyReceipts")==0,"kit receipt stranded after ACK"] call _check;
        [(uiNamespace getVariable "ACME_Thora_WidenPending") isEqualTo [],"pending input not released by ACK"] call _check;
    ''')


def test_delayed_widening_ack_retry_after_reset_does_not_refund_an_applied_kit_or_drain_again():
    execute(owner_receipt_setup()+'''
        [_patient,_args] call _ownerWiden;
        _events=[];
        // Original ACK is lost. The patient resets and its owner changes before
        // the requesting machine queries the same receipt after 16 seconds.
        _patient setVariable ["ACME_clinicalEpoch",2];
        _patient setVariable ["ACM_breathing_Hemothorax_Fluid",0.4];
        serverTime=116;
        [_patient,_args] call _ownerWiden;
        [count _events==1,"receipt query repeated clinical effects"] call _check;
        ((_events select 0) select 1) call ACME_fnc_thoraAftercareAck;
        [_refunds==0,"applied kit refunded after delayed ACK"] call _check;
        [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==0.4,"receipt query drained fresh episode"] call _check;
    ''')


def test_native_first_sweep_reports_actual_full_drain_and_legacy_replay_preserves_new_blood():
    execute(drain_setup()+function('Thoracostomy_startLocal','breathing')+'''
        ACME_fnc_ptxEnsure={};
        ace_medical_status_fnc_getMedicationCount={1};
        [_medic,_patient,true] call ACM_breathing_fnc_Thoracostomy_startLocal;
        [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==0,"native finger retained blood"] call _check;
        [(_patient getVariable "ACM_breathing_Hemothorax_State")==8,"native finger cured source"] call _check;
        private _format=(((_events select 0) select 1) select 0) select 0;
        [(_format find "Blood drained: 1100 mL")>=0,"native popup does not show full drain"] call _check;
        _patient setVariable ["ACM_breathing_Hemothorax_Fluid",0.3];
        [_medic,_patient,true] call ACM_breathing_fnc_Thoracostomy_startLocal;
        [(_patient getVariable "ACM_breathing_Hemothorax_Fluid")==0.3,"legacy repeated start drained new pool"] call _check;
    ''')


def test_successful_peel_ack_cannot_overwrite_the_owner_measured_output_popup():
    from test_b208_chest_singleplayer import setup as chest_setup
    execute(chest_setup()+'''
        private _shown=[]; ace_common_fnc_displayTextStructured={_shown pushBack _this;};
        private _request=[_patient,_medic,_viewer,"peel1","epoch",1,"peel"];
        ACME_CS_pending set ["peel1",[_request,[],100]];
        [_patient,"peel1",true,"Seal removed.",[]] call ACME_fnc_chestSealAck;
        [count _shown==0,"generic ACK overwrote actual mL result"] call _check;
        ACME_CS_pending set ["peel2",[_request,[],100]];
        [_patient,"peel2",false,"Already changed.",[]] call ACME_fnc_chestSealAck;
        [count _shown==1,"rejected peel lost its explanation"] call _check;
    ''')
