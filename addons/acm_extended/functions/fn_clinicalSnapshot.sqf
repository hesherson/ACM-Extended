params ["_patient"];
// Live supply escrow is never serialized as durable clinical equipment.
if (count (_patient getVariable ["ACM_ophthalmology_shieldBindings",[]]) > 0) exitWith {[]};
if (!isNil "ACME_fnc_medmashSnapshotReady" && {!([_patient] call ACME_fnc_medmashSnapshotReady)}) exitWith {[]};
private _rows = [];
// Prefer one normalized atomic document. Legacy rows are accepted on restore,
// but never serialized alongside a canonical snapshot that could disagree.
private _cardNormalized = false;
if (!isNil "DD1380_card_fnc_getDocument") then {
    private _document = [_patient, false] call DD1380_card_fnc_getDocument;
    if (_document isEqualType [] && {count _document == 2}) then {
        _rows pushBack ["DD1380_Document", [_document, true] call ACME_fnc_clinicalCodec];
        _cardNormalized = true;
    };
};
{
    _x params ["_name", "_clock", "", ["_persist", true]];
    if (!_persist) then {continue;};
    if (_cardNormalized && {_name in ["DD1380_Document", "DD1380_Priority", "DD1380_Checkboxes", "DD1380_Text", "DD1380_Back_Checkboxes", "DD1380_Back_Text", "DD1380_Revision"]}) then {continue;};
    if (isNil {_patient getVariable _name}) then {continue;};
    private _v = _patient getVariable _name;
    private _data = [_v, true, _clock] call ACME_fnc_clinicalCodec;
    if (_name in ["ACME_tbi_State", "ACME_circ_State"] && {_v isEqualType createHashMap}) then {
        private _pairs = _data select 1;
        {if ((_x select 0) in ["lastTick", "acidLastTick", "lastSpikeTime", "lastOsmoTime", "do2RecoveredAt", "createdAt", "startedAt", "onsetTime", "dbgLogAt"]) then {
            _x set [1, [_v get (_x select 0), true, "cba"] call ACME_fnc_clinicalCodec];
        };} forEach _pairs;
    };
    if (_name == "ACME_infusion_BagMedications") then {
        {private _i = _forEachIndex; private _encoded = ((_data select 1) select _i) select 1;
            {private _n = _x; if (count (_v select _i) > _n) then {_encoded set [_n, [(_v select _i) select _n, true, "cba"] call ACME_fnc_clinicalCodec];};} forEach [16,18];
        } forEach _v;
    };
    if (_name == "ACME_do2_dilution") then {
        (_data select 1) set [2, [_v select 2, true, "cba"] call ACME_fnc_clinicalCodec];
    };
    if (_name == "ACME_piCuffs" && {_v isEqualType createHashMap}) then {
        {private _entry = (_x select 1) select 1;
            private _raw = _v get (_x select 0);
            private _at = _raw select 0;
            if ((_raw param [2, "cba"]) == "server") then {
                _at = CBA_missionTime - ((serverTime - _at) max 0);
                _entry set [2, ["cba", true] call ACME_fnc_clinicalCodec];
            };
            _entry set [0, [_at, true, "cba"] call ACME_fnc_clinicalCodec];
        } forEach (_data select 1);
    };
    if (_name in ["ACME_yFlushJobs", "ACME_bagMoves"] && {_v isEqualType createHashMap}) then {
        {private _encoded = (_x select 1) select 1; private _i = if (_name == "ACME_yFlushJobs") then {6} else {3};
            private _raw = _v get (_x select 0);
            private _at = _raw select _i;
            if (_name == "ACME_yFlushJobs" && {count _raw >= 13}) then {_at = CBA_missionTime - ((serverTime - _at) max 0);};
            _encoded set [_i, [_at, true, "cba"] call ACME_fnc_clinicalCodec];
        } forEach (_data select 1);
    };
    _rows pushBack [_name, _data];
} forEach (call ACME_fnc_clinicalFields);
[3, _rows]
