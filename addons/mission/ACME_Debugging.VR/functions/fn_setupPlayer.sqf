params ["_unit", "_didJIP"];
private _deadline = diag_tickTime + 45;
waitUntil {
    sleep .1;
    missionNamespace getVariable ["ACMEQA_ready", false] || {!isNil "ACMEQA_startError"}
        || {diag_tickTime >= _deadline}
};
if (!(missionNamespace getVariable ["ACMEQA_ready", false]) || {isNull ACMEQA_control}) exitWith {
    systemChat (missionNamespace getVariable ["ACMEQA_startError", "ACME QA mission setup timed out. See the server RPT."]);
};
private _cases = call ACMEQA_fnc_cases;
if (!(_unit getVariable ["ACMEQA_arrived", false]) && {isNull objectParent _unit}) then {
    _unit setVariable ["ACMEQA_arrived", true, true];
    private _slot = (playableUnits find _unit) max 0;
    _unit setPosATL [1527 + _slot * 2, 3595, 0];
};
_unit setVariable ["ACMEQA_case", 0];
_unit createDiaryRecord ["Diary", ["Run the test", "Open the map for lane locations. At the QA table, prepare the scripted patients. Use ordinary ACE and ACM actions for each checkpoint. Record an observed pass or failure at the table. Restart the mission for a clean rerun."]];
{
    _unit createDiaryRecord ["Diary", +_x];
} forEach _cases;

ACMEQA_control addAction ["QA | Show current checkpoint", {
    params ["", "_caller"];
    ((call ACMEQA_fnc_cases) select (_caller getVariable ["ACMEQA_case", 0])) params ["_name", "_instructions"];
    hintSilent format ["%1\n\n%2", _name, _instructions];
}, nil, 2, true, true, "", "true", 3.5];
ACMEQA_control addAction ["QA | Next checkpoint", {
    params ["", "_caller"];
    private _cases = call ACMEQA_fnc_cases;
    private _index = ((_caller getVariable ["ACMEQA_case", 0]) + 1) % count _cases;
    _caller setVariable ["ACMEQA_case", _index];
    (_cases select _index) params ["_name", "_instructions"];
    hintSilent format ["%1\n\n%2", _name, _instructions];
}, nil, 1.9, true, true, "", "true", 3.5];

{
    _x params ["_label", "_pass"];
    ACMEQA_control addAction [_label, {
        params ["", "_caller", "", "_passed"];
        private _index = _caller getVariable ["ACMEQA_case", 0];
        private _name = (call ACMEQA_fnc_cases) select _index select 0;
        diag_log format ["[ACME QA] OBSERVATION run=%1 case=%2 result=%3 role=%4 time=%5 state=%6",
            ACMEQA_run, _name, ["FAIL", "PASS"] select _passed, vehicleVarName _caller,
            round serverTime, [_caller] call ACMEQA_fnc_snapshot];
        ["ACMEQA_mark", [_caller, _index, _passed]] call CBA_fnc_serverEvent;
        systemChat format ["QA observation entered for %1.", _name];
    }, _pass, 1.8, true, true, "", "true", 3.5];
} forEach [["QA | Record PASS", true], ["QA | Record FAIL", false]];

ACMEQA_control addAction ["QA | Prepare AI patients", {
    params ["", "_caller"];
    ["ACMEQA_prepareAI", [_caller]] call CBA_fnc_serverEvent;
}, nil, 1.6, true, true, "", "ACMEQA_workload == 0", 3.5];
ACMEQA_control addAction ["QA | Start 120-second server capture", {
    params ["", "_caller"];
    ["ACMEQA_capture", [_caller]] call CBA_fnc_serverEvent;
}, nil, 1.5, true, true, "", "true", 3.5];
ACMEQA_control addAction ["QA | Enable Zeus for SkedCo placement", {
    params ["", "_caller"];
    ["ACMEQA_curator", [_caller]] call CBA_fnc_serverEvent;
}, nil, 1.4, true, true, "", "vehicleVarName _this == 'joe' && {isNull getAssignedCuratorLogic _this}", 3.5];

_unit addAction ["QA | Prepare yourself as the player casualty", {
    params ["", "_caller", "_actionId"];
    if ([_caller, "player"] call ACMEQA_fnc_preparePatient) then {_caller removeAction _actionId;};
}, nil, 1.2, true, true, "", "ACMEQA_workload == 0 && {_target isEqualTo _this} && {_this distance [1540,3609,0] < 4}", 1.5];

diag_log format ["[ACME QA] CLIENT_READY run=%1 build=%2 role=%3 jip=%4", ACMEQA_run,
    missionNamespace getVariable ["ACME_buildBatch", "unknown"], vehicleVarName _unit, _didJIP];
systemChat "ACME QA is ready. Check the map briefing and use the QA table near spawn.";
