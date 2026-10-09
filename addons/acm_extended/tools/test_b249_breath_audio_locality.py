"""B249: local respiration sound workers must retire at every locality edge."""
from pathlib import Path
from source_scan import lex, matching

ROOT = Path(__file__).resolve().parents[1] / "functions"

def test_owner_locality_retires_per_patient_breathing_audio_handle():
    owner = (ROOT / "fn_ownerInit.sqf").read_text(encoding="utf-8-sig")
    start = owner.index('["CAManBase", "Local", {')
    end = owner.index('["CAManBase", "init", {', start)
    block = owner[start:end]
    assert 'private _breathPFH = _unit getVariable ["ACME_bs_pfh", -1];' in block
    assert 'if (_breathPFH >= 0) then {[_breathPFH] call CBA_fnc_removePerFrameHandler;};' in block
    assert '_unit setVariable ["ACME_bs_pfh", -1, false];' in block
    cleanup = block.index('_unit setVariable ["ACME_bs_pfh", -1, false];')
    # Cleanup is unconditional within the Local event, so both outgoing and
    # incoming ownership retire the machine-local handle. Earlier incoming-only
    # carrier cleanup is independent of the later worker-registration branch.
    tokens = lex(block)
    pairs = matching(tokens)
    scopes = [i for i, token in enumerate(tokens) if token.value == '{'
              and token.offset < cleanup < tokens[pairs[i]].offset]
    assert len(scopes) == 1, 'breathing audio cleanup is conditional on a locality direction'
    call = ['[', '_breathPFH', ']', 'call', 'CBA_fnc_removePerFrameHandler']
    values = [token.value for token in tokens]
    calls = [i for i in range(len(tokens)) if values[i:i+len(call)] == call]
    assert len(calls) == 1, 'breathing audio must remove its exact old handle once'
    removal = tokens[calls[0]].offset
    removal_scopes = [i for i, token in enumerate(tokens) if token.value == '{'
                      and token.offset < removal < tokens[pairs[i]].offset]
    assert len(removal_scopes) == 2, 'audio handle removal is conditional on a locality direction'
    assert removal_scopes[0] == scopes[0]
    assert values[removal_scopes[1]-7:removal_scopes[1]] == [
        'if', '(', '_breathPFH', '>=', '0', ')', 'then']
    registration = block.index('[_unit] call ACME_fnc_ownerRegister;')
    incoming_registration = block.rfind('if (_isLocal) then {', 0, registration)
    assert cleanup < incoming_registration < registration

def test_sound_worker_can_start_again_after_locality_transition():
    sound = (ROOT / "fn_breathSoundsStart.sqf").read_text(encoding="utf-8-sig")
    assert 'if (isNull _patient || {!alive _patient} || {!local _patient}) exitWith {};' in sound
    assert 'if ((_patient getVariable ["ACME_bs_pfh", -1]) != -1) exitWith {};' in sound
    assert '_patient setVariable ["ACME_bs_pfh", _pfh, false];' in sound
