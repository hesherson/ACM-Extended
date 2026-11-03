if (!isServer || {isNil "ACME_batdok_units"}) exitWith {};
ACME_batdok_units = ACME_batdok_units select { !isNull _x };
private _acm = isClass (configFile >> "CfgPatches" >> "ACM_circulation");
private _t = CBA_missionTime;
{
	private _u = _x;
	private _rec = _u getVariable ["acme_batdok_rec", []];
	if (_rec isEqualTo []) then { continue };

	if (_acm) then {
		private _bags = _u getVariable ["ACM_circulation_IV_Bags", createHashMap];
		if !(_bags isEqualType createHashMap) exitWith {};
		private _known = _u getVariable ["acme_batdok_bags", []];
		private _seen = [];
		private _new = [];
		{
			private _part = _x;
			{
				_x params [["_type", ""], ["_left", 0], "", "", ["_iv", true], "", ["_vol", 0]];
				private _key = _x param [8, ""];
				if !(_key isEqualType "") then { _key = str _key };
				if (_key isEqualTo "") then { _key = format ["%1|%2|%3|%4", _part, _type, _vol, _forEachIndex] };
				_seen pushBack _key;
				if (!(_key in _known) && {_type isNotEqualTo "FBTK"}) then { _new pushBack [_type, [_vol, _left] select (_vol <= 0), _iv] };
			} forEach _y;
		} forEach _bags;
		_u setVariable ["acme_batdok_bags", _seen];
		{
			_x params ["_type", "_vol", "_iv"];
			private _name = switch (_type) do {
				case "Blood": {"Whole blood"};
				case "FreshBlood": {"Fresh whole blood"};
				case "Plasma": {"Plasma"};
				case "Saline": {"Normal saline"};
				default {_type};
			};
			private _route = ["IO", "IV"] select (_iv isEqualTo true);
			[_u, "log", ["fluid", format ["%1 %2 mL %3", _name, round _vol, _route], ["name", _name, "volume", str round _vol, "route", _route]]] call ACME_fnc_batdokOp;
		} forEach _new;
	};

	private _arrest = alive _u && {_u getVariable ["ace_medical_inCardiacArrest", false]};
	private _was = _u getVariable ["acme_batdok_arrest", false];
	if (_arrest isNotEqualTo _was) then {
		_u setVariable ["acme_batdok_arrest", _arrest];
		private _n = ["ROSC", "Cardiac arrest"] select _arrest;
		[_u, "log", ["event", _n, ["name", _n, "note", ["Pulse returned", "No pulse"] select _arrest]]] call ACME_fnc_batdokOp;
	};
	if (!alive _u && {!(_u getVariable ["acme_batdok_kia", false])}) then {
		_u setVariable ["acme_batdok_kia", true];
		[_u, "log", ["event", "Deceased", ["name", "Deceased", "note", "No signs of life"]]] call ACME_fnc_batdokOp;
		[_u, "Deceased"] call ACME_fnc_batdokTriage;
	};

	private _sen = (_u getVariable ["acme_batdok_rec", []]) param [4, []];
	if (_sen isNotEqualTo [] && {_sen select 1}) then {
		([_u, _sen select 0] call ACME_fnc_batdokSense) params ["_on", "_v"];
		if (!_on) then {
			private _miss = (_u getVariable ["acme_batdok_miss", 0]) + 1;
			_u setVariable ["acme_batdok_miss", _miss];
			if (_miss >= 3) then { [_u, "sen", [_sen select 0, false]] call ACME_fnc_batdokOp };
		} else {
			_u setVariable ["acme_batdok_miss", 0];
			if (_t - (_u getVariable ["acme_batdok_sampleAt", -1e9]) >= 60 && {(_v findIf { _x >= 0 }) >= 0}) then {
				_u setVariable ["acme_batdok_sampleAt", _t];
				[_u, "sample", _v] call ACME_fnc_batdokOp;
			};
		};
	};
} forEach +ACME_batdok_units;
