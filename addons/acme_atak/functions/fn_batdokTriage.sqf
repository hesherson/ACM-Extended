params [["_u", objNull], ["_t", ""]];
if (isNull _u) exitWith {};
private _lvl = ["Unassigned", "Minimal", "Delayed", "Immediate", "Deceased"] find _t;
if (_lvl >= 0) then { _u setVariable ["ace_medical_triageLevel", _lvl, true] };
