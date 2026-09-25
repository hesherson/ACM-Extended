// the manual suction bag: squeeze, draw, fill.
// ["tick"] call ACME_fnc_suctionBulb runs every frame while the screen is up.
// ["squeeze"] call ACME_fnc_suctionBulb is one click of the bulb.
// this is the bulb device rather than the ACCUVAC. there is no reservoir and no trigger to hold: each squeeze draws
// a fixed volume, and the work is done by the hand of the medic. it feels like the ACCUVAC in that the tool is on
// the cursor and has to be in the mouth to do anything, and unlike it in that suction happens in discrete pulls.
// the numbers, and why they line up:
// 50 ml per squeeze, read from the profile. the bag art has a frame every 50 ml, so one squeeze advances the bag
// one level and every pull is visible.
// a 1000 ml capacity, so twenty squeezes fill it. full means full: it stops drawing and has to be swapped.
// this used to say 25 ml, forty squeezes, and two squeezes per visible level. the profile has said 50 since it was
// written and the code has always read the profile, so the comment described a version of the device that never
// shipped. the 25 in the getordefault below is a fallback for a profile that omits the value and is not what runs.
// the squeeze animation is chosen by the 50 ml band the bag is currently in, so the bulb compresses against the
// right amount of fluid rather than always replaying the empty-bag cycle.
params ["_mode"];

private _dev = uiNamespace getVariable ["ACME_suction_device", createHashMap];
if ((_dev getOrDefault ["model", "wand"]) isNotEqualTo "bulb") exitWith {};

private _dlg = uiNamespace getVariable ["ACME_laryngo_dlg", displayNull];
if (isNull _dlg) exitWith {};
private _pat = uiNamespace getVariable ["ACME_laryngo_patient", objNull];

