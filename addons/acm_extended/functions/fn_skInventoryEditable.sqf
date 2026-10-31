/* A tag may be edited on an owned carrier, its exact in-flight tag mutation,
 * or a source-funded current-kit allocation. Incoming adoption is read-only.
 */
params ["_owner","_row"];
if (isNull _owner || {!local _owner}) exitWith {false};
if ((_row param [13,"",[""]]) != "inventoryB279") exitWith {true};
private _sid = _row param [11,"",[""]];
if (_sid == "") exitWith {false};
if ([_owner,"syringe",_sid] call ACME_fnc_inventoryLedgerPossessed) exitWith {true};
private _epoch = _owner getVariable ["ACME_equipmentKitEpoch",0];
private _pending = (_owner getVariable ["ACME_inventoryPending",createHashMap]) getOrDefault ["syringe:" + _sid,[]];
if (count _pending >= 4 && {(_pending select 0) == "syringe"} && {(_pending select 1) == _sid} && {(_pending select 3) == _epoch}) exitWith {true};
private _escrow = _owner getVariable ["ACME_inventoryEscrow",createHashMap];
private _mutations = _owner getVariable ["ACME_inventoryMutations",createHashMap];
private _editable = false;
{
    private _held = _escrow getOrDefault [_x,[]];
    private _payload = _mutations get _x;
    if (count _held >= 6 && {(_held select 2) == "syringe"} && {(_held select 4) == _epoch}
        && {(_payload param [0,"",[""]]) == _sid} && {((_held select 1) param [0,"",[""]]) == _sid}) then {
        private _record = missionNamespace getVariable [format ["ACME_inventoryToken_%1",_held select 0],[]];
        if (count _record >= 7 && {(_record select 3) isEqualTo _owner} && {(_record select 5) in ["held","reserved"]}) exitWith {_editable = true;};
    };
} forEach (keys _mutations);
_editable
