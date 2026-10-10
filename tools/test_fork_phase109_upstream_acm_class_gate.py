"""B239: execute the reviewed current contract; original script assertions retained where applicable."""

def test_current_phase109_upstream_acm_class_gate():
    #!/usr/bin/env python3
    """Phase 109: preserve directly declared upstream ACM_* config classes."""
    from pathlib import Path
    import re

    ROOT = Path(__file__).resolve().parents[1]
    ADDONS = ROOT / "addons"
    MANIFEST = ROOT / "tools/upstream_acm_class_manifest.txt"


    def strip_comments(text: str) -> str:
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        return re.sub(r"//[^\n]*", "", text)

    expected = {
        line.strip().casefold()
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert len(expected) == 163, f"unexpected upstream ACM class manifest size: {len(expected)}"

    actual = set()
    for source in ADDONS.rglob("*"):
        if not source.is_file() or source.suffix.lower() not in {".hpp", ".cpp", ".h"}:
            continue
        text = strip_comments(source.read_text(encoding="utf-8", errors="ignore"))
        actual.update(match.group(1).casefold() for match in re.finditer(r"\bclass\s+(ACM_[A-Za-z0-9_]+)\b", text, re.I))

    missing = sorted(expected - actual)
    retired = {"acm_action_syringe", "acm_action_syringe_10_empty", "acm_action_syringe_1_empty", "acm_action_syringe_3_empty", "acm_action_syringe_5_empty"}
    assert set(missing) == retired, "unreviewed class removal or retired Syringes menu restored: " + repr(missing)
    assert len(actual) >= len(expected) - len(retired)
    config=strip_comments((ADDONS/'acm_extended/config.cpp').read_text())
    assert 'class ACME_SyringeKit {' in config and 'class ACME_DrawnSyringes {' in config
    assert 'class ACME_SyringeKit_Draw {' in config

    print(f"PASS phase109: {len(expected)} upstream ACM classes tracked (five intentionally retired menu classes); fork directly declares {len(actual)} ACM_* classes")


if __name__ == "__main__":
    test_current_phase109_upstream_acm_class_gate()
