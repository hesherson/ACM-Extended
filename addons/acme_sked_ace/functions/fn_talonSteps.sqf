// The steps of the two sequences. ["fold"] or ["unfold"] call acme_sked_fnc_talonSteps
// Returns [steps, seconds in all]. A step is [animation source, phase to reach, seconds, pause after].
//
// These are the authored steps of the litter: the handles go in one by one, the straps come off, the tension
// bars break, the poles come together and turn, the four segments fold over, the straps go round the bundle.
// They are played on the four part models that stand in for the litter (fn_talonTransition.sqf). Change the
// seconds and pauses here to change the pace. The phases are the places where one action ends (a buckle is
// open, a bar is broken, the poles are together), so leave them as they are.
params [["_mode", "fold", [""]]];
if (_mode == "fold") exitWith {
    [[
        ["handles", 0.2600, 0.20, 0.05],    // handle 1 in (foot right)
        ["handles", 0.5000, 0.20, 0.12],    // handle 2 in (foot left)
        ["handles", 0.7600, 0.20, 0.05],    // handle 3 in (head left)
        ["handles", 1.0000, 0.20, 0.15],    // handle 4 in (head right)
        ["fold", 0.0300, 0.35, 0.10],    // first buckle opens
        ["fold", 0.1600, 1.25, 0.30],    // straps go out over the poles, the second buckle opens on the way
        ["fold", 0.1816, 0.35, 0.25],    // foot tension bar breaks
        ["fold", 0.2200, 0.35, 0.25],    // head tension bar breaks
        ["fold", 0.4000, 0.80, 0.20],    // poles pushed together
        ["fold", 0.4900, 0.55, 0.20],    // poles turned
        ["fold", 0.8000, 1.20, 0.25],    // segments folded over
        ["fold", 0.9100, 0.70, 0.20],    // first strap round, clipped, pulled tight
        ["fold", 1.0000, 0.70, 0.20]     // second strap round, clipped, pulled tight
    ], 9.37]
};
[[
    ["fold", 0.9400, 0.40, 0.10],    // second strap unclipped
    ["fold", 0.9100, 0.30, 0.10],    // second strap off
    ["fold", 0.8000, 0.60, 0.25],    // first strap unclipped and off
    ["fold", 0.4900, 1.20, 0.20],    // segments swung open
    ["fold", 0.4000, 0.55, 0.20],    // poles turned back
    ["fold", 0.2200, 0.80, 0.10],    // poles pulled apart
    ["fold", 0.1816, 0.35, 0.25],    // head tension bar pressed straight
    ["fold", 0.1600, 0.35, 0.30],    // foot tension bar pressed straight
    ["fold", 0.0550, 0.90, 0.15],    // second strap back over the deck and clipped
    ["fold", 0.0000, 0.70, 0.30],    // first strap clipped
    ["handles", 0.7400, 0.20, 0.05],    // handle 4 out
    ["handles", 0.5000, 0.20, 0.12],    // handle 3 out
    ["handles", 0.2400, 0.20, 0.05],    // handle 2 out
    ["handles", 0.0000, 0.20, 0.10]     // handle 1 out
], 9.22]
