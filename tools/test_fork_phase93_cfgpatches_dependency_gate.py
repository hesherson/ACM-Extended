#!/usr/bin/env python3
"""Phase 93: validate fork-internal CfgPatches dependency closure and acyclicity."""
from __future__ import annotations
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ADDONS = ROOT / "addons"
CLINICAL_PATCHES = {"ACM_burns", "ACM_infection", "ACM_ophthalmology"}
CARD_PATCHES = {"DD1380_main", "DD1380_card"}
ADDITIONAL_PATCHES = CLINICAL_PATCHES | CARD_PATCHES


def component_for(addon_dir: Path) -> str:
    if addon_dir.name == "acm_extended":
        return "Extended"
    sc = addon_dir / "script_component.hpp"
    assert sc.is_file(), f"missing script_component.hpp: {addon_dir.relative_to(ROOT)}"
    m = re.search(r"^\s*#define\s+COMPONENT\s+([A-Za-z0-9_]+)\s*$", sc.read_text(errors="replace"), re.M)
    assert m, f"cannot resolve COMPONENT: {sc.relative_to(ROOT)}"
    return m.group(1)


def namespace_for(addon_dir: Path) -> str:
    """Resolve PREFIX from the component's actual script_mod header.

    DD1380 intentionally retains its original namespace and virtual paths; the
    HEMTT source-folder name alone does not identify either of those contracts.
    """
    if addon_dir.name in {"acm_extended", "itemtext"}:
        return "ACM"
    sc = addon_dir / "script_component.hpp"
    text = sc.read_text(encoding="utf-8-sig", errors="strict")
    m = re.search(r'^\s*#include\s+"([^"\r\n]*script_mod\.hpp)"', text, re.M)
    assert m, f"cannot resolve script_mod.hpp: {sc.relative_to(ROOT)}"
    virtual = m.group(1).replace("\\", "/").strip("/")
    header = addon_dir / virtual
    if not header.is_file():
        for candidate in sorted(ADDONS.iterdir()):
            prefix_file = candidate / "$PBOPREFIX$"
            if not prefix_file.is_file():
                continue
            prefix = prefix_file.read_text(encoding="utf-8-sig").strip().replace("\\", "/").strip("/")
            if virtual.casefold().startswith(prefix.casefold() + "/"):
                header = candidate / virtual[len(prefix) + 1:]
                break
    assert header.is_file(), f"missing script_mod.hpp owner for {sc.relative_to(ROOT)}: {virtual}"
    macro = re.search(r"^\s*#define\s+PREFIX\s+([A-Za-z0-9_]+)\s*$", header.read_text(encoding="utf-8-sig"), re.M)
    assert macro, f"cannot resolve PREFIX: {header.relative_to(ROOT)}"
    return macro.group(1)


def patch_name(addon_dir: Path) -> str:
    if addon_dir.name == "acm_extended":
        return "ACM_Extended"
    if addon_dir.name == "itemtext":
        return "ACM_itemtext"
    return f"{namespace_for(addon_dir)}_{component_for(addon_dir)}"


def required_addons(config: Path) -> list[str]:
    text = config.read_text(errors="replace")
    m = re.search(r"requiredAddons\s*\[\]\s*=\s*\{(.*?)\}\s*;", text, re.S)
    assert m, f"missing requiredAddons[] in {config.relative_to(ROOT)}"
    return re.findall(r'"([^"\r\n]+)"', m.group(1))


def main() -> None:
    dirs = sorted(p.parent for p in ADDONS.glob("*/config.cpp"))
    assert len(dirs) == 19, f"expected 19 addon configs, found {len(dirs)}"

    patches: dict[str, tuple[Path, list[str]]] = {}
    for d in dirs:
        name = patch_name(d)
        assert name not in patches, f"duplicate internal CfgPatches owner: {name}"
        req = required_addons(d / "config.cpp")
        assert len(req) == len(set(req)), f"duplicate requiredAddons entry in {name}: {req}"
        assert name not in req, f"self dependency in {name}"
        patches[name] = (d, req)

    assert ADDITIONAL_PATCHES <= patches.keys(), "missing integrated medical/card patch identities"

    # Every ACM_* or DD1380_* dependency must resolve to a patch supplied by this fork. This is the key fork contract:
    # the combined mod may refer to native ACM patch names, but none of those names may require an external ACM PBO.
    unresolved: list[tuple[str, str]] = []
    for owner, (_, req) in patches.items():
        for dep in req:
            if dep.startswith(("ACM_", "DD1380_")) and dep not in patches:
                unresolved.append((owner, dep))
    assert not unresolved, "unresolved internal ACM/DD1380 requiredAddons: " + repr(unresolved)

    # Internal load-order edges must be acyclic.
    graph = {owner: [d for d in req if d in patches] for owner, (_, req) in patches.items()}
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        mark = state.get(node, 0)
        if mark == 2:
            return
        if mark == 1:
            i = stack.index(node)
            raise AssertionError("internal CfgPatches cycle: " + " -> ".join(stack[i:] + [node]))
        state[node] = 1
        stack.append(node)
        for dep in graph[node]:
            visit(dep)
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        visit(node)

    ext_deps = graph["ACM_Extended"]
    assert "ACM_core" in ext_deps and "ACM_gui" in ext_deps, "Extended must load after fork core/gui"
    assert graph["ACM_itemtext"] == ["ACM_Extended"], "late itemtext patches must load after Extended"
    assert all("ACM_Extended" not in deps for n, deps in graph.items()
               if n not in {"ACM_Extended", "ACM_itemtext"} | ADDITIONAL_PATCHES), \
        "native fork addons must not depend back on ACM_Extended"
    assert all("ACM_Extended" in graph[n] for n in CLINICAL_PATCHES), \
        "integrated clinical addons must load after the authoritative Extended runtime"
    assert "DD1380_main" in graph["DD1380_card"], "DD1380 card must load after its own namespace/font owner"

    edge_count = sum(len(v) for v in graph.values())
    print(f"fork phase 93 CfgPatches dependency gate: PASS ({len(patches)} patches, {edge_count} internal edges)")


if __name__ == "__main__":
    main()
