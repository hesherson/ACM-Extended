/*
 * The "Drag behind you" action of the ACE menu, for a thing.
 *
 * It is never a node of its own on the thing: it goes INSIDE the menu the thing already has, so that no two
 * nodes lie on the same spot (a node on top of another makes the one below unreachable).
 *  - a thing in general: under ACE's main node, ["ACE_MainActions"] (ACE makes that node for a class without
 *    one). XEH_postInit.sqf does that for every ThingX.
 *  - a thing whose addon made a root of its own for its menu (the monitors, the ACCUVAC): under that root; the
 *    addon that makes the root adds this action to it.
 * Returns: the action <ARRAY>.
 */
["acme_drag", "Drag behind you", "", {[_player, _target] call acme_sked_fnc_dragStart},
    {[_player, _target] call acme_sked_fnc_dragCan}] call ace_interact_menu_fnc_createAction
