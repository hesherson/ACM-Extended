/* Change-only UI writes. Recommitting unchanged hit rectangles can synthesize
   enter/exit cycles and repeated hide/show can drop a held mouse click. */
params ["_c","_property","_value"];
if (isNull _c) exitWith {false};
// The final B273 layout owns these rectangles. Historical state/selection code
// can still run without moving controls back through its old intermediate layout.
private _display = ctrlParent _c;
if (_property == "position" && {_display getVariable ["ACME_txLayoutManaged", false]}
    && {!(_display getVariable ["ACME_txLayoutWriting", false])}
    && {(ctrlIDC _c) in [86002,86003,86004,86005,86006,86007,86008,86037,
        86120,86121,86122,86126,86127,86128,86129,86130,86131,86132,86133,
        86134,86141,86142,86143,86144,86145,86146,86147,86148,86149]}) exitWith {true};
switch (_property) do {
    case "position": {if ((ctrlPosition _c) isNotEqualTo _value) then {_c ctrlSetPosition _value;_c ctrlCommit 0;};};
    case "show": {if ((ctrlShown _c) isNotEqualTo _value) then {_c ctrlShow _value;};};
    case "enable": {if ((ctrlEnabled _c) isNotEqualTo _value) then {_c ctrlEnable _value;};};
    case "text": {if ((ctrlText _c) isNotEqualTo _value) then {_c ctrlSetText _value;};};
    case "color": {if ((ctrlTextColor _c) isNotEqualTo _value) then {_c ctrlSetTextColor _value;};};
};
true
