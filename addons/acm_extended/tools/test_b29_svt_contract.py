"""Execute current rhythm precedence and native rate gates in SQF-VM.

B67 retired the separate SVT-above-fatal-rate exemption. These tests must not
restore it to satisfy a historical literal. Sources are read unmodified; only
engine objects, native lookup and CBA transport are mocked. No Arma runs here.
"""
from pathlib import Path
import re
import unittest
from historical_source import assignment_expression, read_source
from test_menu_death_lifecycle import adapt, execute

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return read_source(ROOT / name)


def release_program():
    source = read('functions/fn_rhythmTick.sqf')
    names = ('_torsadesOwnsPVT', '_hrReleases', '_physiologyTookOver')
    return '\n'.join('private ' + n + ' = ' + assignment_expression(source, n) + ';' for n in names)


def fatal_condition():
    text = read('overrides/fn_handleUnitVitals.sqf')
    # This gate has no nested colon; fail if its distinctive variable is missing/duplicated.
    matches = re.findall(r'case\s*\((!_activeGracePeriod\s*&&\s*\{[^;]+?\})\)\s*:', text)
    assert len(matches) == 1, 'Native fatal-HR gate must be identifiable exactly once'
    return matches[0]


class SVTSourceContract(unittest.TestCase):
    def test_custom_rhythms_release_at_native_rate_boundaries(self):
        program = release_program()
        execute('''
            private _u = _patient;
            _u setVariable ["ace_medical_inCardiacArrest",false];
            missionNamespace setVariable ["ACME_rhythmACMFatalLowHR",40];
            missionNamespace setVariable ["ACME_rhythmACMFatalHighHR",220];
            {
                private _code = _x;
                private _curRhythm = 0;
                private _torsadesNonPerf = false;
                {
                    _x params ["_hrNow", "_expected"];
        ''' + program + '''
                    [_physiologyTookOver isEqualTo _expected,format["release code=%1 HR=%2",_code,_hrNow]] call _check;
                } forEach [[0,true],[39,true],[40,false],[100,false],[220,false],[220.1,true],[246,true]];
            } forEach [100,101,102,103,104];
        ''')

    def test_native_rhythm_and_arrest_override_stale_custom_state(self):
        src = read('functions/fn_rhythmGet.sqf').replace('alive _unit', '_patientAlive')
        execute('ACME_fnc_rhythmGet = {' + adapt(src) + '};' + '''
            private _rawNative = 0;
            ACME_fnc_rhythmNative = {_rawNative};
            {
                private _code = _x;
                _patient setVariable ["ACME_rhythm_active",_code];
                _patient setVariable ["ACME_rhythm_torsadesNonPerfusing",false];
                {
                    _rawNative = _x;
                    {
                        private _arrest = _x;
                        _patient setVariable ["ace_medical_inCardiacArrest",_arrest];
                        private _result = [_patient] call ACME_fnc_rhythmGet;
                        private _expected = if (_rawNative == 0 && {!_arrest} && {_code in [100,101,102,103,104]}) then {_code} else {_rawNative};
                        [_result == _expected,format["lookup custom=%1 native=%2 arrest=%3",_code,_rawNative,_arrest]] call _check;
                    } forEach [false,true];
                } forEach [-1,0,1,2,3,4,5];
            } forEach [0,99,100,101,102,103,104,105];
            _patient setVariable ["ACME_rhythm_active",102];
            _patient setVariable ["ACME_rhythm_torsadesNonPerfusing",true];
            _patient setVariable ["ace_medical_inCardiacArrest",true];
            {
                _rawNative = _x;
                private _expected = if (_rawNative in [0,3]) then {102} else {_rawNative};
                [([_patient] call ACME_fnc_rhythmGet) == _expected,"torsades morphology/native authority"] call _check;
            } forEach [-1,0,1,2,3,4,5];
            _rawNative = 3; _patientAlive = false;
            [([_patient] call ACME_fnc_rhythmGet) == 3,"dead lookup retained custom overlay"] call _check;
            [([objNull] call ACME_fnc_rhythmGet) == 0,"null lookup"] call _check;
        ''')

    def test_bradycardia_releases_custom_but_mature_torsades_keeps_morphology(self):
        execute('''
            private _u = _patient;
            missionNamespace setVariable ["ACME_rhythmACMFatalLowHR",40];
            missionNamespace setVariable ["ACME_rhythmACMFatalHighHR",220];
            {
                _x params ["_code","_torsadesNonPerf","_curRhythm","_arrest","_hrNow","_expected"];
                _u setVariable ["ace_medical_inCardiacArrest",_arrest];
        ''' + release_program() + '''
                [_physiologyTookOver isEqualTo _expected,"torsades/native precedence"] call _check;
            } forEach [[104,false,0,false,39,true],[102,false,0,false,0,true],
                [102,true,3,true,0,false],[102,true,2,true,0,true],
                [104,false,3,true,0,true],[104,false,4,false,100,true]];
        ''')

    def test_native_watchdog_remains_authoritative_with_grace(self):
        execute('''
            {
                _x params ["_heartRate","_activeGracePeriod","_expected"];
                private _fatal = ''' + fatal_condition() + ''';
                [_fatal isEqualTo _expected,"native fatal rate/grace"] call _check;
            } forEach [[39,false,true],[40,false,false],[220,false,false],[221,false,true],
                [0,true,false],[240,true,false]];
        ''')
        vitals = read('overrides/fn_handleUnitVitals.sqf')
        high_branch = vitals.split('TRACE_2("heartRate Fatal",_unit,_heartRate);',1)[1].split('case (GET_MAP(',1)[0]
        self.assertRegex(high_branch, r'\};\s*\[QGVAR\(handleFatalVitals\), _unit\] call CBA_fnc_localEvent;')
        self.assertIn('if (_heartRate > 220)',high_branch)
        self.assertNotIn('rhythmGet',high_branch)
        self.assertNotIn('call ACME_fnc_arrestLocal',read('functions/fn_rhythmThresholdTick.sqf'))

    def test_only_rhythm_generated_discomfort_loses_hr_feedback(self):
        hr = read('overrides/fn_updateHeartRate.sqf')
        self.assertIn('private _painLevel = GET_PAIN_PERCEIVED(_unit);',hr)
        self.assertIn('_desiredHR + 50 * _painLevel',hr)
        self.assertIn('_desiredHR + 40 * _painLevel',hr)
        self.assertNotIn('getVariable ["ACME_rhythm_painContribution"',hr)
        self.assertIn('getVariable ["ACME_rhythm_painContribution"',read('overrides/fn_handleEffects.sqf'))


if __name__ == '__main__':
    unittest.main()
