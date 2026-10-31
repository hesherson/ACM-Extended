/* Native display unload retires this presentation only; no medical workers or transactions are touched. */
params ["_display"];
_display setVariable ["ACME_reactSession",""];
_display setVariable ["ACME_reactReady",false];
_display setVariable ["ACME_reactPainted",false];
_display setVariable ["ACME_reactActive",false];
_display setVariable ["ACME_reactRows",createHashMap];
_display setVariable ["ACME_reactContext",[]];
