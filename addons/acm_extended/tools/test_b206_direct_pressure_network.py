"""Execute the DP handshake, with owner returning zero off-server as in Arma.

Network queues and engine presentation are explicit stand-ins; Start, ClaimLocal,
and ClaimAck are the actual source. This cannot certify real transport or poses.
"""
import re
import pytest
from test_menu_death_lifecycle import adapt, execute, read


def network_source(name, source=None):
    if source is None:
        source = read(name)
    # Protect these engine boundaries from the older all-local fixture adapter.
    for command, replacement in {
        'clientOwner': '_machine',
        'isServer': '(_machine == 2 || {!(missionNamespace getVariable ["TEST_multiplayer",true])})',
        'isMultiplayer': '(missionNamespace getVariable ["TEST_multiplayer",true])',
        'serverTime': '_networkTime',
        'diag_frameNo': '100',
        'netId _medic': '"medic"',
        'finite _at': 'true',  # All timestamps in these fixtures are finite.
    }.items():
        source = re.sub(r'\b' + re.escape(command) + r'\b', lambda _: replacement, source)
    source = re.sub(r'\bowner (_\w+)', r'([\1] call _engineOwner)', source)
    source = re.sub(r'\blocal (_\w+)', r'((\1 getVariable ["TEST_owner",-1]) == _machine)', source)
    source = re.sub(r'\balive (_\w+)', r'(\1 getVariable ["TEST_alive",true])', source)
    # Claim helper fixtures supply finite values; SQF-VM does not implement this
    # native predicate. Preserve its numeric type boundary for those inputs.
    source = re.sub(r'\bfinite (_\w+)', r'(\1 isEqualType 0)', source)
    source = re.sub(r'\bfinite \((_[^()]+)\)', r'((\1) isEqualType 0)', source)
    source = source.replace('[objNull]', '[profileNamespace]')
    # VM namespace deletion keeps a nil slot instead of restoring getVariable's
    # default. The debounce's absent-value default is -1 in the actual source.
    source = source.replace('_patient setVariable [_key, nil, false];', '_patient setVariable [_key, -1, false];')
    # SQF-VM does not preserve defaults on missing typed params. Remove only the
    # engine type tag; keep the actual default value and all claim decisions.
    source = re.sub(r'(\bparam\s*\[\s*\d+\s*,\s*(?:"[^"]*"|-?\d+))\s*,\s*\[(?:""|0)\](\s*\])', r'\1\2', source)
    return adapt(source)


def setup():
    source = '''
        private _machine = 7;
        private _networkTime = 1000;
        private _wire = [];
        private _acknowledgments = [];
        private _started = [];
        _medic setVariable ["TEST_owner",7];
        _patient setVariable ["TEST_owner",2];
        private _engineOwner = {if (_machine == 2) then {(_this select 0) getVariable ["TEST_owner",-1]} else {0}};
        ACME_fnc_clinicalEpoch = {(_this select 0) getVariable ["ACME_clinicalEpoch",0]};
        ACME_fnc_directPressureStop = {};
        ACME_fnc_markImportantSfx = {};
        ACME_fnc_worldSfxNearby = {};
        ACM_core_fnc_cprActive = {false};
        ACM_core_fnc_bvmActive = {false};
        ace_medical_status_fnc_updateWoundBloodLoss = {};
        CBA_fnc_ownerEvent = {
            _wire pushBack [_this select 0,_this select 1,_this select 2];
        };
        CBA_fnc_targetEvent = {
            _wire pushBack [_this select 0,_this select 1,(_this select 2) getVariable ["TEST_owner",-1]];
        };
        ACME_fnc_ownerDispatch = {
            params ["_p","_op","_args"];
            if (_op == "directPressureClaim") then {
                _wire pushBack ["claim",[_p,_args select 0,_args select 1],_p getVariable ["TEST_owner",-1]];
            };
        };
        private _activate = {
            params ["_m","_p","_part"];
            _started pushBack _this;
            _m setVariable ["ACME_DP_Active",true];
            _m setVariable ["ACME_DP_Patient",_p];
            _m setVariable ["ACME_DP_Part",_part];
        };
        ACME_fnc_directPressureTorso = _activate;
        ACME_fnc_directPressureLimb = _activate;
        ACME_fnc_directPressureSelf = _activate;
    '''
    for name in ('actionClaimValidate', 'actionClaimLedger', 'directPressureStart', 'directPressureClaimLocal', 'directPressureClaimAck'):
        source += f'ACME_fnc_{name} = {{' + network_source(name) + '};'
    source += '''
        private _deliver = {
            private _message = _wire deleteAt 0;
            _message params ["_event","_payload","_destination"];
            _machine = _destination;
            if (_event == "claim") then {_payload call ACME_fnc_directPressureClaimLocal;};
            if (_event == "ACME_directPressureClaimAck") then {
                _acknowledgments pushBack _message;
                _payload call ACME_fnc_directPressureClaimAck;
            };
        };
    '''
    return source


