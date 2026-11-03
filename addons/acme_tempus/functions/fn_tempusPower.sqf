params ["_o", "_on"];
if (isNull _o) exitWith {};
_o setVariable ["acme_tempus_pw", [_on, CBA_missionTime, false], true];
[["Tempus Pro powering off", "Tempus Pro starting up"] select _on, 1.5] call ace_common_fnc_displayTextStructured;
