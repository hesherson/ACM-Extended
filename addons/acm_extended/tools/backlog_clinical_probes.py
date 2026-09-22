"""Historical-contract probes executing shipped SQF with explicit engine boundaries.

No source text from historical dispatch expansion is executed. These are offline
regressions, not an Arma UI, network-transport or pharmacological validation.
"""
from pathlib import Path
import re
from test_menu_death_lifecycle import ROOT, adapt, execute

F = ROOT / 'addons/acm_extended/functions'


def function(name):
    return (F / ('fn_' + name + '.sqf')).read_text(encoding='utf-8-sig')


def native_breathing(name):
    source=(ROOT/'addons/breathing/functions'/('fnc_'+name+'.sqf')).read_text(encoding='utf-8-sig')
    source=source.replace('owner _patient','_ownerNum')
    # Namespace mock has no broadcast parameter; policy/field mapping is still the real helper.
    return adapt(source,'breathing').replace(', _public]',']')


def io_modes_probe():
    execute('private _io = {'+adapt(function('ioPainResponse'))+'};'+'''
        private _knockouts=0;
        private _sounds=0;
        ace_medical_fnc_adjustPainLevel={
            params ["_p","_amount"];
            _p setVariable ["ace_medical_pain",1 min ((_p getVariable ["ace_medical_pain",0])+_amount)];
        };
        ACM_core_fnc_setAceMedicalState={
            (_this select 0) setVariable ["ace_medical_pain",((_this select 1) select 0) select 1];
        };
        ace_medical_feedback_fnc_playInjuredSound={_sounds=_sounds+1;};
        ace_medical_status_fnc_setUnconsciousState={
            _knockouts=_knockouts+1;
            (_this select 0) setVariable ["ACE_isUnconscious",_this select 1];
        };
        missionNamespace setVariable ["ACME_ioInsertionMinPain",0.35];
        {
            _x params ["_mode","_expectedPain","_expectedWaits","_expectedSound"];
            _waits=[]; _sounds=0; _knockouts=0;
            _patient setVariable ["ace_medical_pain",0];
            _patient setVariable ["ACE_isUnconscious",false];
            _patient setVariable ["ACME_ioSyncopeToken",-1];
            for "_i" from 1 to 10 do {[_patient,"body",_mode] call _io;};
            [abs((_patient getVariable "ace_medical_pain")-_expectedPain)<0.0001,"IO pain contract"] call _check;
            [count _waits==_expectedWaits && {_sounds==_expectedSound},"IO repeated flow/sound scheduling"] call _check;
            [_knockouts==0,"IO immediate forced knockout"] call _check;
            if (_expectedWaits>0) then {
                private _job=_waits select 0;
                _patient setVariable ["ACME_ioSyncopeToken",99];
                (_job select 1) call (_job select 0);
                [_knockouts==0,"superseded fluid callback"] call _check;
            };
        } forEach [["placement",0.35,0,1],["medication",1,0,0],["fluid",1,1,0]];
        _waits=[]; _patientAlive=false;
        [_patient,"body","fluid"] call _io;
        [count _waits==0,"dead IO callback scheduled"] call _check;
    ''')


def rosc_stress_probe():
    commit=adapt(function('rocStressStateCommit')).replace(', _public]',']')
    callback=function('registerRoscBreathingRuntime')
    callback=re.sub(r'private _targets = allPlayers inAreaArray \[[^;]+;', 'private _targets = [];',callback)
    execute('ACME_fnc_rocStressStateCommit={'+commit+'};'+'''
        ACM_circulation_fnc_setRuntimeState={};
        ACM_core_fnc_setAceMedicalState={};
        missionNamespace setVariable ["ACME_roc_postROSCStressDelay",15];
        _patient setVariable ["ACME_roc_awakeDwell",100];
        _patient setVariable ["ACME_roc_awakeResistAdd",20];
        _patient setVariable ["ACME_hrDrive_roc",138];
        _patient setVariable ["ACME_roc_awarenessEvent",true];
        _patient setVariable ["ACME_roc_paralyzed",true];
    '''+adapt(callback)+'''
        [_patient] call _track;
        [(_patient getVariable "ACME_roc_awakeDwell")==0,"ROSC dwell not reset"] call _check;
        [(_patient getVariable "ACME_roc_awakeResistAdd")==0,"ROSC resistance debt"] call _check;
        [(_patient getVariable "ACME_hrDrive_roc")==-1,"ROSC HR debt"] call _check;
        [(_patient getVariable "ACME_roc_postROSCGraceUntil")==25,"ROSC grace not set"] call _check;
        [_patient getVariable "ACME_roc_awarenessEvent","past awareness erased"] call _check;
        [_patient getVariable "ACME_roc_paralyzed","ROSC reversed motor block"] call _check;
    ''')


