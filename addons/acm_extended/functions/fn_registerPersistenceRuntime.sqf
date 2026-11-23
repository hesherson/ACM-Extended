/* B393: the client events of the ACME Persistence module (fn_persistModuleInit.sqf, fn_persistClient.sqf).
 * The server raises ACME_persistStart once (JIP: players joining later get it too) when the module is in the
 * mission; nothing here saves or restores anything in a mission without it. */
["ACME_persistStart", {["start"] call ACME_fnc_persistClient}] call CBA_fnc_addEventHandler;
["ACME_persistApply", {["apply", _this param [0, []]] call ACME_fnc_persistClient}] call CBA_fnc_addEventHandler;
if (hasInterface) then {
    // the module's settings may have arrived before this machine registered the start event (JIP order)
    if (!isNil "ACME_persist") then {["start"] call ACME_fnc_persistClient;};
    // another persistence system set this player's kit through CBA with ACME's item state in it: that state is
    // the one to keep (fn_persistClient.sqf "apply" then does not put the module's own over it)
    ["CBA_loadoutSet", {
        params ["_unit", "", ["_extended", createHashMap]];
        if (_unit isEqualTo player && {_extended isEqualType createHashMap}
            && {(_extended getOrDefault ["ACME_checkpoint_v1", []]) isEqualTo [1, true]}) then {
            ACME_persistOtherKit = _unit;
        };
    }] call CBA_fnc_addEventHandler;
    // the summary of a Zeus "Persistence: save now / status / forget" (fn_persistServer.sqf "report")
    ["ACME_persistReport", {
        params [["_lines", [], [[]]]];
        // plain lines: no markup characters reach parseText
        private _text = (_lines select {_x isEqualType ""}) apply {(_x splitString "<>&") joinString ""};
        if (_text isEqualTo []) exitWith {};
        [parseText format ["<t align='left' size='0.9'>%1</t>", _text joinString "<br/>"], (1 + 0.5 * count _text) min 6, ACE_player, 14] call ace_common_fnc_displayTextStructured;
    }] call CBA_fnc_addEventHandler;
};
// Zeus "save now" in a mission without the Eden module turns persistence on with the default settings
if (isServer) then {
    ["ACME_persistEnableDefault", {
        [{["enableDefault"] call ACME_fnc_persistServer}] call CBA_fnc_execNextFrame;
    }] call CBA_fnc_addEventHandler;
};
