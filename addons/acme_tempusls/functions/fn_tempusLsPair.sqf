params ["_o"];
if (isNull _o) exitWith {};
private _pros = (nearestObjects [_o, ["ACME_TempusPro"], 10]) select { (_x getVariable ["acme_tempus_pw", [false]]) select 0 };
_pros append ((_o nearEntities ["CAManBase", 10]) select { ((_x getVariable ["acme_tempus_pw", [false]]) select 0) && {[_x, "ACME_TempusPro_Item"] call ace_common_fnc_hasItem} });
if (_pros isEqualTo []) exitWith {
	_o setVariable ["acme_tempusls_link", objNull, true];
	["No Tempus Pro in range", 1.5] call ace_common_fnc_displayTextStructured;
};
private _pro = _pros select 0;
_o setVariable ["acme_tempusls_link", _pro, true];
private _pat = _o getVariable ["acme_tempusls_pat", objNull];
if (!isNull _pat && {isNull (_pro getVariable ["acme_tempus_pat", objNull])} && {!isNil "ACME_fnc_tempusConnect"}) then { [_pro, _pat] call ACME_fnc_tempusConnect };
["Tempus Pro connected", 1.5] call ace_common_fnc_displayTextStructured;