@pytest.mark.parametrize('patient_owner', [2, 8, 9, 7], ids=['dedicated-ai', 'remote-player', 'headless-ai', 'local-ai'])
@pytest.mark.parametrize('part', ['body', 'leftarm', 'head'])
def test_actual_handshake(patient_owner, part):
    execute(setup() + f'_patient setVariable ["TEST_owner",{patient_owner}];' + f'''
        [_medic,_patient,"{part}"] call ACME_fnc_directPressureStart;
    ''' + '''
        [count _wire == 1,"owner request not sent"] call _check;
        [count _started == 0,"pressure activated before owner accepted"] call _check;
        [((((_wire select 0) select 1) select 2) select 4) == 7,"provider sent wrong machine identity"] call _check;
        call _deliver;
        [count _wire == 1,"reply not sent"] call _check;
        [((_wire select 0) select 2) == 7,"reply sent to wrong machine"] call _check;
        [count _started == 0,"pressure activated before reply delivered"] call _check;
        call _deliver;
        [count _started == 1,"handshake never activates pressure"] call _check;
        [(_medic getVariable ["ACME_DP_ClaimPending",[]]) isEqualTo [],"claim stuck pending"] call _check;
    ''')


def test_self_pressure_uses_same_handshake():
    execute(setup() + '''
        [_medic,_medic,"leftarm"] call ACME_fnc_directPressureStart;
        call _deliver; call _deliver;
        [_started isEqualTo [[_medic,_medic,"leftarm"]],"self pressure did not activate"] call _check;
    ''')


def test_remote_provider_cannot_create_a_client_local_pending_episode():
    execute(setup() + '''
        _machine = 8;
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        [count _wire == 0,"remote caller sent an invalid provider identity"] call _check;
        [(_medic getVariable ["ACME_DP_ClaimPending",[]]) isEqualTo [],"remote caller left a pending episode"] call _check;
    ''')


@pytest.mark.parametrize('patient_owner', [2, 8, 9])
def test_competing_claim_cannot_steal_pending_or_active_site(patient_owner):
    execute(setup() + f'_patient setVariable ["TEST_owner",{patient_owner}];' + '''
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        call _deliver;
        private _other = parsingNamespace;
        _other setVariable ["TEST_owner",11];
        [_patient,"claim",[_other,"leftarm","other",0,11,_networkTime]] call ACME_fnc_directPressureClaimLocal;
        [!(((_wire select 1) select 1) select 4),"pending reservation stolen"] call _check;
        [((_patient getVariable "ACME_DP_claim_leftarm") select 0) isEqualTo _medic,"pending holder replaced"] call _check;
        call _deliver;
        _wire = [];
        _machine = _patient getVariable "TEST_owner";
        _networkTime = 1005;
        [_patient,"claim",[_other,"leftarm","other-new",0,11,_networkTime]] call ACME_fnc_directPressureClaimLocal;
        [!(((_wire select 0) select 1) select 4),"active reservation stolen"] call _check;
    ''')


def test_late_accepted_reply_releases_its_cancelled_reservation():
    execute(setup() + '''
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        call _deliver;
        _medic setVariable ["ACME_DP_ClaimPending",[]];
        call _deliver;
        [count _started == 0,"late reply restarted cancelled hold"] call _check;
        [count _wire == 1,"late reply did not release owner reservation"] call _check;
        call _deliver;
        [(_patient getVariable ["ACME_DP_claim_leftarm",[]]) isEqualTo [],"cancelled reservation survived"] call _check;
    ''')


