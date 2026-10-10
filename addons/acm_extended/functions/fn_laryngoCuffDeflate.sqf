// letting the cuff down.
// call it as ["start", "tick" or "stop"] call ACME_fnc_laryngoCuffDeflate.
// it is the mirror of inflating it, on purpose: the same syringe, the same pilot balloon, the same held gesture and
// the air the other way. the medic learns one motion and uses it in both directions, which is also how it works
// with a real syringe on a real pilot balloon.
// this is the step that has to happen before the tube can be moved. an inflated cuff sits in the trachea below the
// cords, and dragging it up through them is how you tear somebody's larynx. the mod will let you try, and it will
// cost what it costs.
params ["_mode"];
private _pat = uiNamespace getVariable ["ACME_laryngo_patient", objNull];
if (isNull _pat) exitWith {};

switch (_mode) do {
    case "start": {
        // Tool ownership precedes cuff diagnostics; suction/right-click is not cuff work.
        if ((uiNamespace getVariable ["ACME_laryngo_held", ""]) != "syringe"
            || {!(_pat getVariable ["ACME_ETT_Inserted", false])}) exitWith {};
        if (_pat getVariable ["ACME_ETT_Secured", false]) exitWith {
            ["Take the collar off first.", 2.5] call ace_common_fnc_displayTextStructured;
        };
        if (!(_pat getVariable ["ACME_ETT_CuffInflated", false])) exitWith {
            ["The cuff is already down.", 2] call ace_common_fnc_displayTextStructured;
        };
        if ((uiNamespace getVariable ["ACME_laryngo_held", ""]) != "syringe") exitWith {
            ["Take the syringe from the tray first.", 2.5] call ace_common_fnc_displayTextStructured;
        };
        uiNamespace setVariable ["ACME_laryngo_deflateT0", diag_tickTime];
        [_pat, "ACME_SyringeDraw"] call ACME_fnc_worldSfxNearby;
    };

    case "tick": {
        private _t0 = uiNamespace getVariable ["ACME_laryngo_deflateT0", -1];
        if (_t0 < 0) exitWith {};
        private _need = missionNamespace getVariable ["ACME_ETT_deflateSec", 3.2];
        if ((diag_tickTime - _t0) >= _need) then {
            uiNamespace setVariable ["ACME_laryngo_deflateT0", -1];
            [_pat, -1, false, -1, -1, true, false] call ACME_fnc_ettAirwayStateCommit;
            uiNamespace setVariable ["ACME_laryngo_cuffHaul", 0];

            // The collar is already off (enforced by start). Successful deflation must immediately hand the placed
            // tube back to the adjustment/withdrawal state. Previously the UI remained in `cuff` with tubeInHand
            // false, so the only accidental way to regain the tube was to close/reopen the airway view.
            uiNamespace setVariable ["ACME_laryngo_state", "migrated"];
            uiNamespace setVariable ["ACME_laryngo_tubeInHand", true];
            uiNamespace setVariable ["ACME_laryngo_tubeGrip", false];
            uiNamespace setVariable ["ACME_laryngo_tubeAnchored", true];
            uiNamespace setVariable ["ACME_laryngo_tubeAimLock", "cords"];
            uiNamespace setVariable ["ACME_laryngo_held", "tube"];
            [] call ACME_fnc_laryngoRefreshSlots;

            playSound "ACME_VentClick";
            if (!isNil "ace_medical_treatment_fnc_addToLog") then {
                [_pat, "activity", "ET cuff deflated", []] call ace_medical_treatment_fnc_addToLog;
            };
        };
    };

    case "stop": {
        // let go early and the cuff is still up. the same as inflating: a partial pull is not a deflated cuff.
        if ((uiNamespace getVariable ["ACME_laryngo_deflateT0", -1]) >= 0) then {
            uiNamespace setVariable ["ACME_laryngo_deflateT0", -1];
            ["You let go. The cuff is still up.", 2.5] call ace_common_fnc_displayTextStructured;
        };
    };
};
