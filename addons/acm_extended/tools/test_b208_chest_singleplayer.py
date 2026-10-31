"""Execute chest intentions/ACKs with explicit SP and multiplayer engine identities.

Namespaces represent engine objects; CBA transport and UI/equipment effects are
recorded boundaries. The production edit, key and ACK functions execute. These
tests do not certify live CBA delivery or Arma rendering.
"""
import re

import pytest

from test_menu_death_lifecycle import adapt, execute, read


def adapted(source):
    for command, replacement in (
        ("isServer", "_server"), ("isMultiplayer", "_multiplayer"),
        ("clientOwner", "_clientId"),
    ):
        source = re.sub(r"\b" + command + r"\b", replacement, source)
    source = re.sub(r"\blocal (_\w+)", r'(\1 getVariable ["TEST_local",true])', source)
    # The VM supports namespace identity through isEqualTo, not object ==.
    source = re.sub(r"== (_patient|_originalPatient)\b", r"isEqualTo \1", source)
    # Inputs in this fixture are finite; the VM lacks the native finite command.
    source = re.sub(r"\bfinite (_\w+)", r"(\1 isEqualType 0)", source)
    source = re.sub(r"(\w+) getOrDefault \[(_\w+), (\[\]|0)\]", r"[\1,\2,\3] call _getDefault", source)
    return adapt(source)


def setup(client=0, multiplayer=False, server=True):
    code = f"private _server={str(server).lower()}; private _multiplayer={str(multiplayer).lower()}; private _clientId={client};"
    code += r'''
        private _getDefault = {params ["_map","_key","_default"]; if (_key in _map) then {_map get _key} else {_default}};
        private _viewer = _medic;
        private _messages=[]; private _refunds=[]; private _commits=0;
        CBA_missionTime=100; ACE_player=_medic;
        ACME_CS_editResults=createHashMap; ACME_CS_pending=createHashMap;
        private _hole=["front",0.4,0.5,true,false,"hole",0,0,"hole-1"];
        _patient setVariable ["ACME_CS_netSnapshot",["epoch",1,[_hole],[],[]]];
        _patient setVariable ["ACME_CS_holeVer",1];
        uiNamespace setVariable ["ACME_CS_Patient",_patient];
        uiNamespace setVariable ["ACME_CS_DLG",objNull];
        CBA_fnc_targetEvent={_messages pushBack _this;};
        CBA_fnc_serverEvent={};
        ACME_fnc_chestSealSyncUI={};
        ACME_fnc_treatmentSupplyRefund={_refunds pushBack _this;};
        ACME_fnc_chestSealBumpVer={
            params ["_p","_rows"]; _commits=_commits+1;
            _p setVariable ["ACME_CS_holeVer",2];
            _p setVariable ["ACME_CS_netSnapshot",["epoch",2,_rows,_p getVariable ["ACME_CS_wastedData",[]],_p getVariable ["ACME_CS_ncdPlacedSides",[]]]];
        };
    '''
    for name in ("chestSealKey", "chestSealEdit", "chestSealAck"):
        code += f"ACME_fnc_{name}={{" + adapted(read(name)) + "};"
    return code


@pytest.mark.parametrize("dead", [False, True], ids=["living", "dead"])
@pytest.mark.parametrize("operation,payload", [
    ("reveal", '[["hole-1"]]'), ("seal", '["hole-1"]'),
    ("peel", '["hole-1"]'), ("waste", '["front",0.2,0.3]'),
    ("miss", '["back",0.2,0.3]'), ("ncd", '["left"]'),
])
def test_singleplayer_intention_receives_ack_and_settles_once(dead, operation, payload):
    prepare = '((_patient getVariable "ACME_CS_netSnapshot") select 2 select 0) set [4,true];' if operation == "peel" else ""
    execute(setup() + f"_patientAlive={str(not dead).lower()};" + prepare + f'''
        private _request=[_patient,_medic,_viewer,"request-0","epoch",1,"{operation}",{payload},100,0];
        ACME_CS_pending set ["request-0",[_request,["receipt"],100]];
        _request call ACME_fnc_chestSealEdit;
        private _ackIndex=_messages findIf {{(_x select 0)=="ACME_CS_ack"}};
        [_ackIndex>=0,"SP chest request was silently dropped"] call _check;
        if (_ackIndex>=0) then {{
            private _ack=_messages select _ackIndex;
            [(_ack select 2) isEqualTo _viewer,"ACK was not addressed to the viewer object"] call _check;
            [(_ack select 1 select 2),"valid SP intention was rejected"] call _check;
            (_ack select 1) call ACME_fnc_chestSealAck;
            (_ack select 1) call ACME_fnc_chestSealAck;
            [count ACME_CS_pending==0,"ACK did not clear pending request"] call _check;
            [_refunds isEqualTo [[["receipt"],false]],"receipt was refunded or settled twice"] call _check;
        }};
        private _firstCommits=_commits;
        _request call ACME_fnc_chestSealEdit;
        [_commits==_firstCommits,"duplicate request committed a second edit"] call _check;
    ''')


@pytest.mark.parametrize("client", [2, 7], ids=["hosted", "dedicated-client"])
def test_multiplayer_valid_machine_still_receives_ack(client):
    execute(setup(client=client, multiplayer=True) + f'''
        [_patient,_medic,_viewer,"mp","epoch",1,"seal",["hole-1"],100,{client}] call ACME_fnc_chestSealEdit;
        [(_messages findIf {{(_x select 0)=="ACME_CS_ack" && {{_x select 1 select 2}}}})>=0,"MP edit was rejected"] call _check;
    ''')


@pytest.mark.parametrize("mode", ["mp-zero", "mp-one", "sp-negative", "sp-remote-viewer", "sp-remote-medic", "not-server", "fractional"])
def test_singleplayer_exception_does_not_admit_invalid_network_request(mode):
    changes = {
        "mp-zero": "_multiplayer=true;",
        "mp-one": "_multiplayer=true; _reply=1;",
        "sp-negative": "_reply=-1;",
        "sp-remote-viewer": '_viewer=parsingNamespace; _viewer setVariable ["TEST_local",false];',
        "sp-remote-medic": '_medic setVariable ["TEST_local",false];',
        "not-server": "_server=false;",
        "fractional": "_reply=2.5;",
    }
    execute(setup() + "private _reply=0;" + changes[mode] + r'''
        [_patient,_medic,_viewer,"invalid","epoch",1,"seal",["hole-1"],100,_reply] call ACME_fnc_chestSealEdit;
        [count _messages==0 && {_commits==0},"invalid identity edited the chest or received an ACK"] call _check;
    ''')
