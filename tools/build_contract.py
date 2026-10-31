"""Independent, explicit current-build expectations; never infer expected identity from production."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]

def assert_current_build(root=ROOT):
    root = Path(root)
    expected = json.loads((root / "tools/current_build_contract.json").read_text())
    assert set(expected) == {"version", "batch", "network_revision", "network_protocol", "debug_revision", "status", "baseline"}
    assert re.fullmatch(r"[0-9]+(?:\.[0-9]+){3}", expected["version"])
    assert re.fullmatch(r"B[1-9][0-9]*", expected["batch"])
    assert expected["status"] in {"candidate", "stable"}
    assert expected["network_revision"] == "NA8-" + expected["batch"] + "-" + expected["version"] + "-" + expected["status"]
    assert type(expected["network_protocol"]) is int and expected["network_protocol"] > 0
    assert expected["debug_revision"] == ""
    assert re.fullmatch(r"[0-9a-f]{40}", expected["baseline"])
    startup = (root / "addons/acm_extended/functions/fn_initForkStartupRuntime.sqf").read_text()
    config = (root / "addons/acm_extended/config.cpp").read_text()
    header = (root / "addons/main/script_build.hpp").read_text()
    version_header = (root / "addons/main/script_version.hpp").read_text()
    # Strip source comments, so a commented-out identity never passes.
    def code(text):
        return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", text, flags=re.S))
    startup, config, header, version_header = map(code, (startup, config, header, version_header))
    for field, key in (("ACME_infusion_version", "version"), ("ACME_buildBatch", "batch"),
                       ("ACME_networkAuditRevision", "network_revision"), ("ACME_debugRevision", "debug_revision")):
        assert re.findall(r"\b" + field + r'\s*=\s*"([^"\n]*)"', startup) == [expected[key]], (field, expected[key])
    assert 'configFile >> "CfgPatches" >> "ACM_Extended" >> "version"' in startup
    assert re.findall(r'\bversion\s*=\s*"([^"\n]+)"', config) == [expected["version"]]
    assert re.findall(r'\bacmeBuildBatch\s*=\s*"([^"\n]+)"', header) == [expected["batch"]]
    assert re.findall(r'\bacmeNetworkProtocol\s*=\s*([0-9]+)', header) == [str(expected["network_protocol"])]
    version = ".".join(re.search(r"^#define " + key + r" ([0-9]+)$", version_header, re.M)[1] for key in ("MAJOR", "MINOR", "PATCH", "BUILD"))
    assert version == expected["version"]
    debug = code((root / "addons/acm_extended/functions/fn_debugMenuClinical.sqf").read_text())
    assert 'configFile >> "CfgPatches" >> "ACM_Extended" >> "version"' in debug
    assert "ACME_buildBatch" in debug and "ACME DEBUG v%2" in debug
    return expected

if __name__ == "__main__":
    print(json.dumps(assert_current_build(), indent=2))
