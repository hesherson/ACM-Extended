"""Execute Hang Bag claim/ACK code with Arma's server-only owner semantics.

Only engine boundaries and network delivery are fixtures; production acquisition,
renewal, acceptance, cancellation and episode validation execute unchanged.
"""
import re
import pytest
from test_menu_death_lifecycle import F, adapt, execute


def source(name):
    text = (F / f"fn_{name}.sqf").read_text()
    for old, new in {
        'owner _medic': '(if (_server) then {_serverProviderOwner} else {0})',
        'clientOwner': '_clientId',
        'isServer': '_server',
        'isMultiplayer': 'true',  # This module exercises multiplayer; B208 separately covers single player.
        'local _medic': '_medicLocal',
        'local _patient': '_patientLocal',
        'serverTime': '_nowTime',
        'alive _holder': '_alive',
        'finite _episode': '(_episode isEqualType 0)',
        'finite _flow': '(_flow isEqualType 0)',
        'getPosASL _medic': '[0,0,0]',
    }.items():
        text = text.replace(old, new)
    text = re.sub(r'\bfinite (_\w+)', r'(\1 isEqualType 0)', text)
    text = re.sub(r'\bfinite \((_[^()]+)\)', r'((\1) isEqualType 0)', text)
    text = text.replace('[objNull]', '[profileNamespace]')
    return adapt(text)


def setup():
    result = r'''
        private _server=false; private _clientId=7; private _serverProviderOwner=7;
        private _medicLocal=true; private _patientLocal=false;
        private _requests=[]; private _acks=[]; private _activated=[]; private _restores=[];
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["ACME_clinicalEpoch",0]};
        ACME_fnc_hangBagActivate={_activated pushBack _this;};
        ACME_fnc_hangBagPrepStop={_restores pushBack _this;};
        ACME_fnc_hangBagFluidType={"saline"};
        ACME_fnc_hangBagTick={};
        ACME_fnc_ownerDispatch={_requests pushBack _this;};
        CBA_fnc_targetEvent={_acks pushBack _this;};
    '''
    for name in ("actionClaimValidate", "actionClaimLedger", "hangBagStart", "hangBagClaimLocal", "hangBagClaimAck"):
        result += f"ACME_fnc_{name}={{" + source(name) + "};"
    result += "ACME_fnc_hangBagStop={" + source("hangBagStop").split("private _visualEpoch =", 1)[0] + "};"
    result += "private _tickHang={" + source("hangBagTick").split("// auto-lower when", 1)[0] + "};"
    return result + r'''
        private _deliverRequest={
            (_requests select _this) params ["_p","_op","_data"];
            [_p, if (_op=="hangBagClaim") then {"claim"} else {if (_op=="hangBagRenew") then {"renew"} else {"release"}}, _data] call ACME_fnc_hangBagClaimLocal;
        };
        private _deliverAck={(_acks select _this select 1) call ACME_fnc_hangBagClaimAck;};
        private _providerMachine={_server=false;_clientId=7;_medicLocal=true;_patientLocal=false;};
        private _dedicatedMachine={_server=true;_clientId=2;_medicLocal=false;_patientLocal=true;};
    '''


@pytest.mark.parametrize("patient_machine", [
    "call _dedicatedMachine;",
    "_server=false;_clientId=21;_medicLocal=false;_patientLocal=true;",  # HC owner
    "_server=false;_clientId=9;_medicLocal=false;_patientLocal=true;",   # another player
    "_server=false;_clientId=7;_medicLocal=true;_patientLocal=true;",    # same client
])
def test_real_client_claim_accepts_on_dedicated_client_and_hc_patient_owners(patient_machine):
    execute(setup() + r'''
        [_medic,_patient,"leftarm","saline"] call ACME_fnc_hangBagStart;
        [(_medic getVariable ["ACME_hang_ClaimOwner",-1])==7,"provider saved server-only owner 0"] call _check;
        [(_requests select 0 select 2 select 4)==7,"request sent server-only owner 0"] call _check;
        [count _activated==0,"presentation preceded owner acceptance"] call _check;
    ''' + patient_machine + r'''
        0 call _deliverRequest;
        [(_acks select 0 select 1 select 3),"valid remote claim rejected"] call _check;
        [(_acks select 0 select 2) isEqualTo _medic,"ACK did not target provider object"] call _check;
        call _providerMachine; 0 call _deliverAck;
        [count _activated==1,"client dropped its valid ACK because owner returns 0"] call _check;
        _nowTime=12;
        [[_medic,_patient],0] call _tickHang;
        [(_requests select 1 select 2 select 4)==7,"renewal sent server-only owner 0"] call _check;
    ''' + patient_machine + r'''
        1 call _deliverRequest;
        [(_acks select 1 select 1 select 3),"valid renewal rejected"] call _check;
        call _providerMachine; 1 call _deliverAck;
        [count _activated==1,"renewal repeated presentation"] call _check;
    ''')


@pytest.mark.parametrize("invalid", [
    "call _dedicatedMachine; _serverProviderOwner=9;",
    "_server=false;_clientId=9;_medicLocal=true;_patientLocal=true;",
    'call _dedicatedMachine; (_requests select 0 select 2) set [4,0];',
    'call _dedicatedMachine; _patient setVariable ["ACME_clinicalEpoch",1];',
])
def test_patient_owner_rejects_known_wrong_owner_zero_id_and_old_clinical_epoch(invalid):
    execute(setup() + r'''
        [_medic,_patient,"leftarm","saline"] call ACME_fnc_hangBagStart;
    ''' + invalid + r'''
        0 call _deliverRequest;
        [!(_acks select 0 select 1 select 3),"stale/invalid claim accepted"] call _check;
        call _providerMachine; 0 call _deliverAck;
        [count _activated==0 && {!(_medic getVariable ["ACME_hang_Active",true])},"rejected claim started hold"] call _check;
    ''')


def test_accepted_ack_cannot_start_on_replacement_provider_owner():
    execute(setup() + r'''
        [_medic,_patient,"leftarm","saline"] call ACME_fnc_hangBagStart;
        call _dedicatedMachine; 0 call _deliverRequest;
        call _providerMachine; _clientId=9; 0 call _deliverAck;
        [count _activated==0 && {!(_medic getVariable ["ACME_hang_Active",true])},"old owner ACK started transferred provider"] call _check;
    ''')


def test_cancelled_pending_claim_late_ack_cannot_activate_after_network_delay():
    execute(setup() + r'''
        [_medic,_patient,"leftarm","saline"] call ACME_fnc_hangBagStart;
        call _dedicatedMachine; 0 call _deliverRequest;
        call _providerMachine; [true,_medic] call ACME_fnc_hangBagStop;
        0 call _deliverAck;
        [count _activated==0 && {count _restores==1},"cancelled pending lease restarted or lost equipment restore"] call _check;
    ''')
