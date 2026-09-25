// A targeted request lets a medic refresh premixed infusion state even when another client or the server owns
// the patient. The receiver writes only while the patient is local. The regular PFH catches an ownership change.
["ACME_syncPremixedBagsLocal", {
    params [["_patient", objNull, [objNull]]];
    if (!isNull _patient && {local _patient}) then {[_patient] call ACME_fnc_syncPremixedBags;};
}] call CBA_fnc_addEventHandler;

// Any ACE interaction menu replaces pulse palpation as the active interaction surface. Retire the pulse layer
// immediately so it can never remain underlaid behind another action/menu.
["ace_interactMenuOpened", {
    if (uiNamespace getVariable ["ACME_PulseCheckActive", false]) then {
        uiNamespace setVariable ["ACME_PulseCheckCancel", true];
        "ACM_FeelPulse" cutText ["","PLAIN",0,false];
    };
}] call CBA_fnc_addEventHandler;

// the medical menu opened.
["ace_medicalMenuOpened", {
    params ["_medic", "_target", "_display"];

    // Pulse palpation is a modal cutRsc. Opening the medical menu must retire it immediately; otherwise the pulse
    // layer can survive underneath the menu and keep its input/pose handlers alive until the player finds Escape.
    if (uiNamespace getVariable ["ACME_PulseCheckActive", false]) then {
        uiNamespace setVariable ["ACME_PulseCheckCancel", true];
        "ACM_FeelPulse" cutText ["","PLAIN",0,false];
    };

    // Register a premixed bag at once when the patient menu opens. Pass the target explicitly. A bare call here
    // inherits this event's _this array and previously treated the medic as the optional patient argument.
    [_target] call ACME_fnc_syncPremixedBags;

    // Bind Unload to its original provider and generation, never a later ACE_player/menu.
    if (_medic isEqualTo ACE_player) then {
        [_medic, _target, _display] call ACME_fnc_menuPoseStart;
        if (!isNull _display) then {
            _display displayAddEventHandler ["Unload", {
                params ["_display"];
                private _owner = _display getVariable ["ACME_menuPoseOwner", []];
                if (count _owner == 2) then {[_owner select 0, false, _owner select 1] call ACME_fnc_menuPoseStop;};
            }];
        };
    };

    // the hardcore site relabel used to start a 0-delay PFH here that repainted ACE's buttons and injury list
    // after ACE had drawn them. it is gone. the buttons are now relabelled at the single ctrlSetText in
    // overrides/fn_updateActions.sqf, and the injury list on the ace_medical_gui_updateInjuryListPart event
    // below, both of which run inside ACE's own build rather than chasing it.
    // this also fixes a real defect: the PFH only started when hardcore was ALREADY on at the moment the menu
    // opened, so toggling the setting with the menu up appeared to do nothing.
}] call CBA_fnc_addEventHandler;

// Eligibility is patient-specific and only follows a real started treatment. Menu
// inspection and failed availability checks do not turn first contact into empty hands.
["ace_treatmentStarted", {
    params ["_medic", "_patient", ["_bodyPart", ""], ["_classname", ""]];
    if (!isNull _medic && {local _medic} && {!isNull _patient} && {_medic isNotEqualTo _patient}) then {
        _medic setVariable ["ACME_menuPoseAfterTreatment", _patient];
        _medic setVariable ["ACME_menuPoseCare", [_patient, _classname]];
    };
}] call CBA_fnc_addEventHandler;

// Some treatments close their source menu before their next-frame pose starts.
// Re-arm only the matching, genuinely started care on completion/cancellation.
{
    [_x, {
        params ["_medic", "_patient", ["_bodyPart", ""], ["_classname", ""]];
        if (isNull _medic || {!local _medic}) exitWith {};
        if ((_medic getVariable ["ACME_menuPoseCare", []]) isEqualTo [_patient, _classname]) then {
            _medic setVariable ["ACME_menuPoseCare", []];
            _medic setVariable ["ACME_menuPoseAfterTreatment", _patient];
        };
    }] call CBA_fnc_addEventHandler;
} forEach ["ace_treatmentSucceded", "ace_treatmentFailed"];
