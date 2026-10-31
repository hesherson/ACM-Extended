/* Only retire resources owned by this display. Physiology and native transactions continue. */
params ["_display"];
private _pfh = _display getVariable ["ACME_reactPFH",-1];
if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
_display setVariable ["ACME_reactPFH",-1];
_display setVariable ["ACME_reactSession",""];
_display setVariable ["ACME_reactReady",false];
_display setVariable ["ACME_reactContext",[]];
