"""Execute protocol-2 bootstrap, fallback and mixed-installation rejection.

CfgPatches reads are the native boundary. The assignment extracted from actual
startup and the production manifest/comparison execute with independent current
contract expectations, including runtime state absent during early startup.
"""
import json
import re

import pytest

from test_b207_network_compat_execution import adapted, setup
from test_menu_death_lifecycle import ROOT, execute, read


CONFIG_PROTOCOL = 'getNumber (configFile >> "CfgPatches" >> "ACM_Extended" >> "acmeNetworkProtocol")'


def test_current_protocol_two_is_compiled_and_assigned_from_the_loaded_component():
    contract = json.loads((ROOT / 'tools/current_build_contract.json').read_text())
    from historical_source import assert_release_identity
    assert_release_identity()
    assert contract['network_protocol'] >= 2
    header = (ROOT / 'addons/main/script_build.hpp').read_text()
    assert re.findall(r'\bacmeNetworkProtocol\s*=\s*(\d+)', header) == [str(contract['network_protocol'])]
    assert re.findall(r'\bacmeBuildBatch\s*=\s*"([^"]+)"', header) == [contract['batch']]
    startup = read('initForkStartupRuntime')
    assignment = re.findall(r'^ACME_networkProtocol\s*=\s*[^;]+;', startup, re.M)
    assert assignment == [f'ACME_networkProtocol = {CONFIG_PROTOCOL};']
    execute(setup(initialize=False, protocol=2, batch='B285') + r'''
        missionNamespace setVariable ["ACME_networkProtocol",nil];
    ''' + adapted(assignment[0], protocol=2) + r'''
        [ACME_networkProtocol==2,"actual startup did not install loaded protocol two"] call _check;
        private _m=[] call ACME_fnc_networkCompatManifest;
        [(_m select 3)==2 && {count (_m select 5)==19},"bootstrap manifest lost protocol or components"] call _check;
        [(_m select 5 findIf {(_x select 3)!=2})<0,"runtime protocol disagreed with compiled PBO stamps"] call _check;
        [([_m,_m] call ACME_fnc_networkCompatCompare) isEqualTo [],"bootstrap self-manifest rejected"] call _check;
    ''')


@pytest.mark.parametrize('runtime_present', [True, False])
def test_protocol_two_matches_server_player_and_headless_with_or_without_runtime_state(runtime_present):
    # Removing the runtime value exercises the exact native CfgPatches fallback
    # in production Manifest, rather than a fixture default copied into state.
    absent_check = '' if runtime_present else '[isNil "ACME_networkProtocol","fixture published runtime protocol before fallback"] call _check;'
    execute(setup(initialize=False, protocol=2, batch='B285', publish_protocol=runtime_present) + absent_check + r'''
        _server=true; _interface=false;
        _serverManifest=[] call ACME_fnc_networkCompatManifest;
        _server=false; _interface=true;
        _clientManifest=[] call ACME_fnc_networkCompatManifest;
        _interface=false;
        _hcManifest=[] call ACME_fnc_networkCompatManifest;
        [(_serverManifest select 3)==2 && {(_clientManifest select 3)==2} && {(_hcManifest select 3)==2},"early/runtime manifest fell back to old protocol"] call _check;
        [(_serverManifest select 4)=="server" && {(_clientManifest select 4)=="client"} && {(_hcManifest select 4)=="HC"},"roles changed during protocol publication"] call _check;
        [([_serverManifest,_clientManifest] call ACME_fnc_networkCompatCompare) isEqualTo [],"matching protocol-two player rejected"] call _check;
        [([_serverManifest,_hcManifest] call ACME_fnc_networkCompatCompare) isEqualTo [],"matching protocol-two HC rejected"] call _check;
    ''')


@pytest.mark.parametrize('interface', [True, False])
def test_protocol_one_peer_is_incompatible_with_current_server(interface):
    execute(setup(initialize=False, protocol=2, batch='B285') + f'_interface={str(interface).lower()};' + r'''
        _server=false;
        _compiledProtocol=1; ACME_networkProtocol=1;
        private _old=[] call ACME_fnc_networkCompatManifest;
        [(_old select 5 findIf {(_x select 3)!=1})<0,"old-peer fixture retained new component protocols"] call _check;
        private _issues=[_serverManifest,_old] call ACME_fnc_networkCompatCompare;
        [count _issues==1 && {(_issues select 0 find "Protocol differs")>=0},"old complete protocol-one peer was not explicitly rejected"] call _check;
    ''')


@pytest.mark.parametrize('interface', [True, False])
def test_one_protocol_one_pbo_is_rejected_even_when_top_level_protocol_is_two(interface):
    execute(setup(initialize=False, protocol=2, batch='B285') + f'_interface={str(interface).lower()};' + r'''
        _server=false;
        _staleProtocolComponents=["ACM_core"];
        private _mixed=[] call ACME_fnc_networkCompatManifest;
        [(_mixed select 3)==2,"mixed-component fixture changed top-level protocol"] call _check;
        private _issues=[_serverManifest,_mixed] call ACME_fnc_networkCompatCompare;
        [count _issues==1 && {(_issues select 0 find "ACM_core stale/unmarked")>=0},"mixed protocol-one PBO escaped component validation"] call _check;
    ''')
