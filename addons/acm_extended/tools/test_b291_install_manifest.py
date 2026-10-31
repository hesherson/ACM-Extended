"""Execute installation diagnostics for all five newly integrated addon owners."""
import json

import pytest

from test_b207_network_compat_execution import execute, setup
from test_runtime_compatibility_install import test_checker_preserves_real_failures_and_never_replaces_a_binding as _check_runtime_binding


PORTS = ("ACM_burns", "ACM_infection", "ACM_ophthalmology", "DD1380_main", "DD1380_card")


@pytest.mark.parametrize("function", ("DD1380_card_fnc_openCardLocal", "DD1380_card_fnc_setData"))
@pytest.mark.parametrize("state", ("upstream", "missing", "wrong_type"))
def test_standalone_dd1380_override_is_reported_without_replacing_its_function(function, state):
    _check_runtime_binding(state, function)


@pytest.mark.parametrize("component", PORTS)
def test_missing_clinical_or_card_pbo_is_explicit(component):
    execute(setup(initialize=False, protocol=2, batch="B291") + f'''
        _missingComponents = [{json.dumps(component)}];
        private _m = [] call ACME_fnc_networkCompatManifest;
        private _issues = [_m, _m] call ACME_fnc_networkCompatCompare;
        [count _issues == 1, "missing imported component was hidden or invented other issues"] call _check;
        [((_issues select 0) find {json.dumps(component)}) >= 0, "missing imported owner was not named"] call _check;
    ''')


@pytest.mark.parametrize("component", PORTS)
@pytest.mark.parametrize("stale", ("build", "protocol"))
def test_mixed_imported_component_is_detected(component, stale):
    variable = "_staleComponents" if stale == "build" else "_staleProtocolComponents"
    execute(setup(initialize=False, protocol=2, batch="B291") + f'''
        {variable} = [{json.dumps(component)}];
        private _m = [] call ACME_fnc_networkCompatManifest;
        private _issues = [_m, _m] call ACME_fnc_networkCompatCompare;
        [count _issues == 1, "mixed imported PBO escaped exact build/protocol diagnostics"] call _check;
        [((_issues select 0) find {json.dumps(component)}) >= 0, "stale imported owner was not named"] call _check;
    ''')


def test_dd1380_foreign_namespaces_keep_their_actual_component_stamps():
    execute(setup(initialize=False, protocol=2, batch="B291") + '''
        private _m = [] call ACME_fnc_networkCompatManifest;
        [count (_m select 5) == 19, "incomplete integrated installation"] call _check;
        {
            _x params ["_patch", "_stamp"];
            private _rows = (_m select 5) select {(_x select 0) == _patch};
            [count _rows == 1 && {((_rows select 0) select 4) == _stamp}, "DD1380 namespace was treated as an ACM prefix"] call _check;
        } forEach [["DD1380_main", "card_main"], ["DD1380_card", "card"]];
        [([_m, _m] call ACME_fnc_networkCompatCompare) isEqualTo [], "correct foreign component stamp was rejected"] call _check;
    ''')
