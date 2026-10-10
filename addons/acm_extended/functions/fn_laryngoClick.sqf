
// a display-level left-click over the airway view, using the surface-tracked cursor.
// inserted does nothing, because the lift is on the grip key, left control, since the mouse is doing the aiming.
// tubeheld: a press and hold grips the tube. the wheel then feeds it, through fn_laryngoscroll, and the mouse
// keeps steering it. letting go lets it slide back out.
// tubing: a re-press re-grips after letting go.
// cuff: a press on the syringe grabs the plunger, and dragging it down inflates the cuff.
params ["_display", "_button"];
// A lost MouseUp (focus change) must not disable every subsequent parking press.
if ((diag_tickTime - (_display getVariable ["ACME_laryngo_saladPressAt", -10])) > 1.5) then {
    _display setVariable ["ACME_laryngo_saladPress", false];
};

// the middle button pins the suction. it is handled here rather than through a second MouseButtonDown handler,
// which was the reason it never fired: two handlers for the same event on the same display is not a contract
// worth relying on, and only the first one was getting there.
if (_button == 2 && {
    (_display getVariable ["ACME_laryngo_saladPress", false])
    || {uiNamespace getVariable ["ACME_laryngo_sucPinned", false]}
    || {(uiNamespace getVariable ["ACME_laryngo_held", ""]) == "suction"}
}) exitWith {
    if !(_display getVariable ["ACME_laryngo_saladPress", false]) then {
        _display setVariable ["ACME_laryngo_saladPress", true];
        _display setVariable ["ACME_laryngo_saladPressAt", diag_tickTime];
        [] call ACME_fnc_laryngoSuctionPin;
    };
    true
};
if ([_this,"down"] call ACME_fnc_minigameInputMouse) exitWith {true};

// a right click deflates the cuff, the exact mirror of the left-click hold that inflated it: the same syringe, the
// same pilot balloon and the same hold, with air out instead of in. this is the step that has to come before the
// tube can be moved, and it is deliberately the same gesture so it is learned once.
if (_button == 1) exitWith {
    if ((uiNamespace getVariable ["ACME_laryngo_held", ""]) == "syringe") then {
        ["start"] call ACME_fnc_laryngoCuffDeflate;
    };
    true
};

// a left click on the bulb is a squeeze. the wand suctions while the button is held, and the bulb draws in
// discrete pulls, so it is one click per squeeze. it is dispatched here before the hold logic of the wand, so
// the two cannot both fire.
if (_button == 0
    && {(uiNamespace getVariable ["ACME_laryngo_held", ""]) isEqualTo "suction"}
    && {((uiNamespace getVariable ["ACME_suction_device", createHashMap]) getOrDefault ["model", "wand"]) isEqualTo "bulb"}) exitWith {
    ["squeeze"] call ACME_fnc_suctionBulb;
};
if (_button != 0) exitWith {};
// secured means secured: nothing can be clicked back off it. suction is the exception, because clearing an airway
// does not disturb the tube and is the main reason to come back into this screen at all.
if ((uiNamespace getVariable ["ACME_laryngo_state", ""]) == "complete"
    && {(uiNamespace getVariable ["ACME_laryngo_held", ""]) != "suction"}) exitWith {};
private _cur = uiNamespace getVariable ["ACME_laryngo_cur", [-1, -1]];
_cur params ["_ex", "_ey"];
private _state = uiNamespace getVariable ["ACME_laryngo_state", "idle"];

// suction in hand owns the click. it has to be checked before anything else, because the collar and tube steps
// were claiming the button by state rather than by what is actually in the hand, so trying to suction during the
// collar step just told you to place the collar. hold to suction, release to stop.
if ((uiNamespace getVariable ["ACME_laryngo_held", ""]) == "suction") exitWith {
    if (!(uiNamespace getVariable ["ACME_laryngo_sucOn", false])) then {
        uiNamespace setVariable ["ACME_laryngo_sucOn", true];
        private _med = uiNamespace getVariable ["ACME_laryngo_medic", ACE_player];
        [_med, uiNamespace getVariable ["ACME_laryngo_patient", objNull]] call ACME_fnc_suctionSfxStart;
    };
};

