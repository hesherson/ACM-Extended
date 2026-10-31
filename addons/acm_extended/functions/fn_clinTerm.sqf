// resolve a stringtable key to its hardcore clinical wording.
// call it as [_key] call ACME_fnc_clinTerm, which returns the clinical text, or "" when the key has no entry
// or the descriptor setting is off. "" means the caller should fall through to `localize` as normal.
//
// why a table keyed on the stringtable ID rather than a pile of function overrides.
// ACM and ACE pass raw KEYS into ace_common_fnc_displayTextStructured and addToLog and let those two localize,
// which is verified at:
//   ACM breathing/functions/fnc_checkBreathingLocal.sqf  the whole switch assigns LSTRING keys
//   ACM airway/functions/fnc_checkAirway.sqf:113         same
//   ACE medical_treatment/functions/fnc_checkResponse.sqf:30, and note :37 passes the key as the log FORMAT
// so intercepting at those two output points reaches every one of these without copying a single ACM function
// into this addon. the alternative was three more overrides that go stale the next time ACM ships.
//
// scoped exactly to the inventory rulings. everything not in this table stays vanilla in both registers:
//   3.2 response      only the two strings carrying a physical finding. the plain responsive, unresponsive and
//                     unconscious lines are untouched and AVPU is not used anywhere.
//   3.3 breathing     all seven, each with the "Patient is" lead you asked for. the _Short forms feed the log
//                     and stay bare, because a sentence prefix in a flowsheet entry reads wrong.
//   3.4 chest         bruising only. chest excursion and the tracheal deviation rewrites are struck.
//   3.5 airway        severe inflammation only. head tilt chin lift, the collapse and obstruction ladders and
//                     the mild and significant inflammation rows are all vanilla.
//   3.6 crt, skin,
//       pupils        absent on purpose. nothing added.
//   3.7 limb inspection uses the callback in fn_inspectForFracture; it resolves both hint and log here.
params [["_key", ""]];
if (!(_key isEqualType "")) exitWith { "" };
if (_key isEqualTo "") exitWith { "" };
if (!(((missionNamespace getVariable ["ACME_hc_descriptors", false]) isEqualTo true))) exitWith { "" };

