/* Project exact held, reserved and pending inventory identities into the existing
 * Narc Box. Held records follow their token after native player/container transfer.
 * An active plunger retains its owner-local row until all patient receipts settle.
 */
params ["_owner",["_held",[],[[]]],["_reserved",[],[[]]],["_pending",[],[[]]]];
if (isNull _owner || {!local _owner}) exitWith {false};
private _current = _owner getVariable ["ACME_narcStore",[]];
private _hidden = _owner getVariable ["ACME_syringeInventoryHidden",[]];
private _rows = _current select {(_x param [13,"",[""]]) != "inventoryB279" || {(_x param [11,"",[""]]) in _hidden}};
private _seen = _rows apply {_x param [11,"",[""]]};
{
    private _sid = _x param [0,"",[""]];
    private _row = _x param [1,[],[[]]];
    if (_sid != "" && {!(_sid in _seen)} && {!(_sid in _hidden)} && {count _row >= 12}) then {
        _rows pushBack (+_row);
        _seen pushBack _sid;
    };
} forEach (_held + _pending);
{
    private _sid = _x param [0,"",[""]];
    if (_sid == "" || {_sid in _seen} || {_sid in _hidden}) then {continue};
    private _idx = _current findIf {(_x param [11,"",[""]]) == _sid};
    private _row = if (_idx >= 0) then {+(_current select _idx)} else {+(_x param [1,[],[[]]])};
    if (count _row >= 12) then {_rows pushBack _row; _seen pushBack _sid;};
} forEach _reserved;
// Preserve the former presentation order, so a transfer refresh never changes
// which remembered syringe the medic has selected while browsing.
private _ordered = [];
{
    private _sid = _x param [11,"",[""]];
    private _idx = _rows findIf {(_x param [11,"",[""]]) == _sid};
    if (_idx >= 0) then {_ordered pushBack (_rows deleteAt _idx);};
} forEach _current;
_ordered append _rows;
if !(_ordered isEqualTo _current) then {
    // Live reserved syringes include private plunger changes. Their final public
    // update belongs to the receipt settlement, never to an inventory poll.
    _owner setVariable ["ACME_narcStore",_ordered,_reserved isEqualTo []];
};
true
