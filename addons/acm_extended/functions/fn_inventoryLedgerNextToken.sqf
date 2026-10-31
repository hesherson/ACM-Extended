/* Server-profile monotonic native ID allocator. Reserve a block on disk before
 * issuing its first ID. Retain this profile with mission saves. IDs from abandoned
 * blocks are intentionally lost after a crash; they are never recycled. */
if (!isServer) exitWith {0};
private _avoid = [];
if (!isNil "_this" && {_this isEqualType []} && {count _this == 1} && {(_this select 0) isEqualType []}) then {_avoid = _this select 0;};
if ((_avoid findIf {!(_x isEqualType 0) || {!finite _x} || {_x != floor _x} || {_x < 1} || {_x > 65534}}) >= 0) exitWith {0};
if (isNil {missionNamespace getVariable "ACME_inventoryTokenReservedThrough"}) then {
    private _highWater = profileNamespace getVariable ["ACME_inventoryTokenHighWater_v1",0];
    if !(_highWater isEqualType 0 && {finite _highWater} && {_highWater == floor _highWater}
        && {_highWater >= 0} && {_highWater <= 65534}) then {
        _highWater = 65534;
        diag_log "[ACME INVENTORY] Invalid persistent token high-water mark; allocation disabled. Restore the server profile or import into a new profile explicitly.";
    };
    missionNamespace setVariable ["ACME_inventoryTokenSequence",(missionNamespace getVariable ["ACME_inventoryTokenSequence",0]) max _highWater];
    missionNamespace setVariable ["ACME_inventoryTokenReservedThrough",_highWater];
};
private _sequence = missionNamespace getVariable ["ACME_inventoryTokenSequence",0];
// Explicit imports can move between server profiles. Their source IDs must not
// also be their replacement IDs, even when this profile has never issued an ID.
while {_sequence < 65534 && {(_sequence + 1) in _avoid}} do {_sequence = _sequence + 1;};
if (_sequence >= 60000 && {_sequence < 65534} && {!(missionNamespace getVariable ["ACME_inventoryBudgetWarned",false])}) then {
    missionNamespace setVariable ["ACME_inventoryBudgetWarned",true];
    diag_log format ["[ACME INVENTORY] Persistent ID budget %1/65534. Save fully settled native inventory plus ACME metadata and migrate before exhaustion; see B288-inventory-persistence.md.",_sequence];
};
if (_sequence >= 65534) exitWith {
    if (!(missionNamespace getVariable ["ACME_inventoryExhaustionReported",false])) then {
        missionNamespace setVariable ["ACME_inventoryExhaustionReported",true];
        diag_log "[ACME INVENTORY] Persistent token space exhausted; funded preparation retained, no identity reused. Preserve saves and migrate through explicit metadata import into a new server profile.";
    };
    0
};
if (_sequence >= (missionNamespace getVariable ["ACME_inventoryTokenReservedThrough",0])) then {
    private _through = (_sequence + 256) min 65534;
    profileNamespace setVariable ["ACME_inventoryTokenHighWater_v1",_through];
    saveProfileNamespace;
    missionNamespace setVariable ["ACME_inventoryTokenReservedThrough",_through];
};
_sequence = _sequence + 1;
missionNamespace setVariable ["ACME_inventoryTokenSequence",_sequence];
_sequence