def threshold_observer_probe():
    source=function('rhythmThresholdTick').replace('alive _u','_patientAlive').replace('local _u','true').replace('allUnits','[_patient]')
    # SQF-VM lacks continue. Lower only the one outer patient's continue statements
    # to a named break from that same iteration scope; nested function bodies remain.
    from source_scan import lex
    assert source.count('forEach') == 1
    anchor = '{\n    private _u = _x;'
    assert source.count(anchor) == 1
    source=source.replace(anchor,'{\n    scopeName "backlogPatientIteration";\n    private _u = _x;')
    for token in reversed(lex(source)):
        if token.kind == 'ident' and token.value == 'continue':
            source=source[:token.offset]+'breakOut "backlogPatientIteration"'+source[token.offset+len(token.value):]

    execute('private _threshold={'+adapt(source)+'};'+'''
        private _conversions=[];
        private _rawNative=0;
        private _lido=0;
        private _shock=false;
        ACME_fnc_rhythmGet={_rawNative};
        ACME_fnc_lidoEffectiveness={_lido};
        ACME_fnc_rhythmSet={_conversions pushBack _this;};
        ACM_circulation_fnc_recentAEDShock={_shock};
        ACM_circulation_fnc_setCardiacArrestTargetRhythm={};
        ACM_circulation_fnc_setRuntimeState={};
        ACME_fnc_rhythmRelease={};
        _patient setVariable ["ACM_circulation_ROSC_Time",-9999];
        _patient setVariable ["ace_medical_medications",[[]]];
        missionNamespace setVariable ["ACME_rhythmAutoSVTFromRateEnabled",false];
        {
            _x params ["_raw","_inArrest","_effect","_recentShock","_expected"];
            _conversions=[]; _rawNative=_raw; _lido=_effect; _shock=_recentShock;
            _patient setVariable ["ACM_circulation_Cardiac_RhythmState",_raw];
            _patient setVariable ["ace_medical_inCardiacArrest",_inArrest];
            _patient setVariable ["ACME_rhythm_active",0];
            _patient setVariable ["ace_medical_heartRate",90];
            call _threshold;
            [count _conversions==_expected,"threshold observer converted native rhythm incorrectly"] call _check;
        } forEach [[4,false,0,false,0],[4,false,1,false,1],[4,true,1,false,0],
            [3,true,1,false,0],[2,true,1,false,0],[1,true,1,false,0],[4,false,1,true,0],[0,false,0,false,0]];
    ''')


def chest_reset_probe():
    execute('ACM_breathing_fnc_setRuntimeState={'+native_breathing('setRuntimeState')+'};'+
        'ACM_breathing_fnc_setChestInjuryState={'+native_breathing('setChestInjuryState')+'};'+
        'private _reset={'+adapt(function('megacodeChestInjury'))+'};'+'''
        private _injuries=0;
        private _stopped=[];
        ACME_fnc_ptxInjury={_injuries=_injuries+1;};
        ACM_breathing_fnc_updateLungState={};
        CBA_fnc_removePerFrameHandler={_stopped pushBack (_this select 0);};
        _patient setVariable ["ACM_breathing_Pneumothorax_PFH",5];
        _patient setVariable ["ACM_breathing_ChestInjury_State",true];
        _patient setVariable ["ACM_breathing_Pneumothorax_State",4];
        _patient setVariable ["ACM_breathing_TensionPneumothorax_State",true];
        _patient setVariable ["ACM_breathing_TensionPneumothorax_Time",100];
        _patient setVariable ["ACM_breathing_Hardcore_Pneumothorax",true];
        _patient setVariable ["ACM_breathing_Hemothorax_State",3];
        _patient setVariable ["ACME_ptx_state",[1,4,2,0,1,0,1,4,0]];
        _patient setVariable ["ACME_CS_holeData",["preserved"]];
        _patient setVariable ["ACME_thora_tube_left",true];
        _patient setVariable ["ACME_ncd_placed",true];
        [_patient,"ncd"] call _reset;
        [_stopped isEqualTo [5] && {_injuries==0},"reset scheduled/reinflicted chest injury"] call _check;
        [(_patient getVariable "ACM_breathing_Pneumothorax_PFH")==-1,"PFH not retired"] call _check;
        [(_patient getVariable "ACM_breathing_Pneumothorax_State")==0,"PTX not cleared"] call _check;
        [!(_patient getVariable "ACM_breathing_TensionPneumothorax_State"),"tension remains"] call _check;
        [!(_patient getVariable "ACM_breathing_Hardcore_Pneumothorax"),"hardcore PTX remains"] call _check;
        [!(_patient getVariable "ACM_breathing_ChestInjury_State"),"injury flag re-enabled"] call _check;
        [isNil {_patient getVariable "ACME_ptx_state"},"model survives clear"] call _check;
        [isNil {_patient getVariable "ACM_breathing_TensionPneumothorax_Time"},"tension timer survives"] call _check;
        [(_patient getVariable "ACME_CS_holeData") isEqualTo ["preserved"],"wound evidence changed"] call _check;
        [_patient getVariable "ACME_thora_tube_left","tube removed"] call _check;
        [_patient getVariable "ACME_ncd_placed","NCD removed"] call _check;
    ''')


