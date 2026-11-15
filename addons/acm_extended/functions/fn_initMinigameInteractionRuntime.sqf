// Client presentation/input runtime only. Dedicated servers must not register UI PFHs, controls or keybinds.
if (!hasInterface) exitWith {};

// every dialog in this addon that a medic can stand inside while the world goes dark around them. the night
// vision toggle below uses this, so the goggles can be worked from inside any of them.
ACME_minigameDisplays = [
    86200,  // roller clamp
    86300,  // syringe kit / narc box
    86400,  // chest seal
    86500,  // iv
    86600,  // thoracostomy
    87400,  // blood cooler
    87600,  // blood fridge placement
    87620,  // blood fridge contents
    87700,  // ventilator
    87800  // laryngoscopy / suction
];

// Dialog input reads the native NightVision action and current CBA flip binding.
// The old ACME_vent_nvgToggle action is intentionally no longer registered.
// The flip entry retains its ID so existing user profiles keep their chosen binding.
// Its dialog owns execution, preventing CBA and UI callbacks from flipping twice.
[
    "ACM Extended", "ACME_vent_flipDevice",
    "Ventilator: Flip device (while panel open)",
    {false}, {false}, [0x21, [false,false,false]], false
] call CBA_fnc_addKeybind;

// ACE's own self-interaction menu renders over these dialogs and always did. it is the menu you already know.
// ctrl+win opens ACE's real menu in the minigame, exactly as it does everywhere else.

// the filter of the map, reused.
// the goal is ACE's real self-interaction menu, with everything filtered out except the light picker, and with
// no minigame closing. ACE already does all of that on the map, with one line in ace_common:
// ["notOnMap", {!visiblemap}] call ace_common_fnc_addCanInteractWithCondition;
// that is the whole mechanism. every action carries an exceptions[] list, and any condition not in that list is
// evaluated against it. an action that does not except "notOnMap" therefore fails while the map is open and
// vanishes. ACE_MapFlashlight does except it, so it survives. the short menu on the map is not a special map
// menu. it is the ordinary self-interaction menu with everything that fails one condition removed.
// the menu still opens on the map, rather than being blocked outright, because ACE's own keydown passes
// "notOnMap" in its exceptions too. that distinction is the whole trick. an earlier approach registered a new
// condition, which ACE's keydown does not except, so it blocked the menu from opening at all instead of
// filtering what was inside it.
// the condition map is keyed by name, so re-registering "notOnMap" replaces ACE's. we keep its meaning and add
// ours: not on the map, and not in a minigame. with no minigame open it behaves exactly as ACE wrote it.
// the state is derived from the live displays, never from a stored flag. an earlier version read a boolean that
// the minigames set on open and cleared on close. when a close path failed to run, and one did, the flag stayed
// true forever: the base self-interaction menu stayed filtered down to the flashlight entry for the rest of the
// mission, and ACE interaction was broken on every object in the world. that is a bug in the design, not in the
// close path. a condition ACE reads on every interaction must not depend on our code remembering to clean up
// after itself, because the cost of forgetting once is the whole interaction system, permanently, with no way
// for the player to recover. a display handle held in uinamespace becomes displaynull the instant the engine
// destroys the display. no route, not escape, a script error, ACE closing it or a mission event, can leave it
// stuck true. the engine clears it, and it cannot forget.
// we also block ACE from opening its menu over a dialog. ACE's keydown runs while {dialog} do { closedialog 0;
// } before it opens anything. our display KeyDown handler returning true does not stop that, because CBA's
// keybind system fires independently of our handler, so ACE runs anyway and closes the panel out from under us.
// the block is the only thing that prevents it, because ACE's caninteractwith check sits above that closedialog
// loop and a failing condition makes it bail out early. take it away and ctrl+win in a dialog minigame closes
// the minigame and opens the world menu.
// there are three states, and the middle one is why this is not a simple boolean:
// no minigame open, allow.
// minigame open as a dialog, block, because ACE would close it. our in-panel picker handles the key instead.
// minigame open as a display, allow, because a display is not a dialog, so ACE has nothing to close and its
// menu can open over the panel and be filtered down by notOnMap below.
// notOnMap is re-registered after ACE's own postinit, because ace_common_fnc_addCanInteractWithCondition
// overwrites by name. ACE registers ["notOnMap", {!visiblemap}] in its xeh_postinit, and if our extension runs
// first ACE clobbers it and the minigame filter dies silently. that is exactly why ctrl+win kept opening the
// full self-interact instead of our filtered flashlight menu. addon postinit order is not guaranteed, so we
// re-register on a short delay, after every addon's postinit has run, to guarantee ours wins.
// there is deliberately no separate condition that blocks all interaction while a minigame is open. an earlier
// build registered one, acme_minigameblocksinteract, as a global caninteractwith gate. a global gate blocks
// every action that does not list it in exceptions, and our flashlight action cannot except a private condition
// name, so that gate blocked the flashlight too. ctrl+win in a minigame then opened an empty menu with no
// options at all. the minigame is a dialog and already owns the mouse and the focus, so no extra gate is
// needed. notOnMap alone does the filtering.
[{
["notOnMap", {
    (!visibleMap) && {
        // treat the minigame like the map, so ACE filters its self-menu down to the flashlight alone. this must stay
        // true across the moment ACE closes the minigame dialog to open its menu, so it keys on a flag,
        // ACME_flashlightMenuActive, set when the player presses ctrl+win in a minigame and cleared when the menu
        // closes. it does not key on the live display handle, which nulls the instant the dialog closes, drops the
        // filter and lets the full menu through. the flag has a watchdog in fn_postInit, so it can never strand ACE.
        // live display handles are also honored, for display mode.
        !(missionNamespace getVariable ["ACME_flashlightMenuActive", false]) && {
            (isNull (uiNamespace getVariable ["ACME_IV_DLG", displayNull])) &&
            {isNull (uiNamespace getVariable ["ACME_CS_DLG", displayNull])} &&
            {isNull (uiNamespace getVariable ["ACME_Thora_DLG", displayNull])}
        }
    }
}] call ace_common_fnc_addCanInteractWithCondition;
}, [], 12] call CBA_fnc_waitAndExecute;

