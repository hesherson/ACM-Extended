"""Execute the manual-lower completion; native objects/transport/animation remain stand-ins."""
import os
from pathlib import Path
import pytest
import test_bounded_head_completion as h
from test_menu_death_lifecycle import execute

@pytest.fixture(autouse=True)
def production_override(monkeypatch):
    # Run exactly these assertions against an immutable old production function as a negative control.
    old = os.environ.get('ACME_TEST_LOWER_SOURCE')
    if old:
        original = h.source
        monkeypatch.setattr(h, 'source', lambda name: Path(old).read_text() if name == 'headElevateStop' else original(name))

@pytest.mark.parametrize('change', [
    '_patient setVariable ["ACME_headElev_startEpoch",100];',
    '_patient setVariable ["ACME_headElev_poseToken","new-flat-placement"];',
    '_patient setVariable ["ACME_patientAnimLock",["new-lease","chest",2,_medic,1100]];',
])
def test_retired_manual_lower_cannot_restore_or_delete_new_workspace(change):
    execute(h.setup()+h.begin('stop')+change+'''
        _patient setVariable ["ACME_headElev_propObj",uiNamespace];
        [_pending] call _deliver;
        [count _restores==0 && {count _collisions==0} && {count _moves==0},"retired manual lower changed presentation"] call _check;
        [count _deleted==0 && {count _detached==0},"retired manual lower deleted new support"] call _check;
        [(_patient getVariable ["ACME_headElev_propObj",objNull]) isEqualTo uiNamespace,"retired lower erased new prop reference"] call _check;
    ''')

def test_manual_lower_completion_is_single_use():
    execute(h.setup()+h.begin('stop')+'''
        [_pending] call _deliver;
        [count _restores==2 && {count _moves==1},"current lower failed its first completion"] call _check;
        _collisions=[]; _moves=[]; _restores=[];
        _patient setVariable ["ACME_headElev_propObj",uiNamespace];
        [_pending] call _deliver;
        [count _collisions==0 && {count _moves==0} && {count _restores==0},"duplicate manual lower restored twice"] call _check;
        [count _deleted==0 && {count _detached==0},"duplicate lower deleted new prop"] call _check;
    ''')