def tract_and_peel_probe():
    effect=function('chestSealEffectLocal').replace('local _patient','_patientLocal')
    execute('private _patientLocal=true; private _effect={'+adapt(effect)+'};'+
        'ACME_fnc_thoraSideStateCommit={'+adapt(function('thoraSideStateCommit'))+'};'+
        'ACM_breathing_fnc_setRuntimeState={'+native_breathing('setRuntimeState')+'};'+'''
        private _treat=[];
        private _globalSeal=0;
        ACME_fnc_clinicalEpoch={5};
        ACME_fnc_ptxEnsure={};
        ACME_fnc_ptxTreat={_treat pushBack (_this select 1);};
        ACME_fnc_ptxInjury={_globalSeal=_globalSeal+100;};
        ACME_fnc_thoraBumpVer={};
        ACME_fnc_chestSealLogOnce={false};
        ACM_breathing_fnc_updateLungState={};
        ACM_breathing_fnc_applyChestSealLocal={_globalSeal=_globalSeal+1;};
        _patient setVariable ["ACME_thora_open_left","finger"];
        _patient setVariable ["ACME_thora_tube_left",false];
        _patient setVariable ["ACME_CS_holeData",["external wound"]];
        _patient setVariable ["ACM_breathing_ChestSeal_State",false];
        [_patient,_medic,"thoraSeal",["left",4]] call _effect;
        [count _treat==0,"old clinical epoch sealed tract"] call _check;
        _patientLocal=false;
        [_patient,_medic,"thoraSeal",["left",5]] call _effect;
        [count _treat==0,"non-owner mutated tract"] call _check;
        _patientLocal=true;
        [_patient,_medic,"thoraSeal",["left",5]] call _effect;
        [_treat isEqualTo ["thoraSeal"],"valid tract seal not committed"] call _check;
        [(_patient getVariable "ACME_thora_open_left")=="sealed","finger outlet remained patent"] call _check;
        [_patient getVariable "ACME_thora_sealed_left","sealed flag absent"] call _check;
        [_patient getVariable "ACME_thora_closed_left","closed flag absent"] call _check;
        [!(_patient getVariable "ACM_breathing_ChestSeal_State"),"tract sealed unrelated chest wounds"] call _check;
        [(_patient getVariable "ACME_CS_holeData") isEqualTo ["external wound"],"external wounds changed"] call _check;
        _patient setVariable ["ACME_thora_open_right","finger"];
        _patient setVariable ["ACME_thora_tube_right",true];
        [_patient,_medic,"thoraSeal",["right",5]] call _effect;
        [count _treat==1,"installed tube was sealed over"] call _check;
        _patient setVariable ["ACME_CS_blockedEffectEpoch","old"];
        [_patient,_medic,"peel",[],"old",1,1] call _effect;
        [count _treat==1,"blocked epoch applied peel"] call _check;
        [_patient,_medic,"peel",[],"new",1,2] call _effect;
        [_treat isEqualTo ["thoraSeal","peel"],"fresh peel not accepted"] call _check;
        [_patient,_medic,"peel",[],"new",1,2] call _effect;
        [_patient,_medic,"peel",[],"new",1,1] call _effect;
        [count _treat==2 && {_globalSeal==0},"duplicate peel/new injury or blanket seal"] call _check;
    ''')


def bvm_with_cpr_probe():
    from test_bvm_startup import setup
    execute(setup()+'''
        _cprActive=true;
        [_medic,_patient,false,false] call ACM_breathing_fnc_useBVM;
        [ACM_core_ContinuousAction_Active,"CPR blocked BVM startup"] call _check;
        call _tick; CBA_missionTime=13; call _tick; CBA_missionTime=20; call _tick;
        [_squeezes==2,"CPR blocked BVM delivery"] call _check;
    ''')