def test_old_reply_release_cannot_erase_newer_token_for_same_provider():
    execute(setup() + '''
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        call _deliver;
        _medic setVariable ["ACME_DP_ClaimPending",[_patient,"leftarm","replacement",0]];
        [_patient,"claim",[_medic,"leftarm","replacement",0,7,_networkTime]] call ACME_fnc_directPressureClaimLocal;
        call _deliver;
        [count _started == 0,"stale reply started replacement hold"] call _check;
        call _deliver;
        [count _started == 1,"replacement reply did not activate"] call _check;
        call _deliver;
        [((_patient getVariable "ACME_DP_claim_leftarm") select 1) == "replacement","old release erased new reservation"] call _check;
        [(_patient getVariable ["ACME_DP_press_leftarm",objNull]) isEqualTo _medic,"old release cleared new pressure marker"] call _check;
    ''')


@pytest.mark.parametrize('invalidate', [
    '_medic setVariable ["TEST_owner",9];',
    '_patient setVariable ["ACME_clinicalEpoch",1];',
    '_medic setVariable ["ACE_isUnconscious",true];',
])
def test_accepted_reply_revalidates_before_activation(invalidate):
    execute(setup() + '''
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        call _deliver;
    ''' + invalidate + '''
        // CBA target routing resolves the destination before delivery. Model a
        // migrated provider by delivering on its current machine.
        (_wire select 0) set [2,_medic getVariable "TEST_owner"];
        call _deliver;
        [count _started == 0,"stale accepted reply activated pressure"] call _check;
        [count _wire == 1,"stale accepted reply did not release"] call _check;
        call _deliver;
        [(_patient getVariable ["ACME_DP_claim_leftarm",[]]) isEqualTo [],"stale accepted reservation survived"] call _check;
    ''')


@pytest.mark.parametrize('patient_owner, request_owner', [(2, 0), (2, 11), (7, 11)])
def test_owner_validation_rejects_invalid_identity_when_it_can_resolve_provider(patient_owner, request_owner):
    execute(setup() + f'''
        _patient setVariable ["TEST_owner",{patient_owner}];
        _machine = {patient_owner};
        [_patient,"claim",[_medic,"leftarm","invalid",0,{request_owner},_networkTime]] call ACME_fnc_directPressureClaimLocal;
    ''' + '''
        [!(((_wire select 0) select 1) select 4),"invalid provider identity accepted"] call _check;
        [(_patient getVariable ["ACME_DP_claim_leftarm",[]]) isEqualTo [],"invalid identity reserved site"] call _check;
    ''')


@pytest.mark.parametrize('patient_owner', [2, 8, 9, 7])
def test_owner_reconcile_preserves_pending_claim_until_actual_timeout(patient_owner):
    # Execute the real debounce helper and DP reconciliation region, excluding
    # independent BVM/CPR, IV, bandage, and chest-equipment systems.
    source = read('transientStateReconcile')
    preamble = source.split('// BVM reservation.', 1)[0]
    pressure = '// Direct Pressure claims and clinical markers.' + source.split('// Direct Pressure claims and clinical markers.', 1)[1].split('// Progressive bandage records.', 1)[0]
    reconcile = network_source('transientStateReconcile', preamble + pressure)
    execute(setup() + 'private _reconcile = {' + reconcile + '};' + f'''
        _patient setVariable ["TEST_owner",{patient_owner}];
    ''' + '''
        [_medic,_patient,"leftarm"] call ACME_fnc_directPressureStart;
        call _deliver;
        [_patient] call _reconcile;
        CBA_missionTime = 12.5; _networkTime = 1002.5;
        [_patient] call _reconcile;
        [count (_patient getVariable ["ACME_DP_claim_leftarm",[]]) == 5,"reconcile retired a live pending reservation"] call _check;
        CBA_missionTime = 14; _networkTime = 1004;
        [_patient] call _reconcile;
        CBA_missionTime = 16; _networkTime = 1006;
        [_patient] call _reconcile;
        [(_patient getVariable ["ACME_DP_claim_leftarm",[]]) isEqualTo [],"expired unanswered reservation survived reconciliation"] call _check;
    ''')
