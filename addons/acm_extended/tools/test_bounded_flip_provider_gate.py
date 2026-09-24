"""AW: physical chest Flip cannot fail open before provider medic4 owns the interaction."""
from pathlib import Path
import pytest
from source_scan import lex

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'functions/fn_chestSealFlip.sqf'

def contract(text):
    assert 'if (!_started) exitWith {' in text
    pre=text.split('if (!_started) exitWith {',1)[1].split('private _args =',1)[0]
    assert 'ACME_fnc_chestSealRoll' not in pre
    assert 'ACME_CS_FlipPendingToken",""' in pre
    assert 'ACME_CS_FlipLockedUntil",0' in pre
    assert 'ACME_CS_FlipTarget",""' in pre
    assert 'ACME_fnc_chestSealProviderHoldStart' in pre
    assert 'ACME_DP_PauseTreatmentClass' in pre
    assert 'ACME_DP_Paused",false' in pre
    # Button/prep function has no physical roll dispatch at all.
    executable='\n'.join(line.split('//',1)[0] for line in text.splitlines())
    assert 'call ACME_fnc_chestSealRoll' not in executable

def test_failed_provider_theatre_aborts_before_patient_roll():
    contract(P.read_text())

@pytest.mark.parametrize('injected',[
    '[_patient,_newSide,false,_provider] call ACME_fnc_chestSealRoll;',
    'uiNamespace setVariable ["ACME_CS_FlipLockedUntil",diag_tickTime + _rollTime]; [_patient,_newSide,false,_provider] call ACME_fnc_chestSealRoll;',
])
def test_contract_rejects_fail_open_roll_mutation(injected):
    text=P.read_text()
    marker='if (!_started) exitWith {'
    mutated=text.replace(marker, marker+'\n    '+injected,1)
    with pytest.raises(AssertionError):
        contract(mutated)