private _map = missionNamespace getVariable ["ACME_clinTermMap", createHashMap];
if ((count _map) == 0) then {
    _map = createHashMapFromArray [
        // 3.2 response. ACE ships different text for dead and for arrest already, so a medic can tell them
        // apart from a response check in vanilla too. this widens an existing gap rather than opening one.
        ["str_ace_medical_treatment_check_response_cardiacarrest",
            "%1 is unresponsive with agonal respirations and myoclonic activity"],
        ["str_ace_medical_treatment_check_response_dead",
            "%1 is unresponsive, apneic, pulseless and cool to the touch"],

        // 3.3 breathing, all seven with the "Patient is" lead. the _Short forms feed the log and stay bare,
        // because a sentence prefix in a flowsheet entry reads wrong.
        // these are resolved by overrides/fn_checkBreathingLocal.sqf directly, NOT by the displayTextStructured
        // wrapper. ACM sends that hint through CBA_fnc_targetEvent and ACE registered the event with LINKFUNC,
        // which captured the original function value, so the wrapper never sees it. the override exists for
        // exactly that reason and resolves the key before the event is sent.
        // "Patient is shallow" is not English, so the shallow rows say what is actually low.
        ["str_acm_breathing_checkbreathing_normal",             "Patient is eupneic with equal chest rise"],
        ["str_acm_breathing_checkbreathing_normal_short",       "Eupneic"],
        // these four read their wording from fn_medDescriptor, which is the one place the two findings are
        // worded. this map is built only after the gate above, so the descriptor setting is on and
        // fn_medDescriptor returns the hardcore column every time this line runs.
        ["str_acm_breathing_checkbreathing_none",               (["breathing", "apneic"] call ACME_fnc_medDescriptor)],
        ["str_acm_breathing_checkbreathing_none_short",         (["breathing", "apneicShort"] call ACME_fnc_medDescriptor)],
        ["str_acm_breathing_checkbreathing_slow",               "Patient is bradypneic"],
        ["str_acm_breathing_checkbreathing_slow_short",         "Bradypneic"],
        ["str_acm_breathing_checkbreathing_rapid",              "Patient is tachypneic"],
        ["str_acm_breathing_checkbreathing_rapid_short",        "Tachypneic"],
        ["str_acm_breathing_checkbreathing_shallow",            "Patient is breathing with poor tidal volume"],
        ["str_acm_breathing_checkbreathing_shallow_short",      "Poor tidal volume"],
        ["str_acm_breathing_checkbreathing_shallowslow",        "Patient is bradypneic with poor tidal volume"],
        ["str_acm_breathing_checkbreathing_shallowslow_short",  "Bradypneic, poor tidal volume"],
        ["str_acm_breathing_checkbreathing_shallowrapid",       (["breathing", "tachyShallow"] call ACME_fnc_medDescriptor)],
        ["str_acm_breathing_checkbreathing_shallowrapid_short", (["breathing", "tachyShallowShort"] call ACME_fnc_medDescriptor)],

        // 3.4 chest, bruising only.
        ["str_acm_breathing_inspectchest_bruising",             "Severe Ecchymosis"],
        ["str_acm_breathing_inspectchest_bruising_short",       "Severe Ecchymosis"],

        // 3.5 airway, severe inflammation only. the mild and significant rows above it stay in ACM's wording,
        // so the ladder changes register at the top step. that is deliberate: severe is the one that changes
        // management.
        ["str_acm_airway_checkairway_inflammation_severe",       "Severe pharyngeal edema"],
        ["str_acm_airway_checkairway_inflammation_severe_short", "Severe pharyngeal edema"],

        // 3.1 pulse. these are localized inside overrides/fn_checkPulseLocal.sqf before they are emitted, so
        // the wrappers never see the key. that file calls this function directly instead.
        ["str_ace_medical_treatment_check_pulse_output_1", "Radial pulse %2, regular"],
        ["str_ace_medical_treatment_check_pulse_output_2", "Weak, thready pulse"],
        ["str_ace_medical_treatment_check_pulse_output_3", "Strong, bounding pulse"],
        ["str_ace_medical_treatment_check_pulse_output_4", "Pulse regular, normal amplitude"],
        ["str_ace_medical_treatment_check_pulse_output_5", "Pulseless"],
        ["str_ace_medical_treatment_check_pulse_weak",     "Thready"],
        ["str_ace_medical_treatment_check_pulse_strong",   "Bounding"],
        ["str_ace_medical_treatment_check_pulse_normal",   "Normal"],
        ["str_ace_medical_treatment_check_pulse_none",     "Absent"],

        // 3.7 fracture inspection. fn_inspectForFracture reads the selected limb's native state.
        // Absent crepitus is an observation; it never states that a fracture is excluded.
        ["str_acm_disability_inspectforfracture_splintapplied",
            "Patient's %1 is splinted; crepitus was not assessed through the splint."],
        ["str_acm_disability_inspectforfracture_splintapplied_short",
            "Splint in place; crepitus not assessed"],
        ["str_acm_disability_inspectforfracture_significantswelling",
            "Patient's %1 is severely contused with marked swelling and deformity; crepitus present."],
        ["str_acm_disability_inspectforfracture_significantswelling_short",
            "Severe contusion, marked swelling and deformity; crepitus present"],
        ["str_acm_disability_inspectforfracture_swelling",
            "Patient's %1 is severely contused and swollen; crepitus present."],
        ["str_acm_disability_inspectforfracture_swelling_short",
            "Severe contusion and swelling; crepitus present"],
        ["str_acm_disability_inspectforfracture_severebruising",
            "Patient's %1 is severely contused; crepitus present."],
        ["str_acm_disability_inspectforfracture_severebruising_short",
            "Severe contusion; crepitus present"],
        ["str_acm_disability_inspectforfracture_bruised",
            "Patient's %1 is visibly contused; no crepitus found."],
        ["str_acm_disability_inspectforfracture_bruised_short",
            "Visible contusion; no crepitus found"],
        ["str_acm_disability_inspectforfracture_noinjury",
            "Patient's %1 has no visible contusion or deformity; no crepitus found."],
        ["str_acm_disability_inspectforfracture_noinjury_short",
            "No visible contusion or deformity; no crepitus found"],
        ["str_acm_disability_inspectforfracture_realignmentperformed",
            "Limb realignment previously performed."],
        ["str_acm_disability_inspectforfracture_realignmentperformed_short",
            "realignment previously performed"],
        ["str_acme_disability_inspectforfracture_stabilized",
            "Patient's %1 has been stabilized; crepitus was not reassessed."],
        ["str_acme_disability_inspectforfracture_stabilized_short",
            "Limb stabilized; crepitus not reassessed"],
        ["str_acme_disability_inspectforfracture_confirmed",
            "Patient's %1 has crepitus on assessment."],
        ["str_acme_disability_inspectforfracture_confirmed_short",
            "Crepitus present"],
        ["str_acme_disability_inspectforfracture_indeterminate",
            "Patient's %1 requires reassessment; contusion and crepitus findings are indeterminate."],
        ["str_acme_disability_inspectforfracture_indeterminate_short",
            "Limb findings indeterminate; reassess"]
    ];
    missionNamespace setVariable ["ACME_clinTermMap", _map];
};

// keys are matched case-insensitively, because ArmA's own localize is and the addon references the same ACE
// keys in two different casings already: fn_checkPulseLocal writes STR_ACE_medical_treatment_... while the
// stringtable declares STR_ACE_Medical_Treatment_...
_map getOrDefault [toLower _key, ""]
