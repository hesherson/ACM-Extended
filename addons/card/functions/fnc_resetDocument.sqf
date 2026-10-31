/* A medical full-heal preserves documentation. A new life starts a new card. */
params ["_patient"];
if (isNull _patient || {!local _patient}) exitWith {false};
_patient setVariable ["DD1380_Document", nil, true];
{_patient setVariable [_x, createHashMap, true];} forEach ["DD1380_Priority", "DD1380_Checkboxes", "DD1380_Text", "DD1380_Back_Checkboxes", "DD1380_Back_Text"];
_patient setVariable ["DD1380_Revision", 0, true];
_patient setVariable ["DD1380_Receipts", [], true];
[_patient, true] call DD1380_card_fnc_getDocument;
true
