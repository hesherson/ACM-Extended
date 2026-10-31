if !([] call ACME_fnc_debugEnabled) exitWith {};
if !((call ACME_fnc_controlledProvider) getVariable ["ACME_hang_Active", false]) exitWith {
    ["Raise a bag before opening the placement tuner.", 2, (call ACME_fnc_controlledProvider)] call ace_common_fnc_displayTextStructured;
};
createDialog "ACME_HangBag_Tuner";