def reserved_roles_probe():
    from test_bvm_startup import setup
    cpr=(ROOT/'addons/circulation/functions/fnc_cprSessionValid.sqf').read_text().replace('_medic distance2D _patient','_distance')
    execute(setup()+'ACM_circulation_fnc_cprSessionValid={'+adapt(cpr,'circulation')+'};'+'''
        _patient setVariable ["ACM_breathing_BVM_Medic",_medic];
        _patient setVariable ["ACM_breathing_BVM_provider",objNull];
        _patient setVariable ["ACM_circulation_CPR_session",[_medic,4]];
        _medic setVariable ["ACM_circulation_CPR_Patient",_patient];
        _medic setVariable ["ACM_circulation_CPR_Epoch",4];
        _medic setVariable ["ACM_circulation_isPerformingCPR",false];
        [[_medic,_patient] call ACM_breathing_fnc_bvmSessionValid,"paused BVM lost reservation"] call _check;
        [[_medic,_patient] call ACM_circulation_fnc_cprSessionValid,"paused CPR lost reservation"] call _check;
        [!([missionNamespace,_patient] call ACM_breathing_fnc_canUseBVM),"second BVM provider admitted"] call _check;
        {
            _x params ["_newAlive","_newUnconscious","_newDistance"];
            _alive=_newAlive; _unconscious=_newUnconscious; _distance=_newDistance;
            [!([_medic,_patient] call ACM_breathing_fnc_bvmSessionValid),"unavailable BVM holder retained"] call _check;
            [!([_medic,_patient] call ACM_circulation_fnc_cprSessionValid),"unavailable CPR holder retained"] call _check;
        } forEach [[false,false,1],[true,true,1],[true,false,8]];
    ''')


def compound_save_probe():
    source=function('skCompoundSave').replace('findDisplay 84000','_dialogHandle')
    source=re.sub(r'_dlg displayCtrl 84004','objNull',source)
    execute('private _dialogHandle=uiNamespace; private _save={'+adapt(source)+'};'+'''
        private _steps=[];
        private _accepted=true;
        ACME_fnc_skPendingTagCommit={_steps pushBack "tag";};
        ACME_fnc_skCompoundCommit={_steps pushBack "commit"; _accepted};
        ACME_fnc_skRefreshDrawn={_steps pushBack "drawn";};
        ACME_fnc_skPendingTagReset={_steps pushBack "reset";};
        ACME_fnc_skCompoundBegin={_steps pushBack "begin";};
        ACME_fnc_skListRefresh={_steps pushBack "list";};
        ACME_fnc_skPendingTagRender={_steps pushBack "render";};
        uiNamespace setVariable ["ACME_SK_WasteStage","compound"];
        uiNamespace setVariable ["ACME_SK_CompoundComponents",["sample"]];
        _dialog=true;
        call _save;
        [_steps isEqualTo ["tag","commit","drawn","reset","begin","list","render"],"save commit/reset order"] call _check;
        [_dialog && {count _waits==0},"save required deferred dialog reconstruction"] call _check;
        _steps=[]; _accepted=false;
        call _save;
        [_steps isEqualTo ["tag","commit"],"failed save erased draft"] call _check;
        _steps=[]; uiNamespace setVariable ["ACME_SK_CompoundComponents",[]];
        call _save;
        [_steps isEqualTo [],"empty draft committed"] call _check;
    ''')


