// peel a chest seal back one frame per scroll notch, and roll the other way to lay it down one frame at a time.
// call it as [_src, _scroll] call ACME_fnc_chestSealScroll, from the MouseZChanged of the display and of every
// control on it.
//
// THE FIRST NOTCH ON A SEAL LOCKS THE SIDE, AND THAT LOCK HOLDS UNTIL YOU LEAVE THE SEAL.
//   scroll DOWN first   this seal peels from the RIGHT, and only from the right.
//   scroll UP first     this seal peels from the LEFT, and only from the left.
// after that the locked direction always lifts and the opposite direction always lays down, for as long as the
// cursor stays on that seal. reaching flat does NOT release the lock, so rolling on past flat cannot start a
// fresh peel on the other corner.
// that was the fault: the lock used to be cleared at frame 0, so scrolling hard back and forth alternated sides
// and both corners flapped as fast as the wheel turned. a taped seal has one corner lifted at a time and the one
// you chose is the one you are working.
// the lock is released by MOVING OFF THE SEAL, in fn_chestSealTick, which also lays it flat. that is the only
// release, and it is an input rather than a timer.
//
// The peel remains frame by frame. Only accepting another burp is timed.
// each notch moves exactly one frame, 0 to 5, and the seal sits at that frame until the medic moves the wheel
// again. fn_chestSealRender is EVENT DRIVEN and never runs per frame, so a frame chosen from elapsed time was
// written once and never advanced, which is why earlier versions drew nothing. a notch IS an event, so this
// calls the render itself.
//
// THE BURP ITSELF FIRES ONCE, at frame 5, which is full lift and the moment the seal is off the chest and the
// trapped air can leave. rolling back before frame 5 lays it down without treating anything, which is right: a
// corner lifted halfway is not a burp.
//
// WHY THE HANDLER IS ON EVERY CONTROL AND NOT JUST THE DISPLAY.
// a display level MouseZChanged does not fire while the cursor sits over a control, and the body picture and the
// interaction surface cover almost this whole panel. fn_ivMinigameInit carries the same note. see the binding in
// fn_chestSealInit.
params [["_src", displayNull], ["_scroll", 0]];
if (!hasInterface) exitWith {false};
if (_scroll == 0) exitWith {false};

if ((uiNamespace getVariable ["ACME_CS_FlipLockedUntil",0]) > diag_tickTime) exitWith {false};
private _maxFrame = 5;
// 1 is up and -1 is down. only the sign carries meaning, because a mouse can report any magnitude.
private _dir = if (_scroll > 0) then { 1 } else { -1 };

// a tool in the hand means the medic is placing, not burping. three separate flags and they are not the same
// thing: ACME_CS_Held and ACME_CS_SpearHeld are the tool slots, at fn_chestSealMouseDown:9 and :10, and
// ACME_CS_Held is the seal actually carried on the cursor, at :157.
if (uiNamespace getVariable ["ACME_CS_Held", false]) exitWith {false};
if (uiNamespace getVariable ["ACME_CS_SpearHeld", false]) exitWith {false};
if (uiNamespace getVariable ["ACME_CS_Held", false]) exitWith {false};

// which seal the cursor is on, through the one search shared with the right click peel and the hover check.
private _onSeal = [] call ACME_fnc_chestSealSealAt;
if (_onSeal < 0) exitWith {false};  // nothing under the wheel. the scroll is left alone.

private _lockIdx = uiNamespace getVariable ["ACME_CS_BurpIdx", -1];

// A DIFFERENT SEAL, OR NO LOCK AT ALL. this notch takes the lock and its direction sets the corner.
// DOWN peels from the RIGHT and UP peels from the LEFT. the side names the art folder directly,
// ui/chest_seal/burp_left and burp_right, so there is no mapping to get backwards.
if (_lockIdx != _onSeal) exitWith {
    if (!([uiNamespace getVariable ["ACME_CS_Patient",objNull]] call ACME_fnc_chestSealBurpReady)) exitWith {false};
    uiNamespace setVariable ["ACME_CS_BurpIdx", _onSeal];
    uiNamespace setVariable ["ACME_CS_BurpFrame", 1];
    uiNamespace setVariable ["ACME_CS_BurpFired", false];
    uiNamespace setVariable ["ACME_CS_BurpDir", _dir];
    uiNamespace setVariable ["ACME_CS_BurpSide", (if (_dir > 0) then { "left" } else { "right" })];
    [] call ACME_fnc_chestSealSnd;
    [format ["Peeling the seal. Scroll %1 to lift it, %2 to lay it back.",
        (if (_dir > 0) then {"up"} else {"down"}),
        (if (_dir > 0) then {"down"} else {"up"})], 3, ACE_player] call ace_common_fnc_displayTextStructured;
    [] call ACME_fnc_chestSealRender;
    false
};

// THE SAME SEAL, ALREADY LOCKED. the locked direction lifts and the other lays down. the side never changes.
private _fr = uiNamespace getVariable ["ACME_CS_BurpFrame", 0];
if (!(_fr isEqualType 0) || {!finite _fr}) then { _fr = 0; };
if (_fr <= 0 && {!([uiNamespace getVariable ["ACME_CS_Patient",objNull]] call ACME_fnc_chestSealBurpReady)}) exitWith {false};
private _openDir = uiNamespace getVariable ["ACME_CS_BurpDir", 0];

// A completed burp must not latch this seal forever at full lift. After the shared
// cooldown, a new opening scroll starts a fresh peel cycle without moving off the seal.
// Reversing the wheel still lays the corner down immediately, including during cooldown.
if (_fr >= _maxFrame && {uiNamespace getVariable ["ACME_CS_BurpFired", false]}
    && {_dir isEqualTo _openDir}
    && {[uiNamespace getVariable ["ACME_CS_Patient", objNull]] call ACME_fnc_chestSealBurpReady}) then {
    _fr = 0;
    uiNamespace setVariable ["ACME_CS_BurpFrame", 0];
    uiNamespace setVariable ["ACME_CS_BurpFired", false];
};

if (_dir isEqualTo _openDir) then {
    // further open. it stops at full lift rather than wrapping.
    if (_fr < _maxFrame) then {
        _fr = _fr + 1;
        uiNamespace setVariable ["ACME_CS_BurpFrame", _fr];
        if (_fr >= _maxFrame && {!(uiNamespace getVariable ["ACME_CS_BurpFired", false])}) then {
            uiNamespace setVariable ["ACME_CS_BurpFired", true];
            private _bm = uiNamespace getVariable ["ACME_CS_Medic", objNull];
            private _bp = uiNamespace getVariable ["ACME_CS_Patient", objNull];
            if (!isNull _bp) then { [_bm, _bp, "body"] call ACME_fnc_chestSealBurp; };
        };
    };
} else {
    // back down. it stops AT FLAT and keeps the lock, so rolling on past flat does nothing at all rather than
    // lifting the opposite corner.
    if (_fr > 0) then {
        _fr = _fr - 1;
        uiNamespace setVariable ["ACME_CS_BurpFrame", _fr];
        if (_fr <= 0) then {
            // the same one-shot the seal plays going on, because pressing a lifted corner back down is the same
            // sound. the lock survives, and only leaving the seal releases it.
            uiNamespace setVariable ["ACME_CS_BurpFired", false];
            [] call ACME_fnc_chestSealSnd;
        };
    };
};

[] call ACME_fnc_chestSealRender;
false
