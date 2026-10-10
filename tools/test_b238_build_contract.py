"""Current-build expectations fail on drift, duplicates, and commented-out declarations."""
import json
from pathlib import Path
import shutil
import pytest
from build_contract import ROOT, assert_current_build

FILES = ['tools/current_build_contract.json', 'addons/acm_extended/config.cpp',
         'addons/acm_extended/functions/fn_initForkStartupRuntime.sqf',
         'addons/acm_extended/functions/fn_debugMenuClinical.sqf',
         'addons/main/script_build.hpp','addons/main/script_version.hpp']

def fixture(tmp_path):
    for rel in FILES:
        dest=tmp_path/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dest)
    return tmp_path

def test_current_source_matches_explicit_contract():
    assert_current_build()

@pytest.mark.parametrize('path,old,new',[
    (FILES[1],'version = "1.2.4.1"','version = "1.2.4.0"'),
    (FILES[2],'ACME_buildBatch = "B238"','ACME_buildBatch = "B237"'),
    (FILES[2],'NA8-B238-1.2.4.1-candidate','NA8-B238-1.2.4.1-stable'),
    (FILES[2],'ACME_debugRevision = ""','ACME_debugRevision = "RC"'),
    (FILES[2],'ACME_infusion_version = "1.2.4.1"','ACME_infusion_version = "1.2.4.0"'),
    (FILES[4],'acmeBuildBatch = "B238"','acmeBuildBatch = "B237"'),
    (FILES[4],'acmeNetworkProtocol = 1','acmeNetworkProtocol = 2'),
    (FILES[5],'#define BUILD 1','#define BUILD 0'),
    (FILES[3],'ACME_buildBatch','obsolete_build'),
    (FILES[2],'ACME_buildBatch = "B238";','// ACME_buildBatch = "B238";'),
    (FILES[2],'ACME_buildBatch = "B238";','ACME_buildBatch = "B238"; ACME_buildBatch = "B237";'),
])
def test_identity_drift_is_rejected(tmp_path,path,old,new):
    # Keep the original mutation IDs as provenance, while targeting the explicit
    # current contract rather than assuming every future source still says B238.
    expected = json.loads((ROOT / "tools/current_build_contract.json").read_text())
    old = old.replace("B238", expected["batch"])
    new = new.replace("B238", expected["batch"])
    root=fixture(tmp_path);p=root/path;text=p.read_text();assert old in text;p.write_text(text.replace(old,new))
    with pytest.raises(AssertionError):assert_current_build(root)

@pytest.mark.parametrize('key,value',[('batch','retired'),('version','nonsense'),('network_protocol',True),('network_revision','wrong'),('debug_revision','RC'),('status','approved')])
def test_invalid_expected_contract_is_rejected(tmp_path,key,value):
    root=fixture(tmp_path);p=root/FILES[0];data=json.loads(p.read_text());data[key]=value;p.write_text(json.dumps(data))
    with pytest.raises(AssertionError):assert_current_build(root)
