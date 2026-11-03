params [["_s", ""]];
if (!(_s isEqualType "") || {_s in ["", "_"]}) exitWith {""};
toString ((_s splitString ".") apply { parseNumber _x })
