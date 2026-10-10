/* Keep the visual pass after every procedural early return. */
private _acmeNVArgs = if (isNil "_this") then {[]} else {_this};
_acmeNVArgs call {
// the iv mini-game per-frame tick. it is a freeform skill check, with no step-by-step guidance.
// with the band held, the full-size art sits on the cursor, with a weak snap only when nearly on a site.
// with the pad held, the pad follows the cursor, and while wiping, with lmb held, over the site it shrinks small
// and follows the wipe. Coverage marks the site clean without putting the pad down.
// with the needle held, the full-size catheter sits on the cursor, tip at the cursor, and there is no feel dot.
// the stick is blind, so you must remember where you felt the vein. clicking commits the stick, which
// fn_ivminigameclick handles.
// with nothing held and lmb held, the palpating finger shows and runs red, then yellow, then green near the vein.
// A BOA improves venous filling but is not required. Pressure and the band/site relationship determine how much
// vein can actually be felt. It never locks or finds, so palpate as you like.
// the held item routes through the dynamic ACME_IV_HeldCursor sprite, so it always draws above the buttons.
private _display = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (isNull _display) exitWith {};
if !([] call ACME_fnc_ivUiValid) exitWith {_display closeDisplay 2;};

// Update band presence before any held-tool or insertion early return.
[] call ACME_fnc_ivMinigameSyncBand;

// somebody else worked this limb.
// every write of the marks bumps ACME_IV_MarkVer and records the version locally, so a version on the patient
// that no longer matches ours means another medic stuck or pulled a line here. re-render from the authoritative
// marks rather than from our own copy.
// it runs every tick, so it lands within a frame of the other medic's click instead of on a reopen. our own
// writes record the version as they make it, so they never read as remote and the screen does not rebuild in a
// loop.
private _ivPat = uiNamespace getVariable ["ACME_IV_Patient", objNull];
if (!isNull _ivPat) then {
    private _needMarkRender = false;
    private _mv = _ivPat getVariable ["ACME_IV_MarkVer", 0];
    if (_mv != (uiNamespace getVariable ["ACME_IV_MarkVerSeen", -1])) then {
        uiNamespace setVariable ["ACME_IV_MarkVerSeen", _mv];
        _needMarkRender = true;
    };

    // Medical injury state can change without an IV mark being added or removed.  Repaint the trauma layer when
    // ACE contusions or the site-specific extravasation severity changes, otherwise the visual can lag behind the
    // actual patient until the medic places another catheter or re-opens the minigame.
    private _visBP = uiNamespace getVariable ["ACME_IV_BodyPart", ""];
    private _visualSig = str [
        netId _ivPat,
        [_ivPat, _visBP] call ACME_fnc_visualBruiseState,
        [_ivPat, _visBP] call ACME_fnc_ivExtravasationState
    ];
    if (_visualSig != (uiNamespace getVariable ["ACME_IV_TraumaSig", ""])) then {
        uiNamespace setVariable ["ACME_IV_TraumaSig", _visualSig];
        _needMarkRender = true;
    };

    if (_needMarkRender) then {call ACME_fnc_ivMinigameRenderMarks;};
};
// vehicle motion.
// the limb moves under the needle. it is applied before hit-testing, so the vein you palpated a second ago is not
// where you left it. cannulating in a moving vehicle is hard, and cannulating in a banking aircraft is close to
// futile. that is the lesson, and it is why you get access before you launch.
private _ivBase = uiNamespace getVariable ["ACME_IV_BodyRectBase", []];
if (count _ivBase >= 4) then {
    // shake the entire panel rather than only the limb. moving only the casualty image was never going to feel like
    // turbulence, because the slots, the buttons and the marks all stayed nailed to the screen while the arm alone
    // drifted a few pixels. you do not notice a body move under a stationary ui. you notice the world move.
    ([_display, "ACME_IV_ShakeBase"] call ACME_fnc_uiShakeApply) params ["_ivdx", "_ivdy"];
    _ivBase params ["_ibx", "_iby", "_ibw", "_ibh"];
    // keep the body rect in step with the picture, so the vein, the hit-testing, the placed hubs and the bruises all
    // ride along with the limb they belong to. only your mouse stays still, and that is what makes it hard.
    uiNamespace setVariable ["ACME_IV_BodyRect", [_ibx + _ivdx, _iby + _ivdy, _ibw, _ibh]];
};

[] call ACME_fnc_ivFinishTick;
[] call ACME_fnc_ivFieldProgress;

// the darkness is drawn first, before any branch can bail out.
// this used to be the last line of this function, below thirteen exitwith branches for the held item, dragging,
// the mode, palpating and more. so in most states the tick returned long before it ever got here, and the screen
// only went dark once you clicked something and the state happened to fall all the way through. that is a
// control-flow bug rather than a lighting one, and it is why you could see everything until you touched the
// panel.

private _rect = uiNamespace getVariable ["ACME_IV_BodyRect", []];
if (_rect isEqualTo []) exitWith {};
_rect params ["_bx", "_by", "_bw", "_bh"];
private _af = uiNamespace getVariable ["ACME_IV_AspectFix", 0.5625];

private _held    = uiNamespace getVariable ["ACME_IV_Held", "none"];
private _drag    = uiNamespace getVariable ["ACME_IV_Dragging", false];
private _dot     = uiNamespace getVariable ["ACME_IV_DotCtrl", controlNull];
// keep the instrument in the hand above the dabs, the marks and the bruises. ctrlCreate appends above every
// existing control, so anything created while the screen is open buries the held sprite. this runs before the
// handle is read, so the rest of the tick paints into the control that is actually on top.
[] call ACME_fnc_ivHeldRaise;
private _heldC   = uiNamespace getVariable ["ACME_IV_HeldCursorCtrl", controlNull];

private _finite = { params ["_v"]; (_v isEqualType 0) && {finite _v} };
private _now = diag_tickTime;

// the antiseptic scrub trail ages out on TIME. it holds at full for a dwell, then fades over a window, then
// the control is deleted. it is deliberately NOT cleared by putting the pad down or by taking the band off:
// antiseptic on skin dries, it does not vanish because you changed tool.
private _prep = uiNamespace getVariable ["ACME_IV_PrepCtrls", []];
if !(_prep isEqualTo []) then {
    private _hold = missionNamespace getVariable ["ACME_iv_prepHoldSec", 45];
    private _fade = missionNamespace getVariable ["ACME_iv_prepFadeSec", 40];
    private _a0 = missionNamespace getVariable ["ACME_iv_prepDabAlpha", 0.085];
    private _tint = missionNamespace getVariable ["ACME_iv_prepTint", [0.80, 0.42, 0.40]];
    private _keep = [];
    {
        private _pc = _x param [0, controlNull];
        private _pt = _x param [1, -1];
        // Each non-overlapping cell stores its coverage opacity. Drying scales
        // that coverage instead of adding overlapping red circles.
        private _pa = _x param [2, _a0];
        if (!isNull _pc) then {
            private _age = _now - _pt;
            if (_pt < 0 || {_age < _hold}) then {
                _keep pushBack _x;
            } else {
                private _k = 1 - ((_age - _hold) / (_fade max 0.1));
                if (_k <= 0) then {
                    ctrlDelete _pc;
                } else {
                    _pc ctrlSetTextColor [(_tint select 0), (_tint select 1), (_tint select 2), _pa * _k];
                    _pc ctrlCommit 0;
                    _keep pushBack _x;
                };
            };
        };
    } forEach _prep;
    if ((count _keep) != (count _prep)) then { uiNamespace setVariable ["ACME_IV_PrepCtrls", _keep]; };
};

// the fading antiseptic stain, independent of what is held.
// ACME_IV_CleanCtrl is no longer created: fn_ivMinigameCleanDone stopped stamping a single circle when the pad
// started painting a real scrub trail. this block is kept because a saved state from before that change can
// still restore one, and it costs an isNull check per frame.
private _clean = uiNamespace getVariable ["ACME_IV_CleanCtrl", controlNull];
if (!isNull _clean) then {
    private _ct = uiNamespace getVariable ["ACME_IV_CleanTime", -1];
    if ([_ct] call _finite && {_ct > 0}) then {
        private _age = _now - _ct;
        if (_age >= 30) then {
            _clean ctrlShow false;
        } else {
            private _a = 0.30 * (1 - (_age / 30));
            _clean ctrlSetTextColor (["danger", (_a max 0)] call ACME_fnc_a11yColor);
            _clean ctrlCommit 0;
        };
    };
};

// the fading miss-site bruises, independent of what is held. they develop over the configured few seconds, then hold.
{
    _x params ["_bc", "_bt"];
    if (!isNull _bc && {[_bt] call _finite} && {_bt >= 0}) then {
        // Miss marks are stamped with shared serverTime so every observer sees the same bruise age. Keep this
        // per-frame fade on that same clock. Mixing CBA_missionTime here made fresh remote marks look old and
        // jump straight to full opacity on clients whose local CBA clock differed from the shared stamp.
        private _e = serverTime - _bt;
        private _cap = (missionNamespace getVariable ["ACME_iv_bruiseMaxAlpha", 0.90]);
        if (!(_cap isEqualType 0) || {!finite _cap}) then { _cap = 0.90 };
        _cap = (_cap max 0.05) min 1;
        private _life = missionNamespace getVariable ["ACME_iv_bruiseLifeSec", 1200];
        private _out  = missionNamespace getVariable ["ACME_iv_bruiseFadeOutSec", 300];
        private _fadeIn = (missionNamespace getVariable ["ACME_iv_bruiseFadeInSec", 5.0]) max 0.1;
        private _al = switch (true) do {
            case (_e < 0):              { 0 };
            case (_e < _fadeIn):        { (_e / _fadeIn) * _cap };
            case (_e < (_life - _out)): { _cap };
            case (_e < _life):          { _cap * (((_life - _e) / (_out max 1)) max 0) };
            default                     { 0 };
        };
        _bc ctrlSetTextColor [1, 1, 1, _al];
        _bc ctrlCommit 0;
        // THE VISIBILITY IS SET BOTH WAYS, NOT HIDDEN ONE WAY.
        // this used to be a bare hide when the alpha reached the floor, with nothing anywhere to show the control
        // again. a bruise is created at the START of its configured fade in, so its alpha is about zero on the frame it
        // appears, and this loop hid it on that first frame and left it hidden for good. it came back only when
        // fn_ivMinigameRenderMarks ran again and rebuilt the sprite, which is why placing a new IV made every
        // existing bruise appear at once.
        // the hide is still wanted at the far end, where a bruise has resolved after its twenty minutes, so the
        // test stays and only the direction is completed.
        _bc ctrlShow (_al > 0.004);
    };
} forEach (uiNamespace getVariable ["ACME_IV_BruiseFades", []]);

// A worsening infiltration/extravasation does not pop to the next image.  Both severity sprites are kept alive
// for ten seconds and their opacity is blended here every frame.  Once the blend completes the old control is
// deleted and the state is collapsed to the new severity so future repaints do not restart the transition.
private _exFades = uiNamespace getVariable ["ACME_IV_ExtravasationFades", []];
if !(_exFades isEqualTo []) then {
    private _keepEx = [];
    private _exState = uiNamespace getVariable ["ACME_IV_ExtravasationVisualState", createHashMap];
    {
        _x params ["_oldCtrl", "_newCtrl", "_started", ["_cap", 0.86], ["_key", ""], ["_target", 1], ["_duration", 10]];
        _duration = _duration max 0.1;
        private _t = ((CBA_missionTime - _started) / _duration) max 0 min 1;
        if (!isNull _oldCtrl) then {
            _oldCtrl ctrlSetTextColor [1,1,1,_cap * (1 - _t)];
            _oldCtrl ctrlShow (_t < 0.996);
            _oldCtrl ctrlCommit 0;
        };
        if (!isNull _newCtrl) then {
            _newCtrl ctrlSetTextColor [1,1,1,_cap * _t];
            _newCtrl ctrlShow (_t > 0.004);
            _newCtrl ctrlCommit 0;
        };
        if (_t >= 1) then {
            if (!isNull _oldCtrl) then {ctrlDelete _oldCtrl;};
            if (_key != "") then {_exState set [_key, [_target, -1, -1]];};
        } else {
            _keepEx pushBack _x;
        };
    } forEach _exFades;
    uiNamespace setVariable ["ACME_IV_ExtravasationFades", _keepEx];
    uiNamespace setVariable ["ACME_IV_ExtravasationVisualState", _exState];
};

private _ui = call ACME_fnc_ivMinigameCursor;
if (_ui isEqualTo []) exitWith {};
_ui params ["_ux", "_uy"];
if !(([_ux] call _finite) && {[_uy] call _finite}) exitWith {};
private _fx = (_ux - _bx) / _bw;
private _fy = (_uy - _by) / _bh;
private _probeBP = uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"];
private _probeView = uiNamespace getVariable ["ACME_IV_View", ""];
private _artBounds = [_probeBP, _probeView, _fy] call ACME_fnc_ivLimbBounds;
private _onPatientArt = false;
if (count _artBounds == 2) then {
    _onPatientArt = _fx >= (_artBounds select 0) && {_fx <= (_artBounds select 1)};
};

// On a limb the vein under the finger is selected by the finger's location, not by the BOA. This is what makes
// an unbanded stick possible and what lets a mid-arm/AC band still expose a weaker distal wrist target. The band
// site remains ACME_IV_Site; ACME_IV_ProbeSite is only the site currently being examined/stuck.
if (!(uiNamespace getVariable ["ACME_IV_EJMode", false]) && {_onPatientArt}) then {
    private _probeSite = [_fx, _fy] call ACME_fnc_ivSiteAtPoint;
    if (_probeSite in ["upper", "middle", "lower"]) then {
        uiNamespace setVariable ["ACME_IV_ProbeSite", _probeSite];
        private _probeData = [_probeBP, _probeSite] call ACME_fnc_ivSiteData;
        if (count _probeData >= 6 && {(_probeData select 0) == _probeView}) then {
            private _pU = _probeData select 4;
            private _pV = _probeData select 5;
            uiNamespace setVariable ["ACME_IV_VeinUV", [_pU, _pV]];
            uiNamespace setVariable ["ACME_IV_VeinSet",
                [(uiNamespace getVariable ["ACME_IV_Patient", objNull]), _probeBP, _probeSite, _pU, _pV] call ACME_fnc_ivVeinSet];
        };
    };
};

// ej: two fixed sites either side of the throat, with no band. pick the jugular nearest the cursor each frame and
// make it the active stick target, so the palpation and the stick track whichever side you reach for.
// screen-right is the patient's left.
if (uiNamespace getVariable ["ACME_IV_EJMode", false]) then {
    private _vL = uiNamespace getVariable ["ACME_IV_EJVeinL", [0.560, 0.505]];
    private _vR = uiNamespace getVariable ["ACME_IV_EJVeinR", [0.440, 0.505]];
    private _dL = (abs (_fx - (_vL select 0))) + (abs (_fy - (_vL select 1)));
    private _dR = (abs (_fx - (_vR select 0))) + (abs (_fy - (_vR select 1)));
    private _nearL = (_dL <= _dR);  // the cursor is nearest the patient-left vein, which is screen-right.
    uiNamespace setVariable ["ACME_IV_VeinUV", ([_vR, _vL] select _nearL)];
    // Registration and the main-menu overlay always use the anatomical side.
    // The corrected EJ family is named for the tip direction; the artwork points down
    // toward the chest, unlike the upward-pointing limb catheter artwork.
    uiNamespace setVariable ["ACME_IV_EJAnatomicalSide", (["right", "left"] select _nearL)];
    uiNamespace setVariable ["ACME_IV_EJSide", (["right", "left"] select _nearL)];
};

// the distance to the vein strip, plus the color ramp of the palpating finger, from red through yellow to
// green.
// the nearest of the candidate veins at this site, not a single fixed strip. outside the antecubital fossa
// the set holds exactly one entry and this behaves identically to the old single-strip code.
// the winning vein is published so the stick, the caption and the log all agree about which vessel was under
// the finger, rather than each working it out again.
private _near = [_fx, _fy] call ACME_fnc_ivVeinNearest;
_near params ["_distV", "_nvU", "_nvV", "_nvQ", "_nvName"];
if (_distV < 1e8) then {
    uiNamespace setVariable ["ACME_IV_VeinUV", [_nvU, _nvV]];
    uiNamespace setVariable ["ACME_IV_NearVein", _nvName];
    uiNamespace setVariable ["ACME_IV_NearQuality", _nvQ];
} else {
    // no candidate set. the external jugular takes this path: its two veins are resolved by the EJ block
    // higher up in this file, which has already written ACME_IV_VeinUV, so measuring against that single
    // strip is exactly right and is what shipped before. without this fallback the EJ dot would never warm.
    _distV = [_fx, _fy] call ACME_fnc_ivVeinDist;
    _nvQ = 1;
};
// Recompute palpability from live MAP/SBP every frame. A selected BOA changes the returned values, but no BOA is
// a valid state. The nearest anatomical site owns the difficulty, so a wrist palpated below an AC band receives
// the smaller distal-band benefit rather than the AC-fossa value.
private _diffSite = if (uiNamespace getVariable ["ACME_IV_EJMode", false]) then {
    uiNamespace getVariable ["ACME_IV_EJAnatomicalSide", "left"]
} else {
    uiNamespace getVariable ["ACME_IV_ProbeSite", uiNamespace getVariable ["ACME_IV_Site", "middle"]]
};
private _liveDiff = [uiNamespace getVariable ["ACME_IV_Patient", objNull], _probeBP,
    uiNamespace getVariable ["ACME_IV_Gauge", 16], _diffSite] call ACME_fnc_ivSiteDifficulty;
_liveDiff params ["_livePatency", "_feelRadius", "_hitRadius", "_maxHot"];
uiNamespace setVariable ["ACME_IV_Patency", _livePatency];
uiNamespace setVariable ["ACME_IV_FeelRadius", _feelRadius];
uiNamespace setVariable ["ACME_IV_HitRadius", _hitRadius];
uiNamespace setVariable ["ACME_IV_MaxHot", _maxHot];
private _palp = [_distV, _feelRadius, _hitRadius, _maxHot, _nvQ,
                 (uiNamespace getVariable ["ACME_IV_Patient", objNull])] call ACME_fnc_ivPalpModel;
_palp params ["_dotCol", "_dotSize", "_onVein"];
uiNamespace setVariable ["ACME_IV_DotSize", _dotSize];

// a catheter is being pulled out. it owns the pointer and the sprite until it is out or let go.
if ((uiNamespace getVariable ["ACME_IV_PullIdx", -1]) >= 0) exitWith {
    if (!isNull _heldC) then { _heldC ctrlShow false; };
    [_drag] call ACME_fnc_ivMinigamePullTick;
};

// an insertion is under way. the catheter is locked to the puncture and the drag drives it, so every other held
// item branch is skipped.
private _insStage = uiNamespace getVariable ["ACME_IV_InsStage", ""];
if (_insStage in ["advance", "thread", "retract"]) exitWith {
    if (!isNull _heldC) then { _heldC ctrlShow false; };
    if (_insStage == "advance") then { [_drag] call ACME_fnc_ivMinigameInsertAdvance; };
};

// holding the tubing: the floating line sits on the cursor by its connector, which is the end that plugs into
// the hub. it uses the orientation of the catheter it is going onto.
if (_display getVariable ["ACME_IV_FinishBusy",false]) exitWith {
    if (!isNull _heldC) then {_heldC ctrlShow false;};
    if (!isNull _dot) then {_dot ctrlShow false;};
};
if (_held in ["extension","flush","dressing","line","lock"]) exitWith {
    [_heldC,_held,[] call ACME_fnc_ivMinigameCursor] call ACME_fnc_ivFinishPreview;
    if (!isNull _dot) then {_dot ctrlShow false;};
};
if (_held == "line") exitWith {
    if (!isNull _dot) then { _dot ctrlShow false; };
    if (isNull _heldC) exitWith {};
    // a line in hand with no bare hub to plug it into is a state nothing should be able to produce. drop it
    // rather than draw tubing on the cursor that cannot go anywhere.
    private _lp = uiNamespace getVariable ["ACME_IV_Patient", objNull];
    private _bare = false;
    if (!isNull _lp) then {
        private _lbp = uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"];
        private _lview = uiNamespace getVariable ["ACME_IV_View", ""];
        {
            _x params ["_mbp", "_mview", "_mu", "_mv", "_mkind", ["_mtex", ""]];
            if (_mbp == _lbp && {_mview == _lview} && {_mkind == "hub"} && {_mtex == ""}) exitWith { _bare = true; };
        } forEach (_lp getVariable ["ACME_IV_Marks", []]);
    };
    if (!_bare) exitWith {
        uiNamespace setVariable ["ACME_IV_Held", "none"];
        _heldC ctrlShow false;
    };
    private _lf = uiNamespace getVariable ["ACME_IV_InsSuffix", ""];
    private _ldir = if (_lf == "") then { "base" } else { _lf select [1] };
    private _lanc = (uiNamespace getVariable ["ACME_IV_LineAnchors", createHashMap]) getOrDefault [_lf, [0.49246, 0.50391]];
    private _lcs = uiNamespace getVariable ["ACME_IV_CathScale", 0.62];
    _heldC ctrlSetText (format ["\acm_extended\ui\iv\iv_line\standalone\%1\iv_line_floating_%1_ca.paa", _ldir]);
    [_heldC, _ux, _uy, _lf, uiNamespace getVariable ["ACME_IV_InsAngle", 0], _lcs, _lanc] call ACME_fnc_ivCathPose;
    _heldC ctrlShow true;
};

// band held: the art on the cursor, with a weak snap.
if (_held == "band") exitWith {
    if (!isNull _dot) then { _dot ctrlShow false; };
    if (isNull _heldC) exitWith {};
    private _snaps = uiNamespace getVariable ["ACME_IV_SnapSites", []];
    // CAUTION: Do not exit here on an empty snap set. That code made the band disappear.
    // The snap set is empty when every location on this face of the limb holds an IV.
    // The medic clicks the BAND slot. fn_ivMinigameGrabBand sets Held to "band".
    // fn_ivMinigameRefreshBandSlot then clears the tray logo, because the band is in the hand.
    // The tick exited at this line before. It drew nothing on the cursor.
    // The band was not in the tray and not on the cursor. The medic could not see the band.
    // There is no early exit now. An empty set continues to the else branch below.
    // That branch clears the snap and draws the loose BOA on the cursor.
    // Therefore the medic always sees the band.
    // The clear of ACME_IV_SnapActive is necessary on its own.
    // The old exit kept the value from an earlier view or site.
    // fn_ivMinigameClick applies the band from that value.
    // An old snap could put a band at a location outside the snap set, or at an occupied location.
    private _best = []; private _bestD = 1e9;
    {
        _x params ["_sName", "_sbU", "_sbV", "_svU", "_svV", "_slbl", "_sBandTex"];
        private _dx = (_fx - _sbU); private _dy = (_fy - _sbV) * (1 / _af);
        private _d = sqrt ((_dx * _dx) + (_dy * _dy));
        if (_d < _bestD) then { _bestD = _d; _best = _x; };
    } forEach _snaps;
    private _snapR = 0.045;
    if (!(_best isEqualTo []) && {_bestD <= _snapR}) then {
        _best params ["_sName", "_sbU", "_sbV", "_svU", "_svV", "_slbl", "_sBandTex"];
        uiNamespace setVariable ["ACME_IV_SnapActive", _best];
        _heldC ctrlSetText _sBandTex;
        _heldC ctrlSetPosition [_bx, _by, _bw, _bh];
    } else {
        uiNamespace setVariable ["ACME_IV_SnapActive", []];
        private _r = _bh * 0.16;
        _heldC ctrlSetText "\acm_extended\ui\nar_boa_ca.paa";
        _heldC ctrlSetPosition [_ux - (_r / 2), _uy - (_r * 0.5) / _af, _r, _r / _af];
    };
    _heldC ctrlSetAngle [0, 0.5, 0.5, false];  // shared control. see the note in the line branch.
    _heldC ctrlCommit 0;
    _heldC ctrlShow true;
};

// pad held: YOU scrub the site. the pad follows the cursor exactly and paints an antiseptic mark under it.
// the old behavior shrank the pad, wobbled it on a sine wave, counted three left-right swipes for you and then
// stamped one red mark at the end. that is not scrubbing, it is holding a button while an animation plays. the
// wobble is gone, the swipe counter is gone, and the site is clean when you have actually covered it.
if (_held == "pad") exitWith {
    if (!isNull _dot) then { _dot ctrlShow false; };
    if (isNull _heldC) exitWith {};
    private _cleanR = 0.11;

    // THE PAD HAS WEIGHT AND IT COMPRESSES.
    // it used to sit welded to the pointer at a fixed size. a swab held against skin does two things: it squashes
    // under the hand, and it trails the hand rather than teleporting with it.
    // the lag is the same exponential integration fn_ivNeedleTip uses for the catheter, so one long frame cannot
    // overshoot, and the SAME settled point is what gets painted. the mark has to land under the pad, not under
    // the cursor, or the trail runs ahead of the thing making it.
    private _dt = diag_deltaTime;
    if (_dt <= 0) then { _dt = 0.02 };
    private _pp = uiNamespace getVariable ["ACME_IV_PadPos", []];
    if (count _pp < 2) then { _pp = [_ux, _uy]; };
    _pp params ["_ppx", "_ppy"];
    private _lf = 1 - (exp (-((missionNamespace getVariable ["ACME_iv_padLag", 16]) * _dt)));
    private _padX = _ppx + ((_ux - _ppx) * _lf);
    private _padY = _ppy + ((_uy - _ppy) * _lf);
    uiNamespace setVariable ["ACME_IV_PadPos", [_padX, _padY]];

    // the press. it eases toward the squashed size while the button is down and back out when it is released,
    // so it is a squash rather than a snap between two sizes.
    private _pressT = uiNamespace getVariable ["ACME_IV_PadPress", 0];
    if (!(_pressT isEqualType 0) || {!finite _pressT}) then { _pressT = 0 };
    private _pf = 1 - (exp (-((missionNamespace getVariable ["ACME_iv_padPressRate", 12]) * _dt)));
    _pressT = _pressT + (((([0, 1] select _drag)) - _pressT) * _pf);
    uiNamespace setVariable ["ACME_IV_PadPress", _pressT];
    private _squash = missionNamespace getVariable ["ACME_iv_padPressScale", 0.78];
    private _r = _bh * 0.16 * (1 - ((1 - _squash) * _pressT));

    // the lean. the pad tips into the direction it is being dragged, by how far it is trailing the hand. it is
    // the lag distance doing double duty, so a slow wipe barely leans and a fast scrub swings.
    // set ACME_iv_padTiltDeg to 0 to keep the pad upright and keep the lag and the squash.
    private _tiltMax = missionNamespace getVariable ["ACME_iv_padTiltDeg", 22];
    private _tiltSpan = missionNamespace getVariable ["ACME_iv_padTiltSpan", 0.030];
    private _lagX = _ux - _padX;
    private _tilt = 0;
    if (_tiltSpan > 0) then { _tilt = ((_lagX / _tiltSpan) max -1 min 1) * _tiltMax; };

    // the paint and the coverage test both use the settled pad point, in body fractions.
    private _pfx = if (_bw > 0) then { (_padX - _bx) / _bw } else { _fx };
    private _pfy = if (_bh > 0) then { (_padY - _by) / _bh } else { _fy };
    private _pdv = [_pfx, _pfy] call ACME_fnc_ivVeinDist;
    private _overSite = _pdv <= _cleanR;
    if (_drag && {_overSite}) then {
        uiNamespace setVariable ["ACME_IV_CleanAt", [_pfx, _pfy]];
        private _n = [_pfx, _pfy] call ACME_fnc_ivPrepPaint;
        // covered enough. the threshold is a count of marks laid, and because a mark is only laid after the
        // cursor has MOVED a set distance, it cannot be satisfied by holding still. scrubbing is the only way
        // to reach it, which is the whole point of the change.
        private _need = missionNamespace getVariable ["ACME_iv_prepMarksToClean", 16];
        if (_n >= _need && {!(uiNamespace getVariable ["ACME_IV_Cleaned", false])}) then {
            [] call ACME_fnc_ivMinigameCleanDone;
        };
    } else {
        // let go, or wandered off the site, and the next dab starts a fresh stroke rather than drawing a long
        // line back to wherever the cursor reappeared.
        uiNamespace setVariable ["ACME_IV_PrepLast", []];
    };
    _heldC ctrlSetText (uiNamespace getVariable ["ACME_IV_PadTex", "\acm_extended\ui\iv\alcohol_pad_left_ca.paa"]);
    _heldC ctrlSetPosition [_padX - (_r / 2), _padY - (_r * 0.5) / _af, _r, _r / _af];
    // the order is position, then angle, then commit. that is what fn_laryngoTubePose does and it is the only
    // ordering in this addon that is known to render.
    _heldC ctrlSetAngle [_tilt, 0.5, 0.5, false];
    _heldC ctrlCommit 0;
    _heldC ctrlShow true;
};

// needle held: the full-size catheter on the cursor, tip at the cursor, with no feel dot, so it is a blind
// stick.
if (_held == "needle") exitWith {
    if ([_heldC,[] call ACME_fnc_ivMinigameCursor] call ACME_fnc_ivFieldPreview) exitWith {};
    if (!isNull _dot) then { _dot ctrlShow false; };
    if (isNull _heldC) exitWith {};
    // Anatomical side selects one authored 15-degree family for the entire approach.
    // Limb filenames describe the TIP: _15_left has its handle leaning screen-right,
    // along the patient's resting left arm/leg; _15_right leans screen-left on the right.
    // EJ points down: its handle lean therefore needs the opposite named family.
    // Crossing a limb's centre changes only the physical angle, never the texture family.
    private _bpT = uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"];
    private _isEJ = uiNamespace getVariable ["ACME_IV_EJMode", false];
    private _patientLeft = if (_isEJ) then {
        (uiNamespace getVariable ["ACME_IV_EJAnatomicalSide", "left"]) == "left"
    } else {_bpT in ["leftarm", "leftleg"]};
    private _artSide = if (_patientLeft) then {"left"} else {"right"};
    if (_isEJ) then {_artSide = if (_patientLeft) then {"right"} else {"left"};};
    // Flipping an arm to its posterior face mirrors its resting 15-degree approach on screen. Use the opposite
    // authored family on the rear face so the catheter does not keep leaning the front-view direction.
    private _viewNow = toLower (uiNamespace getVariable ["ACME_IV_View", ""]);
    if (!_isEJ && {_bpT in ["leftarm","rightarm"]} && {_viewNow find "_rear" >= 0}) then {
        _artSide = if (_artSide == "left") then {"right"} else {"left"};
    };
    private _frame = format [if (_isEJ) then {"_ej_15_%1"} else {"_15_%1"}, _artSide];
    private _displayAngle = 0;
    private _onBody = (_fx >= 0) && {_fx <= 1} && {_fy >= 0} && {_fy <= 1};
    if (_isEJ) then {
        private _vein = uiNamespace getVariable ["ACME_IV_VeinUV", [0.5,0.125]];
        private _span = (((_fx - (_vein select 0)) / 0.055) max -1) min 1;
        // Neck approaches rotate opposite the limb convention. Keep each side's
        // authored family while mirroring its physical motion across the neck.
        _displayAngle = _span * (missionNamespace getVariable ["ACME_iv_ejTiltDeg", 15]);
    } else {
        if (_onBody) then {
            private _sdAngle = [_bpT, uiNamespace getVariable ["ACME_IV_Site", ""]] call ACME_fnc_ivSiteData;
            private _edgeLeft = _sdAngle param [8, -1];
            private _edgeRight = _sdAngle param [9, -1];
            // The right arm slopes across its canvas. Read its outline at the
            // pointer's height instead of reusing the selected band's midpoint.
            private _tiltView = uiNamespace getVariable ["ACME_IV_View", _sdAngle param [0, ""]];
            // Preserve the established catheter-angle model. Only the patient right arm needed row-specific
            // correction for its strongly sloped canvas; the expanded ivLimbBounds profiles are also used as
            // puncture hit masks, but must not silently retune the other authored limb angles.
            if (_bpT == "rightarm") then {
                private _rowBounds = [_bpT, _tiltView, _fy] call ACME_fnc_ivLimbBounds;
                if (count _rowBounds == 2) then {
                    _edgeLeft = _rowBounds select 0;
                    _edgeRight = _rowBounds select 1;
                };
            };
            private _refU = _sdAngle param [7, missionNamespace getVariable ["ACME_iv_tiltRefU", 0.5]];
            if ((_edgeLeft isEqualType 0) && {finite _edgeLeft} && {_edgeRight isEqualType 0} && {finite _edgeRight} && {_edgeRight > _edgeLeft}) then {
                _refU = (_edgeLeft + _edgeRight) * 0.5;
            };
            if !(_refU isEqualType 0 && {finite _refU}) then {_refU = 0.5;};
            private _dxn = _fx - _refU;
            private _halfWidth = if (_dxn < 0) then {_refU - _edgeLeft} else {_edgeRight - _refU};
            if !(_halfWidth isEqualType 0 && {finite _halfWidth} && {_halfWidth > 0.005}) then {_halfWidth = 0.050;};
            private _span01 = ((abs _dxn / _halfWidth) max 0) min 1;
            // Pixel-space clockwise rotation: the left limb's screen-right edge
            // adds -15 to _15_left, and the right limb's screen-left edge adds +15
            // to _15_right. The authored resting 15 therefore extends to nominal 30.
            private _sign = if (_dxn > 0) then {-1} else {1};
            if (_bpT in ["leftarm", "rightarm"]) then {
                private _edgeFrac = linearConversion [missionNamespace getVariable ["ACME_iv_armEdgeStart", 0.60], missionNamespace getVariable ["ACME_iv_armEdgeFull", 0.90], _span01, 0, 1, true];
                _displayAngle = _sign * (missionNamespace getVariable ["ACME_iv_armEdgeExtraTiltDeg", 15]) * _edgeFrac;
            } else {
                private _legFrac = linearConversion [missionNamespace getVariable ["ACME_iv_legTiltStart", 0.10], missionNamespace getVariable ["ACME_iv_legTiltFull", 0.74], _span01, 0, 1, true];
                _displayAngle = _sign * (missionNamespace getVariable ["ACME_iv_legTiltDeg", 15]) * _legFrac;
            };
        };
    };
    uiNamespace setVariable ["ACME_IV_NeedleFrame", _frame];
    // The bevel itself is the aiming cursor. Keep the authored catheter anchored so the VERY TIP of the steel
    // sits on the pointer every frame; do not add spring-lag or tremor between the cursor and the puncture point.
    private _tipX = _ux;
    private _tipY = _uy;
    uiNamespace setVariable ["ACME_IV_NeedleTipPos", [_tipX,_tipY]];
    // frame 00 is the ready pose, with the bevel held just off the skin. the anchor is the insertion plane, so the
    // tip draws a little short of the cursor until the stick starts.
    _heldC ctrlSetText ([uiNamespace getVariable ["ACME_IV_Gauge", 16], _frame, 0] call ACME_fnc_ivCathTex);
    // give the held catheter a little hand-weight without any press-size change. the approach angle above stays
    // modest on purpose, because the authored sprite already carries the main orientation.
    private _motionTilt = 0;
    private _motionSpan = missionNamespace getVariable ["ACME_iv_needleMotionTiltSpan", 0.020];
    if ((_motionSpan isEqualType 0) && {finite _motionSpan} && {_motionSpan > 0}) then {
        private _motionNorm = ((((_ux - _tipX) / _motionSpan) max -1) min 1);
        _motionTilt = _motionNorm * (missionNamespace getVariable ["ACME_iv_needleMotionTiltDeg", 4]);
        if (_isEJ) then {_motionTilt = -_motionTilt;};
    };
    // Include hand-lag in the cap, so it cannot push a 30-degree outer approach to 34.
    private _angle = ((_displayAngle + _motionTilt) max -15) min 15;
    uiNamespace setVariable ["ACME_IV_NeedleAngle", _angle];
    ([_heldC, _tipX, _tipY, _frame, _angle] call ACME_fnc_ivCathPose) params ["_hx", "_hy"];
    _heldC ctrlShow true;
    // the body fractions of the real tip, for the hit test.
    private _tfx = if (_bw > 0) then { (_tipX - _bx) / _bw } else { _fx };
    private _tfy = if (_bh > 0) then { (_tipY - _by) / _bh } else { _fy };
    uiNamespace setVariable ["ACME_IV_NeedleTipUV", [_tfx, _tfy, diag_tickTime]];
    uiNamespace setVariable ["ACME_IV_LastNeedleState", [_tfx, _tfy, _frame, _hx, _hy, _bw, _bh, diag_tickTime, _angle]];
    uiNamespace setVariable ["ACME_IV_StickTopLeft", [_hx, _hy]];
};
if (!isNull _heldC) then { _heldC ctrlShow false; };

// Nothing held: palpation is allowed with or without a BOA. Transparent canvas is not skin, so the finger does
// not report a vein outside the authored patient silhouette.
if (isNull _dot) exitWith {};
if (!_drag || {!_onPatientArt}) exitWith { _dot ctrlShow false; };
// the palpation model can tighten or swell the fingertip. a picture control has color, alpha and size and
// nothing else, so size is a third of everything available to say what is under the finger.
private _dotMul = uiNamespace getVariable ["ACME_IV_DotSize", 1];
if (!(_dotMul isEqualType 0) || {!finite _dotMul}) then { _dotMul = 1 };
// the base was 0.014 and the palpation models shrink it further, which made the four modes hard to tell apart
// at a glance. the base is bigger now and tunable, so Ridge tightening to 0.55 still reads as a visible change
// rather than as a speck getting slightly smaller.
private _dotBase = missionNamespace getVariable ["ACME_iv_dotSize", 0.024];
if (!(_dotBase isEqualType 0) || {!finite _dotBase}) then { _dotBase = 0.024 };
private _dotR = _bh * _dotBase * ((_dotMul max 0.25) min 2.5);
_dot ctrlSetPosition [_ux - (_dotR / 2), _uy - (_dotR / 2), _dotR, _dotR / _af];
_dot ctrlSetTextColor _dotCol;
_dot ctrlShow true;
_dot ctrlCommit 0;

// darkness. the limb goes dark and the kit does not. you cannot palpate a vein you cannot see, and a blind stick
// in the dark is exactly as unpleasant as it sounds. get a light on the arm.

};
[uiNamespace getVariable ["ACME_IV_DLG", displayNull], [], "ACME_IV_Shade"] call ACME_fnc_darknessShade;
[uiNamespace getVariable ["ACME_IV_DLG", displayNull]] call ACME_fnc_minigameVisionTick;