// after ACE's interaction menu closes there are two jobs, and the first is a leak.
// 1. give the player their settings back. while forwarding ctrl+win we force
// ace_interact_menu_alwaysUseCursorSelfInteraction true, because that is the lever that makes ACE build the
// map-style cursor menu instead of the camera-aim one. that is the player's setting. it was restored on panel
// close only, so if the menu closed while the panel stayed open, the player kept a forced setting they never
// chose for the rest of the mission.
// an earlier idempotency guard tested for the string "ace_interactMenuClosed", which already existed in an
// unrelated handler further up this file. the guard skipped the append and the verification printed ok for the
// wrong reason. a check that can pass without the thing being true is not a check. this one keys on a string
// that exists nowhere else.
// 2. put the panel back. opening ACE's menu destroys our display. see fn_minigamereopen for why, and why we
// cannot prevent it. the procedure survives in uinamespace and only the controls die, so we rebuild them.
["ace_interactMenuClosed", {
    // the flashlight flow is over. drop the filter flag first, so the next ordinary self-interact is unfiltered,
    // then give the player their cursor setting back and rebuild the minigame panel from its saved procedure
    // state.
    missionNamespace setVariable ["ACME_flashlightMenuActive", false];
    [] call ACME_fnc_aceCursorRestore;
    [] call ACME_fnc_minigameReopen;
}] call CBA_fnc_addEventHandler;

// watchdog. the flashlight filter flag must never strand the action hidden after the menu closes.
// the flashlight filter flag must never strand ACE. ace_interactMenuClosed clears it in the normal
// case, but if that event is ever missed, this force-clears the flag a few seconds after it was set, so a
// filtered self-interact can never persist for the rest of the mission. the check is cheap and runs only while
// the flag is up.
[{
    if (missionNamespace getVariable ["ACME_flashlightMenuActive", false]) then {
        private _at = missionNamespace getVariable ["ACME_flashlightMenuActiveAt", 0];
        if ((diag_tickTime - _at) > 6 && {isNull (findDisplay 91919)}) then {
            missionNamespace setVariable ["ACME_flashlightMenuActive", false];
            // ACE may skip its close event if its menu never opened. Retire
            // the IV rebuild request too, or every subsequent launch rejects it.
            if ((uiNamespace getVariable ["ACME_minigame_reopen", ""]) == "ACME_IVMinigame_Dialog") then {
                uiNamespace setVariable ["ACME_minigame_reopen", ""];
            };
            [] call ACME_fnc_aceCursorRestore;
        };
    };
}, 1, []] call CBA_fnc_addPerFrameHandler;
