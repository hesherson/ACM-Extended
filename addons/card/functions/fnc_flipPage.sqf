params ["_control"];
private _display = ctrlParent _control;
if (isNull _display) exitWith {false};
private _context = _display getVariable ["DD1380_context", []];
if (count _context != 7 || {_display getVariable ["DD1380_closed", false]}) exitWith {false};
private _page = _display getVariable ["DD1380_page", 1];
_display setVariable ["DD1380_flipping", true];
// Harvest synchronously before opening the other page. The closed guard makes
// the native onUnload callback a no-op, even if Arma delivers it later.
[_display] call DD1380_card_fnc_setData;
_display closeDisplay 0;
if !(((uiNamespace getVariable ["DD1380_context", []]) param [3, ""]) isEqualTo (_context select 3)) exitWith {false};
createDialog (if (_page == 1) then {"DD1380_Card2_dlg"} else {"DD1380_Card1_dlg"})
