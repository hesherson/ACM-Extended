// toggle a clinical feature on the megacode dummy from the neuro and features page, and the pulse toggle on the
// vitals page.
// these are panel-authoritative training states, and herniation also drives a cushing-style vitals pattern and a
// blown pupil as a creative-liberty linkage. it refreshes the current page.
// _this is [_key].
params ["_key"];
private _d = uiNamespace getVariable ["ACME_MC_target", objNull];
if (isNull _d) exitWith {};
private _k = toLower _key;
private _page = uiNamespace getVariable ["ACME_MC_page", "neuro"];

switch (_k) do {
    case "herniation": {
        private _h = !(_d getVariable ["ACME_MC_herniation", false]);
        _d setVariable ["ACME_MC_herniation", _h, true];
        if (_h) then {
            // the cushing triad: hypertension plus bradycardia, plus coma. the hr is a real ACM target and the unconsciousness
            // is real ACE, while the SBP, DBP and ICP are monitor-authoritative.
            // the keeper (ACME_fnc_megacodeWatch) eases the live vitals toward the *Tgt values every second, so the
            // Cushing numbers are set as targets too: set only as live values they drifted straight back to normal.
            {_d setVariable [_x select 0, _x select 1, true];} forEach [
                ["ACME_MC_SBP", 200], ["ACME_MC_SBPTgt", 200], ["ACME_MC_DBP", 110], ["ACME_MC_DBPTgt", 110],
                ["ACME_MC_HR", 40], ["ACME_MC_HRTgt", 40]
            ];
            [_d, [["heartRate", 40]], true] call ACM_core_fnc_setTargetVitalsState;
            _d setVariable ["ACME_MC_ICP", 50, true];
            _d setVariable ["ACME_MC_GCS", 3, true];
            if (!(_d getVariable ["ACE_isUnconscious", false])) then {
                [_d, true] remoteExec ["ace_medical_status_fnc_setUnconsciousState", _d];
            };
        } else {
            // off: the Cushing targets go back to baseline (a coma is left for the instructor to wake).
            {_d setVariable [_x select 0, _x select 1, true];} forEach [
                ["ACME_MC_SBPTgt", 122], ["ACME_MC_DBPTgt", 78], ["ACME_MC_HRTgt", 78], ["ACME_MC_ICP", 10]
            ];
            [_d, [["heartRate", 78]], true] call ACM_core_fnc_setTargetVitalsState;
        };
        [[(if (_h) then {"Herniation ON (Cushing + coma)"} else {"Herniation off"}), "#ff8a8a"]] call ACME_fnc_megacodeLog;
    };
    case "uncon": {
        // a direct, real consciousness toggle.
        private _want = !(_d getVariable ["ACE_isUnconscious", false]);
        _d setVariable ["ACME_MC_GCS", (if (_want) then {3} else {15}), true];
        [_d, _want] remoteExec ["ace_medical_status_fnc_setUnconsciousState", _d];
        [[(if (_want) then {"Made unconscious"} else {"Woke up"}), "#bcd4ff"]] call ACME_fnc_megacodeLog;
    };
};
[87300, _page] call ACME_fnc_megacodeMenu;
