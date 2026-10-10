"""B240: reviewed current contract, with individually reportable execution."""

def test_current_phase142_getup_acre_babel_gate():
    from pathlib import Path
    import re

    ROOT = Path(__file__).resolve().parents[1]


    def read(rel: str) -> str:
        p = ROOT / rel
        assert p.is_file(), f"missing {rel}"
        return p.read_text(encoding="utf-8", errors="replace")


    def code_only(text: str) -> str:
        # Sufficient for regression checks: remove // comments and /* ... */ blocks.
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        text = re.sub(r"//.*", "", text)
        return text


    moves = read("addons/core/CfgMoves.hpp")
    getup = read("addons/core/functions/fnc_getUp.sqf")
    getup_code = code_only(getup)
    clear = read("addons/acm_extended/functions/fn_clearAllAilments.sqf")
    master = read("addons/acm_extended/functions/fn_obtundedMasterChanged.sqf")
    post = read("addons/core/XEH_postInit.sqf")

    # Get Up root cause must remain documented in the actual move graph: this is an isolated looping state.
    assert "class ACM_LyingState" in moves
    lying = moves.split("class ACM_LyingState", 1)[1][:900]
    assert "ConnectTo[] = {};" in lying
    assert "InterpolateTo[] = {};" in lying

    # Provider/self requests are routed to the patient owner.
    assert 'if (!local _patient) exitWith' in getup
    assert '"ACM_core_getUpRequest"' in getup
    assert '[QGVAR(getUpRequest)' in post

    # Priority 2 is intentional here: priority 1 cannot exit ACM_LyingState.
    assert '[_patient, _roll, 2] call ACME_fnc_doAnim;' in getup
    assert '[_p, _roll, 2] call ACME_fnc_doAnim;' in getup
    assert '[_p, "AmovPpneMstpSnonWnonDnon", 2] call ACME_fnc_doAnim;' in getup
    assert "ACME_fnc_animQueue" not in getup_code, "Get Up must not route through the priority-1 animation queue"

    # Release the stale engine/ACME animation controller before consuming the action.
    for token in [
        'setVariable ["ACME_animQ", [], false]',
        'setVariable ["ACME_animQEnd", 0, false]',
        'setVariable ["ACME_animQActive", false, false]',
        '"ACME_dah_gen"',
        'setUnitPos "AUTO"',
        'setUnconscious false',
        'setVariable ["ACM_core_Lying_State", false, true]',
    ]:
        assert token in getup, f"missing Get Up release guard: {token}"

    # Two independent engine-state backstops are required so a swallowed playMove does not consume Get Up silently.
    assert '], 0.15] call CBA_fnc_waitAndExecute;' in getup
    assert '], 0.65] call CBA_fnc_waitAndExecute;' in getup
    assert 'ace_medical_engine_uncon_anim' in getup

    # Obtundation must not affect Get Up when its master is disabled.
    assert 'missionNamespace getVariable ["ACME_sys_obtunded", false]' in getup
    assert '&& {_patient getVariable ["ACME_obtunded", false]}' in getup

    # Full-heal/Zeus cleanup must be capable of escaping the same isolated state.
    assert '[_patient, "UnconsciousOutProne", 2] call ACME_fnc_doAnim;' in clear

    # Reviewed removal commit 7407794e: obtundation no longer changes any ACRE Babel registry or language.
    from current_source_contracts import _has
    from source_scan import lex
    for name in ('acreBabbleInit','acreBabbleSet','acreBabbleTick','initAcreBabbleRuntime'):
        assert not (ROOT/'addons/acm_extended/functions'/f'fn_{name}.sqf').exists()
        assert not _has(read('addons/acm_extended/config.cpp'), f'class {name} {{}};')
    for path in (ROOT/'addons/acm_extended/functions').glob('*.sqf'):
        tokens=lex(path.read_text())
        babel_calls=[t.value for t in tokens if t.kind=='ident' and
                     (t.value.lower().startswith('acre_api_fnc_babel') or t.value.lower().startswith('acme_fnc_acrebabble'))]
        assert not babel_calls, (path.name, babel_calls)
    voice=read('addons/acm_extended/functions/fn_obtundedVoice.sqf')
    assert 'private _effectiveMute = _mute' in voice
    assert 'ACME_sys_obtunded' in voice and 'ACME_obtunded' in voice
    assert 'TFAR_fnc_setForbiddenToSpeak' in voice
    print('PASS: owner-local Get Up repair and no return of retired synthetic Babel')


if __name__ == "__main__":
    test_current_phase142_getup_acre_babel_gate()
