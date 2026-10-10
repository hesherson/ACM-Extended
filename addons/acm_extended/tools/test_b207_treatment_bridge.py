"""Execute the immediate Direct Pressure bridge without assuming an immediate ACK."""
import pytest
from historical_source import assert_release_identity as _assert_current_build
from test_menu_death_lifecycle import ROOT, adapt, execute
from test_b204_network_full_audit_20260929 import global_sound_calls


def bridge():
    source = (ROOT / "addons/core/overrides/fnc_treatment.sqf").read_text()
    start = source.index('if (_classname == "ACME_DirectPressure") exitWith {')
    end = source.index('// Stop Direct Pressure', start)
    return adapt(source[start:end])


@pytest.mark.parametrize("eligible,submitted", [(True, True), (True, False), (False, False)])
def test_medical_click_reports_request_submission_before_asynchronous_activation(eligible, submitted):
    execute(f'''
        private _eligible = {str(eligible).lower()};
        private _submitted = {str(submitted).lower()};
        private _starts = 0; private _refreshes = 0; private _sounds = 0;
        ace_medical_treatment_fnc_canTreatCached = {{_eligible}};
        ACME_fnc_directPressureStart = {{_starts = _starts + 1; _submitted}};
        ACME_fnc_markImportantSfx = {{_sounds = _sounds + 1;}};
        ACME_fnc_worldSfxNearby = {{_sounds = _sounds + 1;}};
        private _fnc_refreshDirectPressureMenu = {{_refreshes = _refreshes + 1;}};
        private _entry = {{params ["_medic", "_patient", "_bodyPart", "_classname"]; {bridge()}}};
        private _result = [_medic,_patient,"leftarm","ACME_DirectPressure"] call _entry;
        [_result isEqualTo (_eligible && {{_submitted}}), "queued click was treated as completed/rejected"] call _check;
        [_starts == {int(eligible)}, "eligibility did not guard request"] call _check;
        [_refreshes == {int(eligible)}, "menu refresh changed"] call _check;
        [_sounds == 0, "bridge played before accepted acknowledgement"] call _check;
        [!(_medic getVariable ["ACME_DP_Active",false]), "bridge bypassed owner acknowledgement"] call _check;
    ''')


def test_sound_audit_detects_core_override_broadcasts_and_ignores_decoys():
    assert global_sound_calls('[_medic,"sound"] remoteExec ["say3D",0];')
    assert global_sound_calls('[] remoteExecCall ["ACME_fnc_remoteSay3D",0,false];')
    assert not global_sound_calls('// [] remoteExec ["say3D",0];\nprivate _label = "say3D";')
    assert not global_sound_calls('[] remoteExec ["say3D",_nearby];')


def test_every_release_component_carries_its_own_build_stamp():
    folders = ("airway", "breathing", "cbrn", "circulation", "core", "damage", "disability",
               "evacuation", "gui", "itemtext", "main", "mission", "zeus", "acm_extended")
    for folder in folders:
        source = (ROOT / "addons" / folder / "config.cpp").read_text()
        component = "extended" if folder == "acm_extended" else folder
        assert f'ACME_BUILD_CONFIG("{component}");' in source
        assert 'script_build.hpp"' in source
    header = (ROOT / "addons/main/script_build.hpp").read_text()
    _assert_current_build()
    assert 'acmeNetworkProtocol = 1' in header
