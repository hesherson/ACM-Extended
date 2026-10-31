// Input cannot outlive its captured patient/device panel.
if !([] call ACME_fnc_ventPanelContext) exitWith {};
// a bottom button-strip click, on the live screen: 0 is alarm, 1 is graph, 2 is manual breath and 3 is menu.
params ["_which"];
playSound "ACME_VentClick";
// if we were editing the FiO2, any strip press commits it.
if (uiNamespace getVariable ["ACME_vent_editingFio2", false]) then {
    uiNamespace setVariable ["ACME_vent_editingFio2", false];
};
switch (_which) do {
    case 0: {
        // the bell reports. it does not silence any more, and the x inside the window does that, exactly as on the device.
        // separating the two matters: show me what is wrong and I accept what is wrong are different acts, and a machine
        // that conflates them lets you mute a problem you never actually read.
        [] call ACME_fnc_ventAlarmWindow;
    };
    case 1: { ["graph"] call ACME_fnc_ventPanelShowScreen; };  // graph
    case 2: { [] call ACME_fnc_ventManualBreath; };  // manual breath
    case 3: { ["menu"] call ACME_fnc_ventPanelShowScreen; };  // MENU
};

