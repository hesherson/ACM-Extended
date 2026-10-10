/* Change-only UI writes. Recommitting unchanged hit rectangles can synthesize
   enter/exit cycles and repeated hide/show can drop a held mouse click. */
params ["_c","_property","_value"];
if (isNull _c) exitWith {false};
switch (_property) do {
    case "position": {if ((ctrlPosition _c) isNotEqualTo _value) then {_c ctrlSetPosition _value;_c ctrlCommit 0;};};
    case "show": {if ((ctrlShown _c) isNotEqualTo _value) then {_c ctrlShow _value;};};
    case "enable": {if ((ctrlEnabled _c) isNotEqualTo _value) then {_c ctrlEnable _value;};};
    case "text": {if ((ctrlText _c) isNotEqualTo _value) then {_c ctrlSetText _value;};};
    case "color": {if ((ctrlTextColor _c) isNotEqualTo _value) then {_c ctrlSetTextColor _value;};};
};
true
