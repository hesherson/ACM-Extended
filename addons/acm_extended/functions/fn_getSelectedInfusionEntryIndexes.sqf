private _stored = uiNamespace getVariable ["ACME_RollerClamp_Context", []];
private _display = findDisplay 86000;
// onUnload can run after both dialogs have gone. Validate the captured session
// through the same path as an open clamp before submitting its final position.
if ((!isNull (findDisplay 86200) || {isNull _display}) && {!(_stored isEqualTo [])}) exitWith {
    _stored params ["_patient", "_indexes", ["_ids", []], ["_epoch", -1], ["_capturedBagId", ""]];
    if (isNull _patient) exitWith {[]};
    if (_epoch >= 0 && {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {[]};
    if (_ids isEqualTo []) exitWith {[_patient, _indexes]};
    private _entries = _patient getVariable ["ACME_infusion_BagMedications", []];
    private _live = [];
    {private _uid = _x; private _i = _entries findIf {(_x param [0, ""]) == _uid}; if (_i >= 0) then {_live pushBack _i;};} forEach _ids;
    private _bagIds = [];
    {private _id = (_entries select _x) param [23, ""]; if (_id != "") then {_bagIds pushBackUnique _id;};} forEach _live;
    // A clamp session belongs to one physical bag. Retained medication rows
    // cannot keep a removed bag alive or move the session to another carrier.
    if (count _bagIds != 1) exitWith {[_patient, []]};
    private _bagId = _bagIds select 0;
    if (_capturedBagId != "" && {_bagId != _capturedBagId}) exitWith {[_patient, []]};
    private _physicalMatches = 0;
    private _map = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
    {
        {if ((_x param [8, ""]) == _bagId) then {_physicalMatches = _physicalMatches + 1;};} forEach (_map get _x);
    } forEach keys _map;
    if (_physicalMatches != 1) exitWith {[_patient, []]};
    _live = [];
    {if ((_x param [23, ""]) == _bagId) then {_live pushBack _forEachIndex;};} forEach _entries;
    [_patient, _live]
};
if (isNull _display) exitWith {[]};

private _context = ["infusion"] call ACME_fnc_getSelectedActiveBagContext;
if (_context isEqualTo []) exitWith {[]};

_context params ["_patient", "_bodyPart", "_bagIndex", "_type", "_accessType", "_bagAccessSite", "_bagIV", "_bloodType", "_volume", "_freshBloodID", "_remainingVolume"];

private _entries = _patient getVariable ["ACME_infusion_BagMedications", []];
private _indexes = [];
private _bag = ((_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_bodyPart, []]) param [_bagIndex, []];
private _bagId = _bag param [8, ""];
private _row = [_type, _remainingVolume, _accessType, _bagAccessSite, _bagIV, _bloodType, _volume, _freshBloodID, _bagIndex];

{
    _x params ["", "_eBodyPart", "_eBagIndex", "", "_eAccessSite", "_eIV"];
    private _entryBagId = _x param [23, ""];
    if (_entryBagId != "") then {
        // Native indices and access coordinates can lag a move/removal update.
        // The stable physical UID still binds every additive to this one bag.
        if (_bagId != "" && {_entryBagId == _bagId}) then {_indexes pushBack _forEachIndex;};
    } else {
        // Legacy rows have no durable bag identity. Keep their exact-slot
        // compatibility, but never borrow the shared matcher's loose fallback
        // from an identical neighbour or an orphaned original slot.
        if (toLowerANSI _eBodyPart == toLowerANSI _bodyPart && {_eBagIndex == _bagIndex}
            && {_eAccessSite == _bagAccessSite} && {_eIV isEqualTo _bagIV}
            && {([_patient, _bodyPart, _row, [_x]] call ACME_fnc_bagInfusionEntry) isNotEqualTo []}) then {
            _indexes pushBack _forEachIndex;
        };
    };
} forEach _entries;

private _result = [_patient, _indexes];
if !(_indexes isEqualTo []) then {
    uiNamespace setVariable ["ACME_RollerClamp_Context", [_patient, _indexes, _indexes apply {(_entries select _x) select 0}, [_patient] call ACME_fnc_clinicalEpoch, _bagId]];
};
_result
