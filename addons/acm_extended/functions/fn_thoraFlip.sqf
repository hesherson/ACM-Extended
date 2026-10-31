// toggle which hemithorax we are working, right to left and back. it swaps the body image and the 5th ics accept
// zone, then re-renders.
// only the side flips: the palpated-site lock, if any, is per-side, so switching sides shows the own progress of that
// side.
private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
[_side] call ACME_fnc_thoraPrepFlush;
uiNamespace setVariable ["ACME_Thora_Prepping", false];
uiNamespace setVariable ["ACME_Thora_PrepLast", []];
_side = ["right", "left"] select (_side == "right");
uiNamespace setVariable ["ACME_Thora_Side", _side];
uiNamespace setVariable ["ACME_Thora_OnZone", false];
uiNamespace setVariable ["ACME_Thora_Burp", ["", 0, 0, false]];
[] call ACME_fnc_thoraRender;
[] call ACME_fnc_thoraUpdateTrayIcons;
