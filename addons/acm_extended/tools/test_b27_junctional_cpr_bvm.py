"""B27 contracts at their current native/owner boundaries; no gameplay retuning.

The previous tests required comments and removed Extended overrides. These tests
retain the actual contracts: independent roles, one valid provider per role,
networked role markers, owner-written junctional state, and local-only UI refresh.
Engine object/network boundaries are mocked for the execution cases.
"""
from historical_source import read_source, assert_release_identity, switch_case_body as case_body
from pathlib import Path
import unittest
from test_menu_death_lifecycle import adapt, execute
from test_bvm_startup import setup as bvm_setup

ROOT=Path(__file__).resolve().parents[1]
ADDONS=ROOT.parent

def read(rel): return read_source(ROOT/rel, encoding='utf-8-sig')

class B27JunctionalCPRBVM(unittest.TestCase):
    def test_version_pair(self):
        assert_release_identity()

    def test_junctional_state_writers_still_broadcast(self):
        inflict=read('functions/fn_junctionalInflict.sqf')
        self.assertRegex(inflict,r'setVariable\s*\[format\s*\["ACME_Junc_%1".*?true\]')
        owner=read('functions/fn_ownerDispatch.sqf')
        self.assertIn('local _patient',owner)
        for event,state in [('junctionalPackDone','packed'),('junctionalWrapDone','wrapped')]:
            sender=read('functions/fn_'+event+'.sqf')
            self.assertIn('"'+event+'"',sender)
            self.assertIn('call ACME_fnc_ownerDispatch',sender)
            body=case_body(owner,event)
            self.assertIn('setVariable [format ["ACME_Junc_%1", _part], "'+state+'", true]',body)
        pack=adapt(case_body(owner,'junctionalPackDone'))
        wrap=adapt(case_body(owner,'junctionalWrapDone'))
        execute('ace_common_fnc_isAwake = {false}; private _clots = []; ACM_damage_fnc_clotWoundsOnBodyPart = {_clots pushBack _this;};' +
                'private _pack = {'+pack+'}; private _wrap = {'+wrap+'};' + '''
            {
                private _key = format ["ACME_Junc_%1",_x];
                private _args = [_medic,_x];
                _patient setVariable [_key,"open"];
                call _pack;
                [(_patient getVariable [_key,""]) == "packed","packing state not written"] call _check;
                call _wrap;
                [(_patient getVariable [_key,""]) == "wrapped","wrap state not written"] call _check;
            } forEach ["leftarm","rightarm","leftleg","rightleg"];
            [count _clots == 4,"wrap did not route clotting for every body part"] call _check;
        ''')

    def test_junctional_gui_sync_is_local_only(self):
        s=read('functions/fn_junctionalGuiSyncTick.sqf')
        self.assertIn('ace_medical_gui_menuDisplay',s)
        self.assertIn('ace_medical_gui_fnc_updateBodyImage',s)
        self.assertIn('ace_medical_gui_fnc_updateInjuryList',s)
        for bad in ('targetEvent','globalEvent','serverEvent','remoteExec','publicVariable','_target setVariable','_patient setVariable'):
            self.assertNotIn(bad,s)

    def test_junctional_gui_sync_is_bounded(self):
        p=read('functions/fn_postInit.sqf')
        self.assertIn('[{call ACME_fnc_junctionalGuiSyncTick}, 0.2, []] call CBA_fnc_addPerFrameHandler;',p)

    def test_cpr_action_no_longer_blocked_by_bvm(self):
        c=(ADDONS/'circulation/ACE_Medical_Treatment_Actions.hpp').read_text()
        # The CPR class is native now. Require its actual callback and eligibility expression.
        from medication_inventory import subtree
        block=subtree(c,'CPR')['props']
        self.assertEqual(''.join(block['condition'].split()),'QUOTE([ARR_2(_medic,_patient)]callACEFUNC(medical_treatment,canCPR))')
        self.assertEqual(''.join(block['callbackSuccess'].split()),'QUOTE([ARR_2(_medic,_patient)]callFUNC(beginCPR))')
        self.assertNotIn('bvmActive',str(block))

    def test_begin_cpr_override_registered(self):
        self.assertIn('PREP(beginCPR);',(ADDONS/'circulation/XEH_PREP.hpp').read_text())
        s=(ADDONS/'circulation/functions/fnc_beginCPR.sqf').read_text()
        self.assertNotIn('if !([GVAR(CPRTarget)] call EFUNC(core,bvmActive))',s)
        self.assertIn('call FUNC(cprSessionValid)',s)
        self.assertIn('call CBA_fnc_addPerFrameHandler',s)
        self.assertIn('GVAR(CPR_ControllerPFH) = _controller;',s)

    def test_bvm_can_run_during_cpr(self):
        execute(bvm_setup() + '''
            _cprActive = true;
            _patient setVariable ["ace_medical_CPR_provider",missionNamespace];
            [_medic,_patient,false,false] call ACM_breathing_fnc_useBVM;
            [ACM_core_ContinuousAction_Active,"CPR blocked BVM start"] call _check;
            CBA_missionTime=13; call _tick;
            CBA_missionTime=20; call _tick;
            [_squeezes==2,"CPR blocked ventilation"] call _check;
            [(_patient getVariable ["ace_medical_CPR_provider",objNull]) isEqualTo missionNamespace,"BVM cleared another CPR provider"] call _check;
        ''')

    def test_one_provider_per_role_remains(self):
        # Evaluate the actual reservation predicates, including a paused-but-valid role.
        b=(ADDONS/'breathing/functions/fnc_bvmSessionValid.sqf').read_text()
        c=(ADDONS/'circulation/functions/fnc_cprSessionValid.sqf').read_text()
        for name,component,text in [('bvm','breathing',b),('cpr','circulation',c)]:
            # These retained native reservation cases run on one authority;
            # the new patient-owner MP protocol has its own reordered transport suite.
            text=text.replace('_medic distance2D _patient','_distance').replace('isMultiplayer','false')
            body=adapt(text,component)
            setup='''
                ace_common_fnc_isAwake = {!_unconscious};
                _patient setVariable ["ACM_breathing_BVM_Medic",_medic];
                _patient setVariable ["ACM_circulation_CPR_session",[_medic,42]];
                _medic setVariable ["ACM_circulation_CPR_Patient",_patient];
                _medic setVariable ["ACM_circulation_CPR_Epoch",42];
            '''
            execute(setup+'private _valid = {'+body+'};'+'''
                [[_medic,_patient] call _valid,"paused role lost reservation"] call _check;
                [!([missionNamespace,_patient] call _valid),"different provider accepted"] call _check;
                _alive=false;
                [!([_medic,_patient] call _valid),"dead provider retained role"] call _check;
                _alive=true; _unconscious=true;
                [!([_medic,_patient] call _valid),"unconscious provider retained role"] call _check;
                _unconscious=false; _distance=4;
                [!([_medic,_patient] call _valid),"out-of-range provider retained role"] call _check;
            ''')

    def test_cross_provider_role_vars_still_networked(self):
        b=(ADDONS/'breathing/functions/fnc_useBVM.sqf').read_text()
        c=(ADDONS/'circulation/functions/fnc_beginCPR.sqf').read_text()
        self.assertIn('QGVAR(BVM_provider), _medic, true',b)
        self.assertIn('QGVAR(BVM_Medic), _medic, true',b)
        self.assertIn('QACEGVAR(medical,CPR_provider), _medic, true',c)
        self.assertIn('QGVAR(CPR_Medic), _medic, true',c)

if __name__=='__main__': unittest.main()
