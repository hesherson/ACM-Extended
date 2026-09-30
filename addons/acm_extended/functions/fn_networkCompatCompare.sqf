/* Diagnostic comparison only. A manifest is an installation claim, not authentication. */
params [["_reference", [], [[]]], ["_candidate", [], [[]]]];
private _issues = [];
private _expected = [
    "ACM_main", "ACM_core", "ACM_airway", "ACM_breathing", "ACM_circulation", "ACM_cbrn",
    "ACM_damage", "ACM_disability", "ACM_evacuation", "ACM_gui", "ACM_mission", "ACM_zeus",
    "ACM_Extended", "ACM_itemtext"
];
private _valid = {
    params ["_m"];
    private _protocol = _m param [3, -1];
    count _m == 6 && {(_m select 0) isEqualType 0} && {(_m select 0) == 1}
        && {(_m select 1) isEqualType ""} && {(_m select 1) != ""}
        && {(_m select 2) isEqualType ""} && {(_m select 2) != ""}
        && {_protocol isEqualType 0} && {finite _protocol} && {_protocol >= 1}
        && {_protocol == floor _protocol} && {(_m select 4) isEqualType ""}
        && {(_m select 4) in ["server", "client", "HC"]} && {(_m select 5) isEqualType []}
};
if !([_reference] call _valid) exitWith {["Server manifest missing or unsupported schema"]};
if !([_candidate] call _valid) exitWith {["Peer manifest missing or unsupported schema"]};
if ((_reference select 1) != (_candidate select 1)) then {_issues pushBack format ["Public version differs: server %1 / peer %2", _reference select 1, _candidate select 1];};
if ((_reference select 2) != (_candidate select 2)) then {_issues pushBack format ["Build differs: server %1 / peer %2", _reference select 2, _candidate select 2];};
if ((_reference select 3) != (_candidate select 3)) then {_issues pushBack format ["Protocol differs: server %1 / peer %2", _reference select 3, _candidate select 3];};
private _endpoints = if (_reference isEqualTo _candidate) then {[["Local", _reference]]} else {[["Server", _reference], ["Peer", _candidate]]};
{
    _x params ["_label", "_manifest"];
    private _rows = _manifest select 5;
    if (count _rows != count _expected) then {_issues pushBack format ["%1 component count %2 (expected 14)", _label, count _rows];};
    {
        private _component = _x;
        private _identity = toLower (_component select [4, 100]);
        private _matches = _rows select {_x isEqualType [] && {count _x == 5} && {(_x select 0) isEqualTo _component}};
        if (count _matches != 1) then {
            _issues pushBack format ["%1 component %2 missing/duplicated", _label, _component];
        } else {
            private _row = _matches select 0;
            if !((_row select 1) isEqualTo true) then {
                _issues pushBack format ["%1 PBO %2 missing", _label, _component];
            } else {
                if !((_row select 2) isEqualTo (_manifest select 2)
                    && {(_row select 3) isEqualTo (_manifest select 3)}
                    && {(_row select 4) isEqualTo _identity}) then {
                    _issues pushBack format ["%1 PBO %2 stale/unmarked (%3, protocol %4, identity %5)",
                        _label, _component, _row select 2, _row select 3, _row select 4];
                };
            };
        };
    } forEach _expected;
} forEach _endpoints;
_issues
