/* [ok, reason]. Validates before any patient state is changed. This checks the
   container contracts used by restore, not every possible clinical range. */
params ["_payload", ["_legacyObjectSession", ""]];
if (isNil "_payload") exitWith {[false, "Missing clinical snapshot"]};
if (_payload isEqualTo []) exitWith {[true, ""]};
if !(_payload isEqualType [] && {count _payload == 2} && {!isNil {_payload select 0}} && {!isNil {_payload select 1}} && {(_payload select 0) isEqualTo 3}
    && {(_payload select 1) isEqualType []}) exitWith {[false, "Unsupported clinical snapshot header"]};
private _fields = createHashMap;
{if (_x param [3, true]) then {_fields set [_x select 0, _x select 1];};} forEach (call ACME_fnc_clinicalFields);
private _seen = createHashMap;
private _budget = [100000];
private _reason = "";
private _required = createHashMapFromArray [
    // B291 clinical anatomy/document containers are checked before any restore mutation.
    ["ACM_burns_AirwayBurned","BOOL"],
    ["ACM_burns_AirwayInflammation","SCALAR"],
    ["ACM_burns_BurnSurface","ARRAY"],
    ["ACM_burns_BurnProtected","ARRAY"],
    ["ACM_burns_BurnBurden","SCALAR"],
    ["ACM_burns_SystemicBurden","SCALAR"],
    ["ACM_burns_PermanentInjury","BOOL"],
    ["ACM_infection_Infection_Stage","SCALAR"],
    ["ACM_infection_Infection_RiskAccumulator","SCALAR"],
    ["ACM_infection_Infection_TreatmentAccumulator","SCALAR"],
    ["ACM_infection_Sepsis_Permanent","BOOL"],
    ["ACME_infectionFeverActive","BOOL"],
    ["ACM_ophthalmology_dustInjuryLight","SCALAR"],
    ["ACM_ophthalmology_dustInjuryHeavy","SCALAR"],
    ["ACM_ophthalmology_eyeInjuries","ARRAY"],
    ["ACM_ophthalmology_eyeInjurySevere","BOOL"],
    ["ACM_ophthalmology_ocularPermanent","BOOL"],
    ["ACM_ophthalmology_eyeShieldItem","STRING"],
    ["ACM_ophthalmology_eyeShieldIndex","SCALAR"],
    ["DD1380_Document","ARRAY"],
    ["DD1380_Priority","HASHMAP"],
    ["DD1380_Checkboxes","HASHMAP"],
    ["DD1380_Text","HASHMAP"],
    ["DD1380_Back_Checkboxes","HASHMAP"],
    ["DD1380_Back_Text","HASHMAP"],
    ["DD1380_Revision","SCALAR"],
    ["ACME_aspiration_State","ARRAY"], ["ACME_ptx_state","ARRAY"], ["ACME_ptx_tensionSeverity","SCALAR"],
    ["ACME_ptx_observationRevision","SCALAR"],
    ["ACME_ptx_nativeSealCount","SCALAR"],
    ["ACME_ptx_nativeSealHoleCount","SCALAR"],
    ["ACME_pendingFlush","ARRAY"],
    ["ACME_do2_dilution","ARRAY"], ["ACME_piCuffs","HASHMAP"],
    ["ACME_circ_State","HASHMAP"], ["ACME_tbi_State","HASHMAP"],
    ["ACME_yFlushJobs","HASHMAP"], ["ACME_lineWarmers","HASHMAP"], ["ACME_YLinePrimed","HASHMAP"], ["ACME_bagMoves","HASHMAP"],
    ["ACME_lineWarmerCustody","HASHMAP"], ["ACME_PiggybackLines","HASHMAP"],
    ["ACME_infusion_BagMedications","ARRAY"], ["ACME_detachedBags","ARRAY"],
    ["ACME_IV_SiteState","ARRAY"], ["ACME_CS_holeData","ARRAY"],
    ["ACME_nrb_medic","OBJECT"], ["ACME_vent_operator","OBJECT"],
    ["ACME_nrb_on","BOOL"], ["ACME_nrb_hasO2","BOOL"],
    ["ACME_tbi_HasTBI","BOOL"], ["ACME_vent_connected","BOOL"],
    ["ACME_vent_onPatient","BOOL"], ["ACME_AAJT_inguinal","BOOL"], ["ACME_AAJT_zone3","BOOL"],
    ["ACME_AAJT_axillaleft","BOOL"], ["ACME_AAJT_axillaright","BOOL"]
];
private _number = {params ["_v"]; !isNil "_v" && {_v isEqualType 0} && {finite _v}};
private _clampReceiptsValid = {
    params ["_receipts"];
    if !(_receipts isEqualType []) exitWith {false};
    private _clients = [];
    private _valid = true;
    {
        if !(_x isEqualType [] && {count _x == 3}
            && {(_x findIf {!([_x] call _number) || {_x < 0} || {_x != floor _x}}) < 0}
            && {(_x select 1) > 0} && {(_x select 2) > 0}) exitWith {_valid = false;};
        private _client = _x select 0;
        if (_client in _clients) exitWith {_valid = false;};
        _clients pushBack _client;
    } forEach _receipts;
    _valid
};
{
    if !(_x isEqualType [] && {count _x == 2} && {!isNil {_x select 0}} && {!isNil {_x select 1}} && {(_x select 0) isEqualType ""}) exitWith {_reason = "Malformed clinical field row";};
    _x params ["_name", "_encoded"];
    private _lower = toLowerANSI _name;
    if (_lower in _seen) exitWith {_reason = "Duplicate clinical field: " + _name;};
    _seen set [_lower, true];
    if !([_encoded, 0, _budget] call ACME_fnc_clinicalEncodedValid) exitWith {_reason = "Invalid encoded value: " + _name;};
    if !(_name in _fields) then {continue;}; // old runtime-only or unknown fields are never applied
    private _v = [_encoded, false, "", 0, _legacyObjectSession] call ACME_fnc_clinicalCodec;
    if (isNil "_v") then {
        if (_name in _required || {(_fields get _name) != ""}) then {_reason = "Missing required encoded value: " + _name;};
    };
    if (_reason != "") exitWith {};
    if (isNil "_v") then {continue;};
    private _want = _required getOrDefault [_name, ""];
    if ((_fields get _name) != "") then {_want = "SCALAR";};
    if ((_lower find "acme_iv_bandonpart_") == 0) then {_want = "BOOL";};
    if (_want != "" && {typeName _v != _want}) exitWith {_reason = "Wrong field type: " + _name;};
    private _bad = false;
    switch (_name) do {
        case "ACM_burns_BurnSurface": {
            _bad = count _v != 6 || {(_v findIf {!([_x] call _number) || {_x < 0 || {_x > 1}}}) >= 0};
        };
        case "ACM_burns_BurnProtected": {
            _bad = count _v != 6 || {!(_v isEqualTypeAll true)};
        };
        case "ACM_burns_BurnBurden";
        case "ACM_burns_SystemicBurden": {
            _bad = !([_v] call _number) || {_v < 0 || {_v > 1}};
        };
        case "ACM_burns_AirwayInflammation": {
            _bad = !([_v] call _number) || {_v < 0 || {_v > 100}};
        };
        case "ACM_infection_Infection_Stage": {
            _bad = !([_v] call _number) || {_v < 0 || {_v > 3}} || {_v != floor _v};
        };
        case "ACM_infection_Infection_RiskAccumulator";
        case "ACM_infection_Infection_TreatmentAccumulator": {
            _bad = !([_v] call _number) || {_v < 0};
        };
        case "ACM_ophthalmology_eyeInjuries": {
            _bad = count _v != 2 || {(_v findIf {!([_x] call _number) || {_x < 0 || {_x > 1}}}) >= 0};
        };
        case "ACM_ophthalmology_dustInjuryLight";
        case "ACM_ophthalmology_dustInjuryHeavy": {
            _bad = !([_v] call _number) || {_v < 0 || {_v > 5}};
        };
        case "ACM_ophthalmology_eyeShieldIndex": {
            _bad = !([_v] call _number) || {!(_v in [-1, 0, 1])};
        };
        case "DD1380_Document": {
            _bad = count _v != 2;
            if (!_bad) then {
                _v params ["_revision", "_document"];
                _bad = !([_revision] call _number) || {_revision < 0} || {_revision != floor _revision}
                    || {!(_document isEqualType [])} || {count _document != 5}
                    || {!(_document isEqualTypeAll createHashMap)};
            };
        };
        case "DD1380_Revision": {
            _bad = !([_v] call _number) || {_v < 0} || {_v != floor _v};
        };
        case "ACME_aspiration_State": {
            _bad = count _v != 5;
            if (!_bad) then {
                _v params ["_epoch","_key","_load","_edema","_serial"];
                _bad = !([_epoch] call _number) || {_epoch < 0} || {_epoch != floor _epoch}
                    || {!(_key isEqualType "")}
                    || {!([_load] call _number)} || {_load < 0 || {_load > 1}}
                    || {!([_edema] call _number)} || {_edema < 0 || {_edema > 1}}
                    || {!([_serial] call _number)} || {_serial < 0} || {_serial != floor _serial};
            };
        };
        case "ACME_ptx_state": {
            _bad = count _v != 9 || {(_v findIf {!([_x] call _number)}) >= 0};
            if (!_bad) then {
                _bad = (_v select 0) != 1
                    // Internal trapped gas can exceed ACM's four-stage display
                    // range so altitude expansion/contraction conserves gas.
                    || {([1,8] findIf {(_v select _x) < 0 || {(_v select _x) > 32}}) >= 0}
                    || {(_v select 7) < 0 || {(_v select 7) > 4}}
                    || {([2,4,5] findIf {(_v select _x) < 0 || {(_v select _x) > 1}}) >= 0}
                    || {(_v select 3) < 0 || {(_v select 3) > 86400}}
                    || {(_v select 6) < 0 || {floor (_v select 6) != (_v select 6)}};
            };
        };
        case "ACME_ptx_tensionSeverity": {
            _bad = !([_v] call _number) || {_v < 0 || {_v > 1}};
        };
        case "ACME_ptx_observationRevision": {
            _bad = !([_v] call _number) || {!(_v in [0, 1])};
        };
        case "ACME_ptx_nativeSealCount";
        case "ACME_ptx_nativeSealHoleCount": {
            _bad = !([_v] call _number) || {_v < -1 || {floor _v != _v}};
        };
        case "ACME_pendingFlush": {
            _bad = (_v findIf {
                if !(_x isEqualType [] && {count _x in [8, 9]}) exitWith {true};
                private _row = _x;
                if !((_row select 0) in ["head","body","leftarm","rightarm","leftleg","rightleg"]
                    && {(_row select 1) isEqualType ""} && {[_row select 2] call _number}
                    && {(_row select 2) > 0} && {(_row select 3) isEqualTo true}
                    && {(_row select 4) isEqualType ""} && {(_row select 5) in [-1,0,1,2]}
                    && {(_row select 6) isEqualType []} && {count (_row select 6) == 3}
                    && {[_row select 7] call _number} && {(_row select 7) > 0}
                    && {(_row param [8,false]) isEqualType true}) exitWith {true};
                private _identity = _row select 6;
                (_identity findIf {!([_x] call _number)}) >= 0
                    || {(_identity select 0) != (_row select 5)}
                    || {(_identity select 1) < 0} || {(_identity select 2) <= 0}
                    || {!([_row select 1,true,true,_row param [8,false]] call ACME_fnc_medicationRouteAllowed)}
            }) >= 0;
        };
        case "ACME_do2_dilution": {
            _bad = count _v != 3 || {(_v findIf {!([_x] call _number)}) >= 0};
            if (!_bad) then {_bad = (_v select 0) < 0 || {(_v select 1) < 0} || {(_v select 0) > (_v select 1)};};
        };
        case "ACME_lineWarmers";
        case "ACME_YLinePrimed": {
            _bad = ((keys _v) findIf {!(_x isEqualType "") || {!((_v get _x) isEqualType true)}}) >= 0;
        };
        case "ACME_lineWarmerCustody": {
            _bad = ((keys _v) findIf {
                private _row = _v get _x;
                !(_x isEqualType "" && {_row isEqualType []} && {count _row == 3}
                    && {(_row select 0) isEqualType ""} && {(_row select 0) != ""}
                    && {(_row select 1) isEqualType objNull} && {[_row select 2] call _number}
                    && {(_row select 2) >= 0})
            }) >= 0;
        };
        case "ACME_PiggybackLines": {
            _bad = ((keys _v) findIf {
                private _row = _v get _x;
                !(_x isEqualType "" && {_row isEqualType []} && {count _row == 3}
                    && {(_row select 0) isEqualType ""} && {(_row select 0) != ""}
                    && {(_row select 1) isEqualType ""} && {(_row select 1) != ""}
                    && {(_row select 0) != (_row select 1)} && {[_row select 2] call _number}
                    && {(_row select 2) >= 0})
            }) >= 0;
        };
        case "ACME_piCuffs": {
            _bad = ((keys _v) findIf {
                private _c = _v get _x;
                !(_x isEqualType "" && {_c isEqualType []} && {count _c in [2,3]} && {count _c == 2 || {(_c select 2) in ["server", "cba"]}}
                    && {[_c select 0] call _number} && {[_c select 1] call _number}
                    && {(_c select 1) >= 0} && {(_c select 1) <= 1})
            }) >= 0;
        };
        case "ACME_infusion_BagMedications": {
            {
                if !(_x isEqualType [] && {count _x >= 26}) exitWith {_bad = true;};
                private _entry = _x;
                if (([0,1,3,11,12,23] findIf {!((_entry select _x) isEqualType "")}) >= 0) exitWith {_bad = true;};
                if !((_entry select 5) isEqualType true) exitWith {_bad = true;};
                if (([2,4,6,7,8,9,10,13,14,15,16,17,18,19,20,21,22,24,25]
                    findIf {!([_entry select _x] call _number)}) >= 0) exitWith {_bad = true;};
                if (count _entry > 26 && {!([_entry select 26] call _number) || {(_entry select 26) < 0}}) exitWith {_bad = true;};
                if (count _entry > 27 && {!([_entry select 27] call _number) || {(_entry select 27) < 0}}) exitWith {_bad = true;};
                if (count _entry > 28 && {isNil {_entry select 28}}) exitWith {_bad = true;};
                if (count _entry > 28 && {!([_entry select 28] call _clampReceiptsValid)}) exitWith {_bad = true;};
                if ((_entry select 7) < 0 || {(_entry select 10) <= 0}
                    || {([13,14,15,24,25] findIf {(_entry select _x) < 0}) >= 0}) exitWith {_bad = true;};
            } forEach _v;
        };
        case "ACME_yFlushJobs": {
            _bad = ((keys _v) findIf {
                private _job = _v get _x;
                !(_job isEqualType [] && {count _job >= 9} && {(_job select 0) isEqualType ""}
                    && {(_job select 1) isEqualType true} && {(_job select 3) isEqualType ""}
                    && {(_job select 7) isEqualType objNull}
                    && {([2,4,5,6,8] findIf {!([_job select _x] call _number)}) < 0}
                    && {count _job == 9 || {count _job in [13,14]
                        && {(_job select 9) isEqualType []} && {count (_job select 9) <= 100}
                        && {((_job select 9) findIf {!([_x] call _number) || {_x <= 0} || {_x > 50}}) < 0}
                        && {(_job select 10) in ["prime", "flush"]}
                        && {([11,12] findIf {!([_job select _x] call _number) || {(_job select _x) < 0}}) < 0}
                        && {[_job,_x] call ACME_fnc_yServiceJobValid}}})
            }) >= 0;
        };
        case "ACME_bagMoves": {
            _bad = ((keys _v) findIf {
                private _move = _v get _x;
                !(_move isEqualType [] && {count _move >= 5} && {(_move select 0) isEqualType ""}
                    && {(_move select 1) isEqualType []} && {count (_move select 1) >= 8}
                    && {(_move select 2) isEqualType objNull} && {[_move select 3] call _number}
                    && {[_move select 4] call _number})
            }) >= 0;
        };
        case "ACME_AAJT_inguinalSide": {
            _bad = !(_v isEqualType "") || {!((toLowerANSI _v) in ["", "leftleg", "rightleg"])};
        };
        case "ACME_circ_State";
        case "ACME_tbi_State": {
            // These state maps are numeric physiology with a small number of
            // Boolean latches. Reject unexpected containers in the resume clocks.
            {if (_x in _v && {!([_v get _x] call _number)}) exitWith {_bad = true;};}
                forEach ["lastTick","acidLastTick","paCO2","icp","map","cpp"];
        };
    };
    if (_bad) exitWith {_reason = "Malformed clinical collection: " + _name;};
} forEach (_payload select 1);
[_reason == "", _reason]
