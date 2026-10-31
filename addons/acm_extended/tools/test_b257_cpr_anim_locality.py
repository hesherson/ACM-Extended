"""B257: CPR animation callbacks and event handlers retire on locality changes."""
from pathlib import Path
from test_cpr_lifecycle import execute as cpr_execute

ROOT = Path(__file__).resolve().parents[1] / "functions"
CORE = ROOT.parents[1] / "circulation" / "functions"


def test_old_animdone_cannot_restart_cpr_after_away_back_transfer():
    cpr_execute(r"""
        call _start; call _enter;
        private _handler = _medic getVariable ["ACM_circulation_CPR_AnimEH",-1];
        private _oldCallback = _anims select _handler;
        private _movesBefore = count _moves;
        _medic setVariable ["ACME_providerLocalityEpoch",2];
        private _thisEvent = "AnimDone";
        private _thisEventHandler = _handler;
        [_medic,"ACM_CPR"] call _oldCallback;
        [count _moves == _movesBefore, "old AnimDone restarted CPR"] call _check;
        [_handler in _removedAnims, "old AnimDone handler was not retired"] call _check;
        [(_medic getVariable ["ACM_circulation_CPR_AnimEH",0]) == -1,
            "old animation handler id retained"] call _check;
    """)


def test_matching_owner_animdone_still_reasserts_cpr():
    cpr_execute(r"""
        call _start; call _enter;
        private _handler = _medic getVariable ["ACM_circulation_CPR_AnimEH",-1];
        private _callback = _anims select _handler;
        private _before = count _moves;
        private _thisEvent = "AnimDone";
        private _thisEventHandler = _handler;
        [_medic,"ACM_CPR"] call _callback;
        [count _moves == _before + 1 && {(_moves select ((count _moves)-1)) == "ACM_CPR"},
            "matching owner lost CPR animation repeat"] call _check;
        [!(_handler in _removedAnims), "matching owner handler retired early"] call _check;
    """)


def test_away_event_removes_stale_animdone_before_cpr_worker_next_tick():
    owner=(ROOT / "fn_ownerInit.sqf").read_text(encoding="utf-8-sig")
    start=owner.index('["CAManBase", "Local", {')
    end=owner.index('["CAManBase", "init", {',start)
    local=owner[start:end]
    assert '[_unit] call ACM_circulation_fnc_cprRetireAnimLocal;' in local
    native=(ROOT.parents[1] / "circulation" / "functions" / "fnc_cprRetireAnimLocal.sqf").read_text(encoding="utf-8-sig")
    prep=(ROOT.parents[1] / "circulation" / "XEH_PREP.hpp").read_text(encoding="utf-8-sig")
    assert 'PREP(cprRetireAnimLocal);' in prep
    assert '_unit removeEventHandler ["AnimDone", _handler];' in native
    assert 'QGVAR(CPR_AnimLocalityEpoch)' in native
    assert 'QGVAR(CPR_Loop)' in native


def test_cpr_animdone_is_guarded_against_owner_generation_mismatch():
    src=(CORE / "fnc_beginCPR.sqf").read_text(encoding="utf-8-sig")
    assert 'CPR_AnimLocalityEpoch' in src
    assert 'if (!local _medic' in src
    assert '(_medic getVariable ["ACME_providerLocalityEpoch", 0])' in src
    assert '_medic setVariable [QGVAR(CPR_AnimEH), -1, false];' in src