private _path = _dev getOrDefault ["path", "\acm_extended\ui\laryngo\suctionbag\"];
private _cap  = _dev getOrDefault ["capacityMl", 1000];
private _per  = _dev getOrDefault ["mlPerSqueeze", 25];
private _nFr  = _dev getOrDefault ["squeezeFrames", 12];
private _fms  = _dev getOrDefault ["frameMs", 84];

private _vol = uiNamespace getVariable ["ACME_suction_bagMl", 0];

// the 50 ml band the bag currently sits in, clamped so a full bag still has a valid band to animate from.
private _fnc_band = {
    params ["_v"];
    private _lo = ((floor (_v / 50)) * 50) min 950;
    [format ["%1", [_lo, 4] call ACME_fnc_zeroPad], format ["%1", [(_lo + 50), 4] call ACME_fnc_zeroPad]]
};

switch (_mode) do {

    // one squeeze.
    case "squeeze": {
        if ((uiNamespace getVariable ["ACME_laryngo_held", ""]) isNotEqualTo "suction") exitWith {};

        // Recheck at input time: a newly carried ACCUVAC takes priority before a bag is spent.
        if (([true] call ACME_fnc_suctionSelectDevice) != 0) exitWith {};
        private _medic = uiNamespace getVariable ["ACME_laryngo_medic", objNull];
        if (isNull _medic || {!local _medic}) exitWith {};
        if !((uiNamespace getVariable ["ACME_suction_bagOwner", []]) isEqualTo [_medic, _pat]) then {
            private _receipt = [_medic, _pat, ["ACM_SuctionBag"]] call ACME_fnc_treatmentSupplyTake;
            if (_receipt isNotEqualTo []) then {
                [_receipt, false] call ACME_fnc_treatmentSupplyRefund;
                uiNamespace setVariable ["ACME_suction_bagOwner", [_medic, _pat]];
            };
        };
        if !((uiNamespace getVariable ["ACME_suction_bagOwner", []]) isEqualTo [_medic, _pat]) exitWith {};
        _medic setVariable ["ACME_suctionManualSession", [_pat, uiNamespace getVariable ["ACME_suctionToken", ""], uiNamespace getVariable ["ACME_suctionBagBase", 0]], true];

        // a full bag draws nothing, because there is nowhere for it to go.
        if (_vol >= _cap) exitWith {
            ["The collection bag is full. It will not draw any more.", 3] call ace_common_fnc_displayTextStructured;
        };

        // already mid-squeeze, so ignore it, and holding the button down does not machine-gun the bulb.
        if ((uiNamespace getVariable ["ACME_suction_sqT0", -1]) >= 0) exitWith {};

        // in the mouth, or nothing happens. it is the same rule as the ACCUVAC: a tool waving next to a face is not
        // suction.
        private _inMouth = uiNamespace getVariable ["ACME_laryngo_sucInMouth", false];

        uiNamespace setVariable ["ACME_suction_sqT0", diag_tickTime];
        uiNamespace setVariable ["ACME_suction_sqBand", ([_vol] call _fnc_band)];
        if (!isNull _pat) then { [_pat, (_dev getOrDefault ["sfxSqueeze", "ACME_ManualSuction"])] remoteExec ["ACME_fnc_remoteSay3D", 0]; };

        if (!_inMouth) exitWith {};

        // the bag only fills if there was something to take. a squeeze into a clear airway moves the bulb and
        // draws air, so the bulb compresses and the collection bag does not change.
        private _kind = uiNamespace getVariable ["ACME_laryngo_fluidKind", ""];
        if (_kind isEqualTo "") exitWith {};

        // it drew: volume into the bag and fluid out of the airway.
        if (_kind isNotEqualTo "") then {
            private _rates = _dev getOrDefault ["clearPerSqueeze", createHashMap];
            private _step  = _rates getOrDefault [_kind, 0.095];
            [(_step * 10) min ((_cap - _vol) / 50)] call ACME_fnc_laryngoFluidDrain;
        };

        // ten seconds of continuous pulling still costs air, exactly as it does with the ACCUVAC. a squeeze is an active
        // pull, so it counts toward the same clock.
        [true] call ACME_fnc_suctionPublish;
    };

    // per frame.
    case "tick": {
        private _c = _dlg displayCtrl 87916;
        if (isNull _c) exitWith {};

        private _t0 = uiNamespace getVariable ["ACME_suction_sqT0", -1];
        private _tex = "";

        if (_t0 >= 0) then {
            // mid-squeeze: run the twelve-frame cycle for the band the bag was in when it started.
            private _el = (diag_tickTime - _t0) * 1000;
            private _fr = (floor (_el / _fms)) + 1;
            if (_fr > _nFr) then {
                uiNamespace setVariable ["ACME_suction_sqT0", -1];
            } else {
                (uiNamespace getVariable ["ACME_suction_sqBand", ["0000","0050"]]) params ["_lo", "_hi"];
                _tex = format ["%1nar_tsd_sq_%2_%3_f%4_ca.paa", _path, _lo, _hi, ([_fr, 2] call ACME_fnc_zeroPad)];
            };
        };

        if (_tex isEqualTo "") then {
            // at rest: the static level nearest the volume actually in the bag, rounded down to a real frame.
            private _lvl = ((floor (_vol / 50)) * 50) min 1000;
            _tex = format ["%1nar_tsd_level_%2_ca.paa", _path, ([_lvl, 4] call ACME_fnc_zeroPad)];
        };

        _c ctrlSetText _tex;
        // and make it visible.
        // fn_laryngoinit sets this control to alpha 0 at open, along with every other instrument sprite, and only
        // the ACCUVAC path in fn_laryngosuction ever turned it back up. the bulb driver set the texture and left
        // the control transparent, so the suction bag was drawn correctly and could not be seen. that is why the
        // manual suction screen looked completely empty.
        _c ctrlSetTextColor [1, 1, 1, 1];
        _c ctrlShow true;

        // off the squeeze, the air clock winds back down.
        if ((uiNamespace getVariable ["ACME_suction_sqT0", -1]) < 0 && {!isNull _pat}) then {
            [] call ACME_fnc_suctionPublish;
        };
    };
};
