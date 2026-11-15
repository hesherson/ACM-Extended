// put the minigame back after ACE's interaction menu has closed.
// on why this exists: opening ACE's real menu over a display-mode minigame destroys the panel. every other
// explanation is ruled out by the game itself, because dialog is false for our panel, so ACE's while {dialog} do
// {closedialog 0} loop never touches it. that leaves the one thing we cannot change: ACE creates its cursormenu
// as a child of display 46, and our panel is a child of display 46 too. the map survives the same menu only
// because the map is display 12, an engine display, and is not competing for that slot.
// we cannot move our panel out of that slot, so we stop fighting it.
// the panel is not the procedure. the controls die with the display, and the procedure lives in uinamespace, as
// ACME_Thora_CutLen, cutangle and cutlocked, the placed catheters of the iv and the seal positions, and on the
// patient. the close handlers only clear transient interaction state, meaning what you were holding and whether
// the mouse was down, and that is state which should be reset anyway when a menu takes your cursor away mid-cut.
// so the display is rebuilt and the procedure is exactly where you left it. you get ACE's real menu, filtered to
// the light picker, and your incision is still open when it closes.
if (!hasInterface) exitWith {};

private _cls = uiNamespace getVariable ["ACME_minigame_reopen", ""];
if (_cls isEqualTo "") exitWith {};
uiNamespace setVariable ["ACME_minigame_reopen", ""];  // a one shot: never let this fire twice.

// already alive? then the panel survived after all and there is nothing to do. if a future ACE or engine build
// stops destroying sibling displays, this function simply becomes a no-op and quietly retires itself.
private _alive = (!isNull (uiNamespace getVariable ["ACME_IV_DLG", displayNull]))
              || (!isNull (uiNamespace getVariable ["ACME_CS_DLG", displayNull]))
              || (!isNull (uiNamespace getVariable ["ACME_Thora_DLG", displayNull]))
              || (!isNull (uiNamespace getVariable ["ACME_laryngo_dlg", displayNull]))
              || (!isNull (uiNamespace getVariable ["ACME_SK_DLG", displayNull]));
if (_alive) exitWith {
};


// next frame. ACE's cursormenu is mid-teardown right now, and creating a display into 46 while another is being
// destroyed on the same frame is how you end up with the focus in the wrong place.
[{
    params ["_c", "_ivSession", "_returnSerial"];
    if (_c == "ACME_IVMinigame_Dialog") exitWith {
        [_c, {
            params ["_session", "_serial"];
            _session isNotEqualTo []
                && {_serial == (uiNamespace getVariable ["ACME_medicalReturnSerial", 0])}
                && {!dialog}
                && {[_session] call ACME_fnc_ivUiValid}
                && {[] call ACME_fnc_ivInteractionValid}
        }, [_ivSession, _returnSerial]] call ACME_fnc_minigameOpen;
    };
    [_c] call ACME_fnc_minigameOpen;

    // the syringe kit rebuilds its lists and resets the barrel in its onload, so put the syringe back the frame
    // after it opens. it is the same problem the airway screen has and it is solved the same way.
    // one more frame, because the onload of the kit populates the lists and seats the plunger, and restoring
    // before that has finished would be overwritten by it.
    if (_c isEqualTo "ACME_SyringeKit_Dialog") then {
        [{
            private _snap = uiNamespace getVariable ["ACME_SK_snap", []];
            if ((count _snap) < 6) exitWith {};
            _snap params ["_size", "_vol", "_src", "_med", "_base", "_epi"];
            uiNamespace setVariable ["ACME_SK_Size", _size];
            uiNamespace setVariable ["ACME_SK_Vol", _vol];
            uiNamespace setVariable ["ACME_SK_Source", _src];
            uiNamespace setVariable ["ACME_SK_Med", _med];
            uiNamespace setVariable ["ACME_SK_SalineBase", _base];
            uiNamespace setVariable ["ACME_SK_EpiMl", _epi];
            uiNamespace setVariable ["ACME_SK_snap", []];
            // the plunger and the fluid column are drawn from that state, so repaint once rather than waiting for
            // the next drag to move them.
            call ACME_fnc_syringeKitRender;
        }, []] call CBA_fnc_execNextFrame;
    };
}, [_cls, +(uiNamespace getVariable ["ACME_IV_Session", []]),
    uiNamespace getVariable ["ACME_medicalReturnSerial", 0]]] call CBA_fnc_execNextFrame;
