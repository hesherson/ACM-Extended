"""Execute delayed head placement and seated treatment gates at engine boundaries.

Actual startup/stop/bridge SQF runs. CBA scheduling, inventory/animation and vehicle
parents are explicit stand-ins; these tests do not certify Arma animation or MP transport.
"""
import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute
from test_bounded_head_start_contracts import start_setup


def pending(route):
    setup = start_setup() + '''
        _actualSide="back";
        ACME_fnc_ownerDispatch={
            _events pushBack _this;
            if ((_this select 1)=="chestAccessFrontRoll") then {_providerRolls pushBack (_this select 2);};
        };
    '''
    if route == "nonphysical":
        setup += '_canRoll=false;\n'
    elif route == "denied":
        setup += 'ACME_fnc_chestSealRoll={_rolls pushBack _this;};\n'
    setup += '[_medic,_patient,"Head"] call ACME_fnc_headElevateStart;\n'
    if route == "physical":
        setup += '''
            [count _untils==1,"missing physical continuation"] call _check;
            private _retry=_untils select 0; _untils=[];
            _patient setVariable ["ACME_CS_rollToken",""];
            private _deliverRetry={(_retry select 2) call (_retry select 1);};
        '''
    else:
        if route == "timeout":
            setup += '''
                [count _untils==1,"missing roll timeout"] call _check;
                private _job=_untils select 0; _untils=[];
                (_job select 2) call (_job select 4);
            '''
        setup += '''
            [count _waits==1,"missing next-slice retry"] call _check;
            private _retry=_waits select 0; _waits=[];
            private _deliverRetry={[_retry] call _deliver;};
        '''
    return setup


RESET_EFFECTS = '''
    _events=[]; _rolls=[]; _restores=[]; _tilts=[]; _starts=[]; _watches=[];
    _patient setVariable ["ACME_CS_facing","sentinel"];
'''

NO_EFFECTS = '''
    [(_patient getVariable ["ACME_CS_facing",""])=="sentinel","retired retry rewrote facing"] call _check;
    [count _tilts==0 && {count _starts==0} && {count _watches==0},"retired retry started placement"] call _check;
    [count _restores==0 && {count _waits==0} && {count _rolls==0} && {count _events==0},"retired retry wrote gear/pose or forwarded to new owner"] call _check;
'''


@pytest.mark.parametrize("route", ["physical", "nonphysical", "denied", "timeout"])
@pytest.mark.parametrize("retire", [
    '_patientLocal=false;',
    '_patientAlive=false;',
    '_alive=false;',
    '_unconscious=true;',
    '_distance=100;',
    '_patient setVariable ["ACME_headElev_poseToken","replacement"];',
    '_patient setVariable ["ACME_CS_rollToken","replacement-roll"];',
    '[_medic,_patient,true] call ACME_fnc_headElevateStop;',
])
def test_retired_normalization_cannot_reenter_or_forward_to_another_owner(route, retire):
    execute(pending(route) + retire + RESET_EFFECTS + 'call _deliverRetry;' + NO_EFFECTS)


@pytest.mark.parametrize("route", ["physical", "nonphysical", "denied", "timeout"])
def test_complete_new_placement_then_stop_does_not_revive_old_empty_token_retry(route):
    execute(pending(route) + '''
        _actualSide="front";
        [_medic,_patient,"Head"] call ACME_fnc_headElevateStart;
        [_patient getVariable ["ACME_headElevated",false],"new placement did not start"] call _check;
        [_medic,_patient,true] call ACME_fnc_headElevateStop;
        [!(_patient getVariable ["ACME_headElevated",true]),"new placement did not stop"] call _check;
        [(_patient getVariable ["ACME_headElev_poseToken","sentinel"])=="","stop did not return token to initial value"] call _check;
    ''' + RESET_EFFECTS + 'call _deliverRetry;' + NO_EFFECTS)


@pytest.mark.parametrize("route", ["physical", "nonphysical", "denied", "timeout"])
def test_current_normalization_still_places_once_and_duplicate_delivery_is_inert(route):
    execute(pending(route) + RESET_EFFECTS + '''
        call _deliverRetry;
        [_patient getVariable ["ACME_headElevated",false],"current retry did not place"] call _check;
        [count _tilts==1 && {count _starts==1} && {count _watches==1},"placement lost or duplicated lift"] call _check;
    ''' + RESET_EFFECTS + 'call _deliverRetry;' + NO_EFFECTS)


@pytest.mark.parametrize("route", ["physical", "nonphysical", "denied", "timeout"])
def test_automatic_transport_restore_keeps_providerless_supported_placement(route):
    update = (
        '(_retry select 2) set [3,objNull]; (_retry select 2) set [5,true];'
        if route == "physical" else
        '(_retry select 1) set [0,objNull]; (_retry select 1) set [3,true];'
    )
    execute(pending(route) + update + RESET_EFFECTS + '''
        _alive=false; _unconscious=true; _distance=100;
        call _deliverRetry;
        [_patient getVariable ["ACME_headElevated",false],"providerless automatic restore was rejected"] call _check;
        [count _tilts==1 && {count _watches==1} && {count _starts==0},"automatic restore requested provider theatre"] call _check;
    ''')


