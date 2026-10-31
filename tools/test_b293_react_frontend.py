"""Require the offline client behavior and committed source/bundle integrity in CI."""
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / 'frontend/medical-ui'
ASSETS = ROOT / 'addons/acm_extended/ui/react'


def test_shared_frontend_session_and_freshness_decisions():
    node = shutil.which('node')
    assert node, 'Node.js 20+ is required for the frontend contract checks'
    result = subprocess.run([node, '--test', '--test-reporter=tap', 'test/bridge.test.mjs'], cwd=FRONT,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert int(re.search(r'# tests (\d+)', result.stdout)[1]) >= 20, result.stdout
    assert '# fail 0' in result.stdout and '# skipped 0' in result.stdout, result.stdout


def test_committed_bundle_and_licenses_match_recorded_sources():
    manifest = json.loads((FRONT / 'bundle-manifest.json').read_text())
    for name, expected in manifest['sources'].items():
        assert hashlib.sha256((FRONT / name).read_bytes()).hexdigest() == expected, name
    assert hashlib.sha256((ASSETS / 'index.html').read_bytes()).hexdigest() == manifest['htmlSha256']
    assert hashlib.sha256((ASSETS / 'THIRD_PARTY_LICENSES.txt').read_bytes()).hexdigest() == manifest['licensesSha256']
    html = (ASSETS / 'index.html').read_text()
    assert '<script src=' not in html and '<link ' not in html
    assert 'ACMEUI' in html and len(html.encode()) < 300_000


def test_native_browser_callbacks_and_fallback_are_registered_without_relaxing_lints():
    header = (ROOT / 'addons/acm_extended/ReactMedical_Dialog.hpp').read_text()
    assert 'type = 106;' in header and 'allowExternalURL = 0;' in header
    assert 'onPageLoaded = "_this call ACME_fnc_reactMedicalPage";' in header
    assert 'onJSDialog = "_this call ACME_fnc_reactMedicalMessage";' in header
    assert 'ACME_fnc_reactMedicalFallback' in header and 'closeDisplay 0' in header
    assert 'event_unknown' not in (ROOT / '.hemtt/lints.toml').read_text()
    setting = (ROOT / 'addons/acm_extended/XEH_preInit.sqf').read_text()
    start = setting.index('["ACME_reactTransfusion"')
    assert 'false, 2, {}]' in setting[start:start + 500]
