// the suction device profile.
// call it as [_type] call ACME_fnc_suctionDevice, which returns a hashmap of everything the screen needs to run
// that device.
// _type is 0 for the suction bag and 1 for the ACCUVAC, which is ACM's own numbering, so it can be passed straight
// through.
// everything that differs between devices lives here and nowhere else. the suction screen reads this and has no
// idea which device it is running: the art path, the frame counts, the anchor it hangs from, how fast it clears
// each fluid, and which sounds it makes. adding the suction bag is filling in the second block rather than
// touching the screen.
// the frame sets a device must provide, using the ACCUVAC naming as the contract:
// clear_nn is the idle loop, with nothing in the lumen.
// cont_k_nn is actively pulling fluid k, which is b, s or v.
// out_k_nn is the lumen clearing after that fluid is gone.
params [["_type", 1, [0]]];
if (_type < 0) exitWith {
    createHashMapFromArray [["name", "Suction"], ["model", "none"], ["item", ""],
        ["tray", ""], ["acmType", -1], ["ready", false]]
};

if (_type == 0) exitWith {
    // the suction bag. it is a different device rather than the ACCUVAC with different pictures, and the profile says
    // which model it is so the screen can behave accordingly.
    // the wand, the ACCUVAC, is a rigid yankauer on a vacuum reservoir. hold the trigger and fluid runs up the lumen.
    // what is animated is the lumen, through cont_, out_ and clear_ frames per fluid type.
    // the bulb, which is this one, is a hand-squeezed bulb feeding a collection bag. there is no reservoir and no
    // trigger: each squeeze moves a fixed volume, and what is animated is the bulb compressing and the bag filling.
    // there are twenty squeeze cycles of twelve frames, plus twenty-one static fill levels.
    // it is 50 ml per squeeze, so a full 1000 ml bag is twenty squeezes. that is why it is slow, and it is slow for the
    // honest reason: there is no vacuum doing the work, only the hand of the medic.
    createHashMapFromArray [
        ["name",        "Suction Bag"],
        ["tray",        "\acm_extended\ui\laryngo\suctionbag\nar_tsd_level_0000_ca.paa"],
        ["model",       "bulb"],
        ["path",        "\acm_extended\ui\laryngo\suctionbag\"],
        // measured off the art, not typed. the tip is the end of the suction catheter, and it is at the same
        // point in all 261 frames, so one anchor serves every fill level and every squeeze frame.
        // the previous value, 0.2680 and 0.1055, was above the artwork entirely. the sprite does not begin until
        // y 0.3101, so the bag hung well below the pointer and the tip was never where the cursor was.
        ["tipUV",       [0.4536, 0.3101]],
        ["scale",       0.62],
        ["aspect",      1],
        ["frameMs",     84],
        ["squeezeSeqs", 20],
        ["squeezeFrames", 12],
        ["levels",      21],
        ["mlPerSqueeze", 50],
        ["capacityMl",  1000],
        ["sfxSqueeze",  "ACME_ManualSuction"],
        ["acmType",     0],
        // the inventory item this device is. everything that asks "is the medic still carrying it" reads this rather
        // than naming a class, because three separate places used to test for an ACCUVAC by name and a medic holding
        // only a suction bag failed all three: the tray showed no device, the grab was refused, and the per-frame
        // check took the tool back out of their hand. the manual suction screen drew nothing at all as a result.
        ["item",        "ACME_SuctionBag"],
        // per squeeze rather than per second: the clearance a single squeeze buys, by fluid type. vomit is thicker, so a
        // squeeze moves less of it.
        // it is tuned so a full mouth takes 12 squeezes of vomit, 9 of blood and 6 of thin secretions: slow enough that the
        // missing vacuum is felt and short of tedious. the wand clears the same mouth in about 5 seconds of held trigger,
        // so the bulb is roughly twice the work, which is the point.
        ["clearPerSqueeze", createHashMapFromArray [["v", 0.083], ["b", 0.111], ["s", 0.167]]],
        ["ready",       true]
    ]
};

// the ACCUVAC. the yankauer set already shipped and measured.
createHashMapFromArray [
    ["name",       "ACCUVAC"],
    ["tray",       "\acm_extended\ui\laryngo\suction\yank_master.paa"],
    ["model",      "wand"],  // a rigid yankauer on a vacuum reservoir: hold the trigger and animate the lumen.
    ["path",       "\acm_extended\ui\laryngo\suction\"],
    ["tipUV",      [0.5703, 0.02539]],
    ["scale",      0.55],
    ["aspect",     2],
    ["frameMs",    110],
    ["clearN",     8],
    ["contN",      8],
    ["outN",       12],
    ["sfxStart",   "ACM_Suction_SoundSource"],
    ["sfxOff",     "ACM_Suction_Off"],
    ["acmType",    1],
    ["item",       "ACME_ACCUVAC"],  // see the note on the bulb profile above.
    ["drainMult",  1],
    ["ready",      true]
]
