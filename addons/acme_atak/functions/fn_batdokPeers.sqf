private _me = ACE_player;
private _devs = missionNamespace getVariable ["ctab_core_androidDevices", ["ItemAndroid"]];
private _side = side group _me;
((allPlayers - [_me]) select {
	alive _x && {(side group _x) isEqualTo _side} && {isNil "cTab_fnc_checkGear" || {[_x, _devs] call cTab_fnc_checkGear}}
}) apply { [_x, format ["%1 (%2)", name _x, [_x] call ACME_fnc_batdokCallsign]] }
