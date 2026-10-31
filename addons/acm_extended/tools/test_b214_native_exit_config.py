"""Source-structure protection for native animation inheritance.

Arma's concrete ``class Name { ... };`` form clears a previously inherited
base. A native state can therefore lose connectFrom and other required fields
even though the addon config compiles successfully. These checks preserve the
external state and detect the B213 mutation; they do not execute Arma's config
merge, resolve the vanilla move graph, or render animation transitions.
"""
from dataclasses import dataclass
from pathlib import Path

import pytest

from source_scan import lex, matching


ROOT = Path(__file__).resolve().parents[1]
END = "AinvPknlMstpSnonWnonDnon_medicEnd"


@dataclass(frozen=True)
class Declaration:
    name: str
    base: str | None
    body: int | None
    end: int


def declarations(tokens, pairs, lo, hi):
    """Direct child declarations only; use the repository's shared lexer."""
    i = lo
    while i < hi:
        token = tokens[i]
        if token.kind == "ident" and token.value.lower() == "class":
            name = tokens[i + 1].value
            j = i + 2
            base = None
            if tokens[j].value == ":":
                base = tokens[j + 1].value
                j += 2
            if tokens[j].value == ";":
                yield Declaration(name, base, None, j)
                i = j + 1
                continue
            assert tokens[j].value == "{" and j in pairs, f"Malformed class {name}"
            end = pairs[j]
            yield Declaration(name, base, j, end)
            i = end + 1
        elif token.kind == "symbol" and token.value in {"{", "[", "("} and i in pairs:
            i = pairs[i] + 1
        else:
            i += 1


def move_states(source):
    tokens = lex(source)
    pairs = matching(tokens)
    roots = declarations(tokens, pairs, 0, len(tokens))
    moves = next(node for node in roots if node.name.lower() == "cfgmovesmalesdr")
    assert moves.body is not None
    sections = declarations(tokens, pairs, moves.body + 1, moves.end)
    states = next(node for node in sections if node.name.lower() == "states")
    assert states.body is not None
    return list(declarations(tokens, pairs, states.body + 1, states.end))


def assert_state_inheritance_preserved(source):
    concrete = [node for node in move_states(source) if node.body is not None]
    assert concrete, "No concrete provider states examined"
    missing = [node.name for node in concrete if node.base is None]
    assert not missing, f"Concrete move states remove inherited properties: {missing}"
    return concrete


def test_every_concrete_provider_state_retains_an_explicit_base():
    assert_state_inheritance_preserved((ROOT / "config.cpp").read_text(encoding="utf-8"))


def test_native_end_is_referenced_but_not_redefined():
    source = (ROOT / "config.cpp").read_text(encoding="utf-8")
    assert END.lower() not in {node.name.lower() for node in move_states(source) if node.body is not None}
    # The custom hold/workspace can link to the native move without reopening it.
    assert END in {token.value for token in lex(source) if token.kind == "string"}


def test_b213_array_append_mutation_is_rejected():
    source = (ROOT / "config.cpp").read_text(encoding="utf-8")
    bad_block = f'''
        class {END} {{
            connectTo[] += {{"AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown", 0.08}};
            interpolateTo[] += {{"AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown", 0.08}};
        }};
    '''
    tokens = lex(source)
    pairs = matching(tokens)
    moves = next(node for node in declarations(tokens, pairs, 0, len(tokens))
                 if node.name.lower() == "cfgmovesmalesdr")
    states = next(node for node in declarations(tokens, pairs, moves.body + 1, moves.end)
                  if node.name.lower() == "states")
    insertion = tokens[states.body].offset + 1
    mutated = source[:insertion] + bad_block + source[insertion:]
    with pytest.raises(AssertionError, match=END):
        assert_state_inheritance_preserved(mutated)


@pytest.mark.parametrize("body", ["", "connectFrom[] = {};", "speed = -2;"])
def test_filling_one_missing_field_cannot_hide_an_inheritance_reset(body):
    source = f"class CfgMovesMaleSdr {{ class States {{ class Broken {{ {body} }}; }}; }};"
    with pytest.raises(AssertionError, match="Broken"):
        assert_state_inheritance_preserved(source)


def test_source_walker_distinguishes_forward_declarations_strings_and_other_scopes():
    source = r'''
        class Outside { class Bad {}; };
        class CfgMovesMaleSdr: CfgMovesBasic {
            class States {
                class NativeBase;
                // class CommentedOut {};
                class Good: NativeBase {
                    note = "class StringLiteral {}";
                    connectTo[] = {"NativeBase", 0.1};
                    class NestedMetadata {};
                };
            };
            class OtherScope { class Bad {}; };
        };
    '''
    states = assert_state_inheritance_preserved(source)
    assert [(node.name, node.base) for node in states] == [("Good", "NativeBase")]


@pytest.mark.parametrize("name,variable", [
    ("directPressurePoseExit", "_anim"),
    ("headElevMedicSeq", "_end"),
])
def test_both_exit_controllers_still_select_the_requested_literal_native_motion(name, variable):
    tokens = lex((ROOT / "functions" / f"fn_{name}.sqf").read_text(encoding="utf-8"))
    assignments = [tokens[i + 2] for i, token in enumerate(tokens[:-2])
                   if token.kind == "ident" and token.value == variable
                   and tokens[i + 1].value == "="]
    assert any(token.kind == "string" and token.value == END for token in assignments)
