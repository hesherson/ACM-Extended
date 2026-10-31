/* Owner-authoritative IV mark mutation. No provider may publish a read/modify/write copy of ACME_IV_Marks.
 * Operations:
 *   add        [mark]
 *   connect    [signature, texture]
 *   remove     [signature, holeTexture]
 *   removeSite [bodyPart, nativePart, siteName, gauge, holeTexture]
 * Signature is [bodyPart, view, u, v, site, gauge].
 */
params [
    ["_patient", objNull, [objNull]],
    ["_op", "", [""]],
    ["_data", [], [[]]],
    ["_epoch", -1, [0]]
];
if (isNull _patient) exitWith {false};
if (!local _patient) exitWith {
    [_patient, "ivMarks", [_op, _data, _epoch]] call ACME_fnc_ownerDispatch;
    false
};
if (_epoch >= 0 && {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {false};

private _marks = +(_patient getVariable ["ACME_IV_Marks", []]);
if !(_marks isEqualType []) then {_marks = [];};
private _changed = false;
private _newHubUid = {
    private _serial=(_patient getVariable ["ACME_IV_HubSerial",0])+1;
    private _ce=[_patient] call ACME_fnc_clinicalEpoch;
    private _uid=format ["ivhub:%1:%2",_ce,_serial];
    while {(_marks findIf {(_x param [14,""])==_uid})>=0
        || {((_patient getVariable ["ACME_IV_FinishReceipts",[]]) findIf {(_x param [2,""])==_uid})>=0}} do {
        _serial=_serial+1;_uid=format ["ivhub:%1:%2",_ce,_serial];
    };
    _patient setVariable ["ACME_IV_HubSerial",_serial,true];
    _uid
};
private _matchesSignature = {
    params ["_row", "_sig"];
    if (!(_row isEqualType []) || {count _sig < 6}) exitWith {false};
    _sig params ["_bp", "_view", "_u", "_v", "_site", "_gauge"];
    (toLower (_row param [0, ""])) == toLower _bp
        && {(_row param [1, ""]) == _view}
        && {abs ((_row param [2, -99]) - _u) < 0.0005}
        && {abs ((_row param [3, -99]) - _v) < 0.0005}
        && {toLower (_row param [10, ""]) == toLower _site}
        && {(_row param [7, 0]) == _gauge}
};

switch (toLower _op) do {
    case "finishmigrate": {
        for "_j" from 0 to ((count _marks)-1) do {
            private _row=+(_marks select _j);
            if ((_row param [4,""])=="hub" && {(_row param [14,""])==""}) then {
                _row set [14,call _newHubUid];
                private _oldLine=(_row param [5,""]) find "iv_line_connected" >= 0;
                _row set [15,[_oldLine,_oldLine,_oldLine,_oldLine]];
                if (_oldLine) then {_row set [5,""];};
                _row set [16,[]];_marks set [_j,_row];_changed=true;
            };
        };
    };
    case "add": {
        private _mark = +(_data param [0, []]);
        if (count _mark >= 11) then {
            private _kind = toLower (_mark param [4, ""]);
            if (_kind == "hub") then {
                _mark set [14,call _newHubUid];
                _mark set [15,[false,false,false,false]];
                _mark set [16,[]];
                private _bp = toLower (_mark param [0, ""]);
                private _site = toLower (_mark param [10, ""]);
                private _existing = _marks findIf {
                    toLower (_x param [0, ""]) == _bp
                        && {toLower (_x param [4, ""]) == "hub"}
                        && {toLower (_x param [10, ""]) == _site}
                };
                if (_existing >= 0) then {_marks set [_existing, _mark];} else {_marks pushBack _mark;};
            } else {
                _marks pushBack _mark;
            };
            _changed = true;
        };
    };
    case "connect": {
        _data params [["_sig", [], [[]]], ["_texture", "", [""]]];
        private _i = _marks findIf {
            [_x, _sig] call _matchesSignature
                && {toLower (_x param [4, ""]) == "hub"}
                && {(_x param [5, ""]) == ""}
        };
        if (_i >= 0 && {_texture != ""} && {((_marks select _i) param [14,""])==""}) then {
            private _row = +(_marks select _i);
            _row set [5, _texture];
            _marks set [_i, _row];
            _changed = true;
        };
    };
    case "remove": {
        _data params [["_sig", [], [[]]], ["_hole", "", [""]]];
        private _i = _marks findIf {[_x, _sig] call _matchesSignature && {toLower (_x param [4, ""]) == "hub"}};
        if (_i >= 0) then {
            private _row = +(_marks select _i);
            _row set [15,[false,false,false,false]]; _row set [16,[]]; _row set [4, "removed"];
            _row set [5, _hole];
            _marks set [_i, _row];
            _changed = true;
        };
    };
    case "removesite": {
        _data params [
            ["_bp", "", [""]], ["_nativePart", "", [""]], ["_site", "", [""]],
            ["_gauge", 0, [0]], ["_hole", "", [""]]
        ];
        private _i = _marks findIf {
            toLower (_x param [0, ""]) == toLower _bp
                && {toLower (_x param [4, ""]) == "hub"}
                && {toLower (_x param [10, ""]) == toLower _site}
                && {_gauge <= 0 || {(_x param [7, 0]) == _gauge}}
        };
        if (_i >= 0) then {
            private _row = +(_marks select _i);
            _row set [15,[false,false,false,false]]; _row set [16,[]]; _row set [4, "removed"]; _row set [5, _hole]; _marks set [_i, _row]; _changed = true;
        };
        // Defensive cleanup of legacy stale hubs only when the native circulation state confirms the whole part is empty.
        private _stillHas = false;
        if (_nativePart != "" && {!isNil "ACM_circulation_fnc_hasIV"}) then {
            {if ([_patient, _nativePart, 0, _x] call ACM_circulation_fnc_hasIV) exitWith {_stillHas = true;};} forEach [0,1,2];
        };
        if (!_stillHas && {_nativePart != ""}) then {
            for "_j" from 0 to ((count _marks) - 1) do {
                private _row = +(_marks select _j);
                if (toLower (_row param [0, ""]) == toLower _bp && {toLower (_row param [4, ""]) == "hub"}) then {
                    _row set [15,[false,false,false,false]]; _row set [16,[]]; _row set [4, "removed"]; _row set [5, _hole]; _marks set [_j, _row]; _changed = true;
                };
            };
        };
    };
};

if (_changed) then {
    _patient setVariable ["ACME_IV_Marks", _marks, true];
    _patient setVariable ["ACME_IV_MarkVer", (_patient getVariable ["ACME_IV_MarkVer", 0]) + 1, true];
};
_changed
