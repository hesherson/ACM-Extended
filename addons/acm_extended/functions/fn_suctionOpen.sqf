// Open the shared airway screen in suction-only mode after ACE finishes its action.
// Keep the legacy type argument for callers. Eligible shared equipment selects the actual device.
params ["_medic", "_patient", ["_type", 1]];

if (!hasInterface) exitWith {  };
if (isNull _patient) exitWith {  };

// Keep an unspent manual bag in inventory until the first squeeze.
if (isNull _medic || {!local _medic}) exitWith {};
if (([_medic, _patient, "ACM_ACCUVAC"] call ACME_fnc_treatmentSupplyCount) < 1 && {
    ([_medic, _patient, "ACM_SuctionBag"] call ACME_fnc_treatmentSupplyCount) < 1
}) exitWith {["No suction device carried.", 2] call ace_common_fnc_displayTextStructured;};
uiNamespace setVariable ["ACME_suction_bagOwner", []];
uiNamespace setVariable ["ACME_suction_resume", []];
uiNamespace setVariable ["ACME_laryngo_patient", _patient];
uiNamespace setVariable ["ACME_laryngo_medic", _medic];
uiNamespace setVariable ["ACME_suction_standalone", true];
// The initializer selects the actual profile before the first tray refresh.
uiNamespace setVariable ["ACME_suction_type", -2];

// open on a short delay rather than here and now.
// this runs inside the callbacksuccess of an ACE treatment, and ACE is still tearing its own treatment down at
// that moment: it closes the progress bar and reopens the medical menu on the frames immediately after the
// callback returns. a dialog created synchronously here is created into the middle of that teardown and is
// destroyed by it, which on screen is the suction window appearing for a frame and then vanishing.
// every other minigame in this addon already opens on a delay for the same reason. fn_laryngoopen uses 0.1 s
// into this identical dialog, so this matches it exactly rather than inventing a second timing.
[{
    if !(createDialog "ACME_Laryngoscopy_Dialog") exitWith {
        uiNamespace setVariable ["ACME_suction_standalone", false];
        ["Could not open the suction screen.", 2] call ace_common_fnc_displayTextStructured;
    };
}, [], 0.1] call CBA_fnc_waitAndExecute;
