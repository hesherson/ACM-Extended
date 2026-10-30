/* Owner-only, bounded document replacement. Duplicate delivery replays its
 * receipt; a different editor's revision cannot be silently overwritten. */
params [["_patient", objNull, [objNull]], ["_medic", objNull, [objNull]], ["_epoch", -1], ["_id", ""], ["_revision", -1], ["_data", []], ["_hops", 0]];
if (isNull _patient || {isNull _medic} || {!(_id isEqualType "")} || {_id == ""} || {count _id > 128}
    || {!(_hops isEqualType 0)} || {!finite _hops} || {_hops != floor _hops} || {_hops < 0} || {_hops > 4}) exitWith {false};
if (!local _patient) exitWith {
    if (_hops < 4) then {
        ["LNX_DD1380_Save", [_patient, _medic, _epoch, _id, _revision, _data, _hops + 1], _patient] call CBA_fnc_targetEvent;
    };
    false
};
private _ack = {
    params ["_accepted", "_reason"];
    ["LNX_DD1380_SaveAck", [_medic, _patient, _epoch, _id, _accepted, _reason], _medic] call CBA_fnc_targetEvent;
    _accepted
};
if !(_epoch isEqualType 0 && {_epoch == ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {[false, "The casualty changed. Reopen the card."] call _ack};
private _document = [_patient, false] call DD1380_card_fnc_getDocument;
private _receipts = _patient getVariable ["DD1380_Receipts", []];
if !(_receipts isEqualType []) then {_receipts = [];};
private _found = _receipts findIf {_x isEqualType [] && {count _x == 4} && {(_x select 0) isEqualTo _id} && {(_x select 1) isEqualTo _medic} && {(_x select 2) isEqualTo _epoch}};
if (_found >= 0) exitWith {[(_receipts select _found) select 3, ""] call _ack};
private _sameVehicle = !isNull objectParent _medic && {objectParent _medic isEqualTo objectParent _patient};
if (!alive _medic || {_medic getVariable ["ACE_isUnconscious", false]}
    || {!_sameVehicle && {_medic distance _patient > 6}}) exitWith {[false, "The card could not be saved from this position."] call _ack};
if !(_revision isEqualType 0 && {finite _revision} && {_revision >= 0} && {_revision == floor _revision}
    && {_revision == (_document select 0)}) exitWith {[false, "The card was changed by another provider. Reopen it to review the latest entries."] call _ack};
if !(_data isEqualType [] && {count _data == 5}) exitWith {[false, "The card contains invalid data."] call _ack};
private _fields = call DD1380_card_fnc_fieldIds;
private _valid = true;
{
    private _index = _forEachIndex;
    if !(_x isEqualType createHashMap) exitWith {_valid = false;};
    private _allowed = _fields select _index;
    if (count _x != count _allowed) exitWith {_valid = false;};
    private _map = _x;
    {
        private _value = _map get _x;
        if !(_x in _allowed) exitWith {_valid = false;};
        if (_index in [0, 1, 3]) then {
            if !(_value isEqualType false) exitWith {_valid = false;};
        } else {
            if !(_value isEqualType "" && {count _value <= (if (_x == 1651) then {4096} else {1024})}) exitWith {_valid = false;};
        };
    } forEach (keys _map);
    if (!_valid) exitWith {};
} forEach _data;
if (!_valid) exitWith {[false, "The card contains invalid data."] call _ack};
// Freeze the accepted packet: local CBA delivery can share HashMap references
// with its caller just as a native network delivery would serialize them.
_data = _data apply {
    private _map = _x;
    createHashMapFromArray ((keys _map) apply {[_x, _map get _x]})
};
_patient setVariable ["DD1380_Document", [_revision + 1, _data], true];
{
    _patient setVariable [_x, _data select _forEachIndex, true];
} forEach ["DD1380_Priority", "DD1380_Checkboxes", "DD1380_Text", "DD1380_Back_Checkboxes", "DD1380_Back_Text"];
_patient setVariable ["DD1380_Revision", _revision + 1, true];
_receipts pushBack [_id, _medic, _epoch, true];
if (count _receipts > 32) then {_receipts deleteAt 0;};
_patient setVariable ["DD1380_Receipts", _receipts, true];
[true, ""] call _ack
