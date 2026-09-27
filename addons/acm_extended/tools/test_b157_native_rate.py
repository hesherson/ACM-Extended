"""Execute native treatment's rate boundary, including stale leases and short-action skips."""
import re

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute


def rate_source():
    source = (ROOT / "addons/core/functions/fnc_treatmentNative.sqf").read_text()
    source = source[source.index("private _animRatio ="):source.index("// Play animation\n")]
    source = re.sub(r"TRACE_3\([^;]*;", "", source)
    source = source.replace("ANIMATION_SPEED_MIN_COEFFICIENT", "0.5")
    source = source.replace("ANIMATION_SPEED_MAX_COEFFICIENT", "2.5")
    return adapt(source)


@pytest.mark.parametrize("lease,expected", [
    ('[1,_patient,"Head","InsertNPA",7]', 1.5),
    ('[1,_patient,"Head","InsertNPA",6]', 0.6),
    ('[1,_patient,"Body","InsertNPA",7]', 0.6),
    ('[1,_patient,"Head","InsertOPA",7]', 0.6),
    ('[1,missionNamespace,"Head","InsertNPA",7]', 0.6),
    ('[]', 0.6),
])
def test_exact_owned_native_action_preserves_shared_rate(lease, expected):
    execute('''
        private _bodyPart="Head";private _classname="InsertNPA";
        private _animDuration=3;private _treatmentTime=5;private _ignoreAnimCoef=false;
        _medic setVariable ["ACME_treatmentPoseEpoch",7];
        CBA_fnc_globalEvent={_events pushBack _this;};
    ''' + f'_medic setVariable ["ACME_nativeTreatmentRate",{lease}];' +
        'call {' + rate_source() + '};' + f'''
        [count _events==1,"native rate missing or duplicated"] call _check;
        [abs (((_events select 0) select 1 select 1)-{expected})<0.00001,"native rate ownership mismatch"] call _check;
        [_treatmentTime==5,"animation changed clinical treatment time"] call _check;
    ''')


def test_near_instant_launcher_keeps_native_animation_skip():
    execute('''
        private _bodyPart="Head";private _classname="InsertNPA";
        private _animDuration=3;private _treatmentTime=0.001;private _ignoreAnimCoef=false;
        _medic setVariable ["ACME_treatmentPoseEpoch",7];
        _medic setVariable ["ACME_nativeTreatmentRate",[1,_patient,"Head","InsertNPA",7]];
        CBA_fnc_globalEvent={_events pushBack _this;};
    ''' + 'call {' + rate_source() + '};' + '''
        [count _events==0,"short action started generic treatment animation"] call _check;
        [_treatmentTime==0.001,"short action timing changed"] call _check;
    ''')
