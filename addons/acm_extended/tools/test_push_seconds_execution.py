"""Execute the actual duration readers and edit sanitization with SQF-VM.

Only native control reads/writes are substituted. Focus and hit testing still need Arma.
"""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

FUNCTIONS = Path(__file__).resolve().parents[1] / "functions"


def read(name):
    return (FUNCTIONS / f"fn_{name}.sqf").read_text()


def execute(code):
    vm = os.environ.get("SQFVM") or shutil.which("sqfvm")
    if not vm:
        pytest.skip("SQF-VM is required for duration execution checks")
    result = subprocess.run(
        [vm, "--automated", "--suppress-welcome", "--no-execute-print", "--no-work-print",
         "--sqf", code], capture_output=True, text=True, timeout=15,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and "[ERR]" not in output, output
    assert "PUSH_SECONDS_OK" in output and "PUSH_SECONDS_FAIL" not in output, output


def test_actual_edit_handler_preserves_digits_and_backspace_without_rewriting():
    handler = read("skBodyActionRender").split('ctrlAddEventHandler ["KeyUp", {', 1)[1].split("}];", 1)[0]
    handler = handler.replace("ctrlText _ctrl", "_testInput")
    handler = handler.replace("_ctrl ctrlSetText _clean", "_testInput = _clean; _writes = _writes + 1")
    execute('''
        private _ok = true;
        {
            _x params ["_testInput", "_expected", "_expectedWrites"];
            private _writes = 0;
            [0] call {''' + handler + '''};
            if (_testInput != _expected || {_writes != _expectedWrites}) then {_ok = false;};
        } forEach [["", "", 0], ["3", "3", 0], ["30", "30", 0], ["120", "120", 0],
            ["300", "300", 0], ["30s", "30", 1], ["abc", "", 1]];
        diag_log (if (_ok) then {"PUSH_SECONDS_OK"} else {"PUSH_SECONDS_FAIL"});
    ''')


@pytest.mark.parametrize("name,start,end,value,valid", [
    ("skConfirmInjection", "private _pushSec = 3;", "if (!_pushDurationValid)", "_pushSec", "_pushDurationValid"),
    ("hardcorePushStart", "private _dur = 3;", "if (!_durValid)", "_dur", "_durValid"),
])
def test_actual_normal_and_hardcore_readers_use_typed_time_and_blank_default(name, start, end, value, valid):
    code = start + read(name).split(start, 1)[1].split(end, 1)[0]
    code = code.replace("_d displayCtrl 84831", "0")
    code = code.replace("isNull _durCtrl", "false")
    code = code.replace('_durCtrl getVariable ["ACME_SK_GhostActive",false]', "false")
    code = code.replace("ctrlText _durCtrl", "_testInput")
    execute('''
        private _ok = true;
        private _route = "vascular";
        {
            _x params ["_testInput", "_expected", "_expectedValid"];
            ''' + code + f'''
            if (!({valid} isEqualTo _expectedValid) || {{_expectedValid && {{{value} != _expected}}}}) then {{_ok = false;}};
        }} forEach [["", 3, true], ["1", 1, true], ["30", 30, true], ["120", 120, true],
            ["300", 300, true], ["0", 0, false], ["301", 301, false]];
        diag_log (if (_ok) then {{"PUSH_SECONDS_OK"}} else {{"PUSH_SECONDS_FAIL"}});
    ''')
