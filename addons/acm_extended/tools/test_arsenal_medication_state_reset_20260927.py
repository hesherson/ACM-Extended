from historical_source import read_source
from pathlib import Path
from source_scan import lex, matching, render, split_args

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return read_source(ROOT / rel, encoding="utf-8-sig", errors="strict")


def test_fresh_kit_reset_clears_virtual_syringes_and_partial_vials():
    s = read("functions/fn_resetPersonalMedicationKit.sqf")
    assert '[_unit, []] call ACME_fnc_narcStoreCommit;' in s
    assert '[_unit, createHashMap] call ACME_fnc_openVialStoreCommit;' in s
    assert 'ACME_narcStoreSerial' in s
    assert 'ACME_SK_SelectedSyringeId' in s
    assert 'ACME_SK_VialHolder' in s


def test_ace_arsenal_load_and_import_are_explicit_reset_boundaries():
    s = read("functions/fn_registerSyringeLifecycleRuntime.sqf")
    # B268: both ACE buttons use CBA's extended setter. Its post-set hook
    # resets exactly the edited unit; button-only/invalid imports do not reset.
    core = (ROOT.parents[1] / "addons/core/functions/fnc_registerEquipmentKitRuntime.sqf").read_text()
    assert 'forEach ["CBA_loadoutSet", "ACME_equipmentKitReplaced"]' in core
    assert '[_unit] call ACM_core_fnc_equipmentKitChanged;' in core
    assert '[_unit] call ACME_fnc_resetPersonalMedicationKit;' in core
    assert '["ace_arsenal_onLoadoutLoad",' not in s
    assert '["ace_arsenal_loadoutImported",' not in s
    assert 'ace_arsenal_displayClosed' not in s


def test_reset_function_is_registered():
    cfg = read("config.cpp")
    assert "class resetPersonalMedicationKit {};" in cfg
    assert "class registerSyringeLifecycleRuntime {};" in cfg


def test_death_keeps_the_partial_vial_ledger_on_the_corpse():
    s = read("functions/fn_registerSyringeLifecycleRuntime.sqf")
    # B279 also preserves tangible prepared syringes. Parse the actual handler
    # so a reset call or selection cleanup in a comment cannot satisfy the gate.
    tokens = lex(s)
    pairs = matching(tokens)
    handlers = []
    for i, token in enumerate(tokens[:-1]):
        if token.kind != "ident" or token.value != "addEventHandler" or tokens[i + 1].value != "[":
            continue
        opening = i + 1
        arguments = split_args(tokens, opening + 1, pairs[opening], pairs)
        if len(arguments) == 2 and len(arguments[0]) == 1 and arguments[0][0].kind == "string" and arguments[0][0].value == "Killed":
            assert arguments[1][0].value == "{" and arguments[1][-1].value == "}"
            handlers.append(arguments[1])
    assert len(handlers) == 1, "Expected one actual Killed handler"
    killed = handlers[0]
    references = {token.value for token in killed if token.kind == "ident"}
    assert not references.intersection({
        "ACME_fnc_narcStoreCommit", "ACME_fnc_openVialStoreCommit",
        "ACME_fnc_resetPersonalMedicationKit", "ACME_fnc_inventoryLedgerCommit",
        "ACME_fnc_inventoryLedgerSettle",
    }), "Death must preserve opened-vial contents and transferable corpse syringes"
    body = render(killed)
    for statement in (
        'uiNamespace setVariable ["ACME_SK_SelectedSyringeId", ""];',
        'uiNamespace setVariable ["ACME_SK_CarouselIdx", -1];',
        'uiNamespace setVariable ["ACME_SK_SelDrawn", -1];',
    ):
        assert render(lex(statement)) in body, ("Killed", statement)
    killed_pairs = matching(killed)
    for i, token in enumerate(killed[:-1]):
        if token.kind == "ident" and token.value == "setVariable" and killed[i + 1].value == "[":
            opening = i + 1
            arguments = split_args(killed, opening + 1, killed_pairs[opening], killed_pairs)
            assert not (arguments and len(arguments[0]) == 1 and arguments[0][0].kind == "string"
                        and arguments[0][0].value in {"ACME_narcStore", "ACME_infusion_openVials"}), "Death must not overwrite corpse stock directly"