// clicking the collar into place. it only takes while it is actually sitting where it belongs.
if (_state == "collar" && {(uiNamespace getVariable ["ACME_laryngo_held", ""]) == "collar"}) exitWith {
    if ((uiNamespace getVariable ["ACME_laryngo_held", ""]) == "collar" && {uiNamespace getVariable ["ACME_laryngo_collarSnapped", false]}) then {
        [] call ACME_fnc_laryngoCollarSet;
    } else {
        ["Take the collar from the tray and line it up over the tube.", 2] call ace_common_fnc_displayTextStructured;
    };
};

// the syringe on the pilot balloon. pressing starts the inflation. it is a hold rather than a click, and the whole
// run of the sound has to be held or the air comes back out.
if ((uiNamespace getVariable ["ACME_laryngo_held", ""]) == "syringe") exitWith {
    if ((uiNamespace getVariable ["ACME_laryngo_state", ""]) in ["cuff", "collar", "seated"]) then {
        ["grab"] call ACME_fnc_laryngoCuff;
    } else {
        ["There is no cuff to inflate yet.", 1.5] call ace_common_fnc_displayTextStructured;
    };
};

private _rect = uiNamespace getVariable ["ACME_laryngo_rect", [0, 0, 0.001, 0.001]];
_rect params ["_rx", "_ry", "_rw", "_rh"];
if (_ex < _rx || {_ex > _rx + _rw} || {_ey < _ry} || {_ey > _ry + _rh}) exitWith {};

switch (_state) do {
    case "inserted": {
        // lifting is done with the grip key, left control, rather than the mouse button, because the mouse is busy aiming
        // the instrument and will shortly be busy with the tube. a click here just tells the medic that.
        ["Hold LEFT CONTROL to grip the laryngoscope, then pull.", 2] call ace_common_fnc_displayTextStructured;
    };
    default {
        // anchor the tube at the cursor. the press commits the placement: the tip is pinned exactly where the pointer was
        // at this instant and does not move again until the button is released, so what you aimed at is what you get.
        // the wheel then feeds it.
        if (uiNamespace getVariable ["ACME_laryngo_tubeInHand", false]) then {
            uiNamespace setVariable ["ACME_laryngo_tubeGrip", true];
            uiNamespace setVariable ["ACME_laryngo_missLatched", false];
            uiNamespace setVariable ["ACME_laryngo_tubeAnchored", true];
            // it is stored against the frame rather than the screen. once the tube is committed it belongs to the airway, so
            // it has to ride the shake with the head. keeping an absolute screen position meant the head moved under a tube
            // that stayed nailed to the monitor.
            (uiNamespace getVariable ["ACME_laryngo_frame", [0,0,1,1]]) params ["_afx","_afy","_afw","_afh"];
            uiNamespace setVariable ["ACME_laryngo_tubeAnchorRel",
                [((_ex - _afx) / (_afw max 1e-5)), ((_ey - _afy) / (_afh max 1e-5))]];
            uiNamespace setVariable ["ACME_laryngo_tubeCatch", -1];

            // the verdict is taken here, at the cursor, at the instant of the click, and locked.
            // it used to be re-evaluated every frame from the sprung tip position of the tube, which lags the cursor and
            // settles on its own schedule, so the same click could read as on the cords one time and off them the next. that
            // is the inconsistency: it was not the aim that varied, it was when the answer happened to be sampled. the tube
            // cannot move once anchored, so there is nothing to re-check.
            (uiNamespace getVariable ["ACME_laryngo_rect", [0,0,0.2,0.2]]) params ["_hx","_hy","_hw","_hh"];
            (uiNamespace getVariable ["ACME_laryngo_cordsZone", [0.4978, 0.1367, 0.032]]) params ["_ccx","_ccy","_cr"];
            private _du = (_ex - _hx) / (_hw max 1e-5);
            private _dv = (_ey - _hy) / (_hh max 1e-5);
            private _d = sqrt ((((_du - _ccx)^2) + ((_dv - _ccy)^2)) max 0);
            private _verdict = switch (true) do {
                case (_d <= _cr): { "cords" };
                case (_d <= (missionNamespace getVariable ["ACME_laryngo_oesophRadius", 0.045])): { "esoph" };
                default { "" };
            };
            uiNamespace setVariable ["ACME_laryngo_tubeAimLock", _verdict];
        };
    };
};