def locality_handler():
    source = (ROOT / "addons/acm_extended/functions/fn_ownerInit.sqf").read_text()
    source = source.split('["CAManBase", "Local", {', 1)[1].split('}] call CBA_fnc_addClassEventHandler;', 1)[0]
    source = source.replace("alive _unit", "_patientAlive").replace("serverTime", "_serverClock")
    return adapt(source)


@pytest.mark.parametrize("route", ["physical", "nonphysical", "denied", "timeout"])
def test_actual_away_and_back_locality_handler_retires_pending_start(route):
    execute(pending(route) + '''
        ACME_fnc_aajtDownedStop={}; ACME_fnc_providerStanceOwned={false};
        ACME_fnc_ownerRegister={}; CBA_fnc_execNextFrame={};
    ''' + 'private _onLocal={' + locality_handler() + '};' + '''
        _patientLocal=false; [_patient,false] call _onLocal;
        _patientLocal=true; [_patient,true] call _onLocal;
        // The real Local handler queues unrelated owner-registration work.
        _waits=[];
    ''' + RESET_EFFECTS + 'call _deliverRetry;' + NO_EFFECTS)


@pytest.mark.parametrize("route", ["physical", "nonphysical", "denied", "timeout"])
def test_actual_full_heal_begin_retires_pending_start(route):
    source = (ROOT / "addons/acm_extended/functions/fn_clinicalReset.sqf").read_text()
    source = source.split('// Physical equipment is detached', 1)[0]
    execute(pending(route) + '''
        ACME_fnc_aajtDownedStop={}; ACME_fnc_ventDeviceFields={[]};
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["ACME_clinicalEpoch",0]};
        ACM_breathing_fnc_setRuntimeState={}; ACM_circulation_fnc_setRuntimeState={};
        ACM_airway_fnc_setAirwayState={};
    ''' + 'private _reset={' + adapt(source) + '};' + '''
        [_patient,"begin"] call _reset;
        [(_patient getVariable ["ACME_clinicalEpoch",0])==1,"real full-heal begin was not exercised"] call _check;
    ''' + RESET_EFFECTS + 'call _deliverRetry;' + NO_EFFECTS)


def bridge():
    source = (ROOT / "addons/core/overrides/fnc_treatment.sqf").read_text()
    # Preserve the vehicle-parent boundary before the general namespace adapter.
    source = source.replace("objectParent _medic", "_medicParent")
    source = source.replace("objectParent _patient", "_patientParent")
    # Native Arma network-owner identities are not implemented by the SQF VM;
    # B263 uses both in its *refusal-only* diagnostic message. Keep the denial
    # branches executable and retain their clinical admission assertions.
    source = source.replace("owner _medic", "_ownerNum")
    source = source.replace("owner _patient", "_ownerNum")
    return adapt(source)


@pytest.mark.parametrize("action", ["ACME_ApplyChestSeal", "ACME_PerformThoracostomy", "ACME_VentOpenPatient", "ACME_ConnectETVent"])
@pytest.mark.parametrize("self_treatment", [False, True])
@pytest.mark.parametrize("eligible", [False, True])
def test_seated_bridge_preserves_native_self_and_passenger_eligibility(action, self_treatment, eligible):
    execute(f'''
        private _medicParent=missionNamespace; private _patientParent=_medicParent;
        private _eligible={str(eligible).lower()}; private _launches=[]; private _exceptions=[];
        private _nativeChecks=0;
        {"_patient=_medic;" if self_treatment else "_distance=100;"}
        ace_common_fnc_isPlayer={{false}};
        ACME_fnc_procedureActionAllowed={{true}};
        ace_medical_treatment_fnc_canTreatCached={{_nativeChecks=_nativeChecks+1; _eligible}};
        // Supplied ACE common/XEH_postInit.sqf isNotInside condition: another passenger
        // is accepted, self inside is rejected. No controlled UAV is present in this fixture.
        ace_common_fnc_canInteractWith={{
            params ["_unit","_target","_exceptionsPassed"];
            _exceptions=+_exceptionsPassed;
            ("isNotInside" in _exceptionsPassed) || {{
                _medicParent isEqualTo objNull || {{_medicParent isEqualTo _target}}
                || {{_unit isNotEqualTo _target && {{_patientParent isNotEqualTo objNull}} && {{_medicParent isEqualTo _patientParent}}}}
            }}
        }};
        ACME_fnc_chestSealOpen={{_launches pushBack _this;}};
        ACME_fnc_thoraOpen={{_launches pushBack _this;}};
        ACME_fnc_ventPanelOpen={{_launches pushBack _this;}};
        ACME_fnc_ventConnectPatient={{_launches pushBack _this;}};
        ACME_fnc_ventRecoveryNear={{true}};
        private _entry={{ {bridge()} }};
        private _accepted=[_medic,_patient,"body","{action}"] call _entry;
        [_accepted isEqualTo _eligible,"bridge overrode native seated eligibility"] call _check;
        [count _launches=={int(eligible)},"seated intervention was lost or incorrectly started"] call _check;
        [_nativeChecks==1,"native config gate was bypassed"] call _check;
    ''')