def thora_access_probe():
    # Execute actual provider callback and item selector. Rendering and ACE inventory
    # access are the mocked boundaries; all rejection/consumption/state ordering is real.
    source=function('thoraMouseDown').replace('_tubeMedic removeItem "ACM_ChestTubeKit";',
        'if (_debitAccepted) then {_tubeCount=_tubeCount-1;}; _debits=_debits+1;')
    execute('ACME_fnc_thoraKitItem={'+adapt(function('thoraKitItem'))+'};'+
        'ACME_fnc_thoraSideStateCommit={'+adapt(function('thoraSideStateCommit'))+'};'+
        'ACME_fnc_thoraClosureMode={'+adapt(function('thoraClosureMode'))+'};'+
        'private _down={'+adapt(source)+'};'+
        'private _up={'+adapt(function('thoraMouseUp'))+'};'+'''
        private _disposable=false; private _surgical=false; private _permitted=true;
        private _debitAccepted=true; private _debits=0; private _tubeCount=1;
        private _nativeStarts=0; private _nativeTubes=0;
        ace_medical_treatment_fnc_hasItem={
            if (((_this select 2) select 0)=="ACM_ThoracostomyKit") then {_disposable} else {_surgical}
        };
        ace_medical_treatment_fnc_useItem={
            _debits=_debits+1;
            if (_debitAccepted) then {[_medic,(_this select 2) select 0]} else {[_medic,""]}
        };
        ace_common_fnc_getCountOfItem={_tubeCount};
        ACME_fnc_procedureAllowed={_permitted};
        ACME_fnc_minigameInputMouse={false};
        ACME_fnc_thoraCanSweep={false};
        ACME_fnc_thoraCursorUV={[0.5,0.5]};
        ACME_fnc_thoraBumpVer={}; ACME_fnc_thoraRender={};
        ACME_fnc_thoraRenderOpen={}; ACME_fnc_thoraRenderTube={};
        ACME_fnc_thoraSelectTool={}; ACME_fnc_thoraPassiveDrain={};
        ACM_breathing_fnc_Thoracostomy_start={_nativeStarts=_nativeStarts+1;};
        ACM_breathing_fnc_Thoracostomy_insertChestTube={_nativeTubes=_nativeTubes+1;};
        uiNamespace setVariable ["ACME_Thora_Medic",_medic];
        uiNamespace setVariable ["ACME_Thora_Patient",_patient];
        uiNamespace setVariable ["ACME_Thora_Side","left"];
        uiNamespace setVariable ["ACME_Thora_Held","finger"];
        _patient setVariable ["ACME_thora_incision_left",[[0.5,0.5],0,2]];
        missionNamespace setVariable ["ACME_thora_allowSurgicalKit",true];
        {
            _x params ["_disp","_surg","_allowed","_debit","_expectedOpen","_expectedDebit"];
            _disposable=_disp;_surgical=_surg;_permitted=_allowed;_debitAccepted=_debit;
            _debits=0;_nativeStarts=0;
            _patient setVariable ["ACME_thora_open_left","kelly"];
            [objNull,0] call _down;
            [(_patient getVariable "ACME_thora_open_left")==_expectedOpen,"finger commit ignored kit/access"] call _check;
            [_debits==_expectedDebit,"disposable/reusable debit"] call _check;
            [_nativeStarts==(if(_expectedOpen=="finger")then{1}else{0}),"native start before accepted kit"] call _check;
        } forEach [[true,true,true,true,"finger",1],[false,true,true,true,"finger",0],
            [true,false,true,false,"kelly",1],[false,false,true,true,"kelly",0],[true,true,false,true,"kelly",0]];
        _surgical=true;_disposable=false;
        missionNamespace setVariable ["ACME_thora_allowSurgicalKit",false];
        [([_medic,_patient] call ACME_fnc_thoraKitItem)=="","disabled reusable kit accepted"] call _check;
        missionNamespace setVariable ["ACME_thora_allowSurgicalKit",true];
        {
            _x params ["_allowed","_hasKit"];
            _permitted=_allowed;_surgical=_hasKit;_disposable=false;
            uiNamespace setVariable ["ACME_Thora_Cutting",true];
            uiNamespace setVariable ["ACME_Thora_KellyArmed",true];
            _patient setVariable ["ACME_thora_open_left","split"];
            [objNull,0] call _up;
            [! (uiNamespace getVariable "ACME_Thora_Cutting"),"rejected incision remains armed"] call _check;
            [! (uiNamespace getVariable "ACME_Thora_KellyArmed"),"rejected Kelly remains armed"] call _check;
            [(_patient getVariable "ACME_thora_open_left")=="split","lost access committed tract"] call _check;
        } forEach [[false,true],[true,false]];
        uiNamespace setVariable ["ACME_Thora_Held","tube"];
        uiNamespace setVariable ["ACME_Thora_TubeSnap",true];
        {
            _x params ["_allowed","_debit","_expected"];
            _permitted=_allowed;_debitAccepted=_debit;_debits=0;_tubeCount=1;_nativeTubes=0;
            _patient setVariable ["ACME_thora_closed_left",false];
            _patient setVariable ["ACME_thora_tube_left",false];
            [objNull,0] call _down;
            [(_patient getVariable "ACME_thora_tube_left") isEqualTo _expected,"tube published before accepted debit"] call _check;
            [_nativeTubes==(if(_expected)then{1}else{0}),"native tube registered before accepted debit"] call _check;
        } forEach [[false,true,false],[true,false,false],[true,true,true]];
    ''')
