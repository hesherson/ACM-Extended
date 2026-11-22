// SKED litter settings (CBA, server wide).
[
    "acme_sked_bearersRequired", "SLIDER",
    ["Rescuers to lift", "How many rescuers must hold a handle before the SKED can be lifted and carried."],
    ["ACM Extended", "SKED"], [1, 2, 2, 0], 1
] call CBA_fnc_addSetting;
[
    "acme_sked_allowConscious", "CHECKBOX",
    ["Strap in conscious casualties", "Off: only unconscious or dead casualties can be strapped into a SKED."],
    ["ACM Extended", "SKED"], false, 1
] call CBA_fnc_addSetting;
[
    "acme_sked_strip", "CHECKBOX",
    ["Undress casualties on a litter", "A casualty strapped on a SKED or litter is undressed so the blanket fits. Everything is kept and given back when they are unstrapped; their pack lies on their legs meanwhile."],
    ["ACM Extended", "SKED"], true, 1
] call CBA_fnc_addSetting;
[
    "acme_drag_maxMass", "SLIDER",
    ["Drag: heaviest thing (kg)", "Things heavier than this cannot be dragged behind you. Casualties and litters always can."],
    ["ACM Extended", "SKED"], [50, 5000, 1500, 0], 1
] call CBA_fnc_addSetting;
[
    "acme_drag_onto", "CHECKBOX",
    ["Drag: onto a litter loads the casualty", "A casualty who is dragged onto a laid out, empty SKED or Talon is put into it without the loading timer."],
    ["ACM Extended", "SKED"], true, 1
] call CBA_fnc_addSetting;
[
    "acme_slide", "CHECKBOX",
    ["Casualties slide on steep slopes", "A casualty who is left lying on a steep slope, or strapped into a litter nobody holds, slides down it. Nothing moves on shallower ground."],
    ["ACM Extended", "SKED"], true, 1
] call CBA_fnc_addSetting;
[
    "acme_slide_angle", "SLIDER",
    ["Slide: from this slope", "The angle of the ground (degrees) from which a casualty on the ground slides. A SKED is a plastic sled and goes 8 degrees earlier. Just over the angle the slide is a crawl; the steeper, the faster."],
    ["ACM Extended", "SKED"], [15, 50, 30, 0], 1
] call CBA_fnc_addSetting;
[
    "acme_drag_jog", "CHECKBOX",
    ["Drag: jog with the sprint key", "A rescuer who drags or carries can jog while he holds the sprint key: one fixed pace, and with ACE's fatigue on it costs him several times the effort. Off: he can only walk."],
    ["ACM Extended", "SKED"], true, 1
] call CBA_fnc_addSetting;
[
    "acme_drag_jogPace", "SLIDER",
    ["Drag: jog pace", "The pace of that jog, as a share of an unladen jog."],
    ["ACM Extended", "SKED"], [0.5, 1, 0.72, 2], 1
] call CBA_fnc_addSetting;
[
    "acme_drag_jogDuty", "SLIDER",
    ["Drag: jog effort", "How many times the effort of an unladen jog it costs (ACE advanced fatigue)."],
    ["ACM Extended", "SKED"], [1, 8, 3.5, 1], 1
] call CBA_fnc_addSetting;
[
    "acme_drag_strapRope", "CHECKBOX",
    ["Drag: SKED strap to the hip", "The strap of a dragged SKED runs from its head end up to the rescuer's left hip and swings after him. Off: it stays flat on the ground."],
    ["ACM Extended", "SKED"], true, 1
] call CBA_fnc_addSetting;
[
    "acme_drag_dust", "CHECKBOX",
    ["Drag: dust", "Dust where a dragged litter, box or casualty scrapes over dry ground. Made on your machine only."],
    ["ACM Extended", "SKED"], true, 0
] call CBA_fnc_addSetting;
[
    "acme_drag_sound", "CHECKBOX",
    ["Drag: sound", "The sound of a dragged litter, box or casualty scraping over the ground, by the kind of ground. Made on your machine only."],
    ["ACM Extended", "SKED"], true, 0
] call CBA_fnc_addSetting;
[
    "acme_drag_limp", "CHECKBOX",
    ["Drag: limp casualty", "A casualty who is dragged behind you lies in a limp pose of his own, with loose limbs while he is moved. Off: he keeps the pose he lay in."],
    ["ACM Extended", "SKED"], true, 1
] call CBA_fnc_addSetting;
[
    "acme_sked_patientAnim", "EDITBOX",
    ["Casualty pose", "Animation a strapped casualty is held in (lying on the back, arms at the sides)."],
    ["ACM Extended", "SKED"], "ACM_LyingState", 1
] call CBA_fnc_addSetting;
[
    "acme_sked_liftHeight", "SLIDER",
    ["Carry height (m)", "Height of the SKED above the ground while a team carries it."],
    ["ACM Extended", "SKED"], [0.3, 1.0, 0.55, 2], 1
] call CBA_fnc_addSetting;
[
    "acme_sked_hpmkSqueeze", "CHECKBOX",
    ["Squeeze the HPMK-I shell", "A casualty in the HPMK-I gets the squeezed shell while strapped into a SKED."],
    ["ACM Extended", "SKED"], true, 1
] call CBA_fnc_addSetting;
// Calibration: move the casualty in the SKED (SKED axes: X right, Y toward the head, Z up), metres.
{
    [
        format ["acme_sked_offset%1", _x], "SLIDER",
        [format ["Casualty offset %1 (m)", _x], "Fine adjustment of where the casualty lies in the SKED."],
        ["ACM Extended", "SKED"], [-0.3, 0.3, 0, 3], 1
    ] call CBA_fnc_addSetting;
} forEach ["X", "Y", "Z"];
// The carry bag shown slung from the shoulder of whoever has a SKED in their inventory (fn_slungUpdate.sqf).
[
    "acme_sked_slungShow", "CHECKBOX",
    ["Show the slung bag", "Whoever carries a SKED in their inventory wears its bag slung from the right shoulder."],
    ["ACM Extended", "SKED"], true, 1
] call CBA_fnc_addSetting;
[
    "acme_sked_slungRange", "SLIDER",
    ["Slung bag range (m)", "The slung bag is shown on units within this distance of the camera."],
    ["ACM Extended", "SKED"], [50, 1000, 300, 0], 1
] call CBA_fnc_addSetting;
{
    [
        format ["acme_sked_slung%1", _x], "SLIDER",
        [format ["Slung bag offset %1 (m)", _x], "Fine adjustment of where the bag hangs (X right, Y forward, Z up)."],
        ["ACM Extended", "SKED"], [-0.3, 0.3, 0, 3], 1
    ] call CBA_fnc_addSetting;
} forEach ["X", "Y", "Z"];

[
    "acme_sked_debug", "CHECKBOX",
    ["Medical transport diagnostics", "Log transport handoffs to RPT and show the read-only audit in ACE Self Interaction."],
    ["ACM Extended", "SKED"], false, 1
] call CBA_fnc_addSetting;
