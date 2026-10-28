/* A stamped command belongs to one physical valve. Its per-client receipt is
 * carried with the medication rows so another medic or owner cannot erase it.
 * Historical five-argument callers retain the same physical-carrier gate. */
params ["_patient", "_ids", "_epoch", "_position", "_dropSet", ["_request", []]];
private _tracked = count _this > 5;
private _number = {params ["_value"]; !isNil "_value" && {_value isEqualType 0} && {finite _value}};
private _stampValid = {
    params ["_value"];
    !isNil "_value" && {_value isEqualType []} && {count _value == 3}
        && {(_value findIf {!([_x] call _number) || {_x < 0} || {_x != floor _x}}) < 0}
        && {(_value select 1) > 0} && {(_value select 2) > 0}
};
private _medic = objNull;
private _stamp = [];
private _capturedBagId = "";
private _requestValid = !_tracked;
if (_tracked && {_request isEqualType []} && {count _request == 3}
    && {(_request findIf {isNil "_x"}) < 0}) then {
    _medic = _request select 0;
    _stamp = _request select 1;
    _capturedBagId = _request select 2;
    _requestValid = _medic isEqualType objNull && {!isNull _medic}
        && {[_stamp] call _stampValid}
        && {_capturedBagId isEqualType ""} && {_capturedBagId != ""};
};
private _reply = {
    params ["_accepted"];
    if (_tracked && {_medic isEqualType objNull} && {!isNull _medic} && {[_stamp] call _stampValid}) then {
        ["ACME_clampResult", [_patient, _medic, +_stamp, _accepted], _medic] call CBA_fnc_targetEvent;
    };
    _accepted
};
if (!_requestValid || {!(_patient isEqualType objNull)} || {isNull _patient}) exitWith {[false] call _reply};
if (!local _patient) exitWith {[_patient, "infusionClamp", _this] call ACME_fnc_ownerDispatch;};
// The clamp is retained equipment and remains adjustable after patient death.
if (!([_epoch] call _number) || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {_patient getVariable ["ACME_persistenceFrozen", false]}
    || {_tracked && {!alive _medic || {_medic getVariable ["ACME_persistenceFrozen", false]}}}) exitWith {[false] call _reply};
if (!([_position] call _number) || {_position < 0} || {_position > 1}
    || {!([_dropSet] call _number)}) exitWith {[false] call _reply};
if !(_ids isEqualType [] && {!(_ids isEqualTo [])}
    && {(_ids findIf {!(_x isEqualType "") || {_x == ""}}) < 0}) exitWith {[false] call _reply};

private _entries = _patient getVariable ["ACME_infusion_BagMedications", []];
if !(_entries isEqualType []) exitWith {[false] call _reply};
private _bagId = "";
private _validIds = true;
{
    private _id = _x;
    private _matches = _entries select {_x isEqualType [] && {count _x >= 24} && {(_x select 0) isEqualTo _id}};
    if (count _matches != 1) exitWith {_validIds = false;};
    private _idBag = (_matches select 0) select 23;
    if !(_idBag isEqualType "" && {_idBag != ""}) exitWith {_validIds = false;};
    if (_bagId == "") then {_bagId = _idBag;};
    if (_idBag != _bagId) exitWith {_validIds = false;};
} forEach _ids;
if (!_validIds || {_bagId == ""} || {_tracked && {_capturedBagId != _bagId}}) exitWith {[false] call _reply};
private _map = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
if !(_map isEqualType createHashMap) exitWith {[false] call _reply};
private _physicalMatches = 0;
{
    private _bags = _map get _x;
    if (_bags isEqualType []) then {
        {if (_x isEqualType [] && {(_x param [8, ""]) isEqualTo _bagId}) then {_physicalMatches = _physicalMatches + 1;};} forEach _bags;
    };
} forEach keys _map;
if (_physicalMatches != 1) exitWith {[false] call _reply};

// Merge every additive's receipts. A legacy row or a later additive cannot
// discard another component's newer receipt for an interleaved clinician.
private _ledger = [];
private _validLedger = true;
private _bagRows = _entries select {_x isEqualType [] && {count _x >= 24} && {(_x select 23) isEqualTo _bagId}};
{
    if (_tracked && {count _x < 26}) exitWith {_validLedger = false;};
    if (count _x > 28 && {isNil {_x select 28}}) exitWith {_validLedger = false;};
    private _receipts = _x param [28, []];
    if !(_receipts isEqualType []) exitWith {_validLedger = false;};
    private _clients = [];
    {
        if !([_x] call _stampValid) exitWith {_validLedger = false;};
        private _client = _x select 0;
        if (_client in _clients) exitWith {_validLedger = false;};
        _clients pushBack _client;
        private _i = _ledger findIf {(_x select 0) == _client};
        if (_i < 0) then {_ledger pushBack +_x;} else {
            private _old = _ledger select _i;
            if ((_x select 1) > (_old select 1)
                || {(_x select 1) == (_old select 1) && {(_x select 2) > (_old select 2)}}) then {_ledger set [_i, +_x];};
        };
    } forEach _receipts;
    if (!_validLedger) exitWith {};
} forEach _bagRows;
if (!_validLedger) exitWith {[false] call _reply};
private _receiptState = 1;
if (_tracked) then {
    private _client = _stamp select 0;
    private _i = _ledger findIf {(_x select 0) == _client};
    if (_i >= 0) then {
        private _old = _ledger select _i;
        if (_stamp isEqualTo _old) then {_receiptState = 0;} else {
            if ((_stamp select 1) < (_old select 1)
                || {(_stamp select 1) == (_old select 1) && {(_stamp select 2) < (_old select 2)}}) then {_receiptState = -1;};
        };
        if (_receiptState == 1) then {_ledger set [_i, +_stamp];};
    } else {_ledger pushBack +_stamp;};
};
// Duplicate delivery acknowledges its original result even when its retried
// payload differs. Neither duplicate nor older delivery mutates any source row.
if (_receiptState < 0) exitWith {[false] call _reply};
if (_receiptState == 0) exitWith {[true] call _reply};
private _clients = _ledger apply {_x select 0};
_clients sort true;
_ledger = _clients apply {private _client = _x; +(_ledger select (_ledger findIf {(_x select 0) == _client}))};

// Mutate a detached copy only after every identity and receipt is validated.
private _updated = _entries apply {if (_x isEqualType []) then {+_x} else {_x}};
{
    if (_x isEqualType [] && {(_x param [23, ""]) isEqualTo _bagId}) then {
        if (_dropSet > 0 && {_dropSet in (missionNamespace getVariable ["ACME_infusion_dropSets", [10,15,20,60]])}) then {_x set [20, _dropSet];};
        _x set [22, _position];
        _x set [21, [_position] call ACME_fnc_clampPositionToDrops];
        if (_tracked) then {
            if (count _x <= 26 || {isNil {_x select 26}}) then {_x set [26, if ((_x param [10, 0]) > 0) then {(_x param [14, 0]) / (_x select 10)} else {0}];};
            if (count _x <= 27 || {isNil {_x select 27}}) then {_x set [27, 1];};
            _x set [28, _ledger apply {+_x}];
        };
    };
} forEach _updated;
[_patient, _updated] call ACME_fnc_infusionMedicationStateCommit;
[true] call _reply
