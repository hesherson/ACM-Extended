private _me = ACE_player;
if (isNil "ACME_batdok_sent") then { ACME_batdok_sent = createHashMap };
if (isNil "ACME_batdok_asked") then { ACME_batdok_asked = createHashMap };
ACME_batdok_roster = ACME_batdok_roster select { !isNull _x };
private _now = call ACME_fnc_batdokNow;
private _sec = dayTime * 3600;
private _clock = _now + [floor ((_sec mod 1) * 1000), (timeMultiplier max 0.01) * accTime];
private _tri = ["", "Minimal", "Delayed", "Immediate", "Deceased"];

private _dev = [];
if (isClass (configFile >> "CfgPatches" >> "acme_tempus")) then { _dev pushBack "Tempus Pro" };
if (isClass (configFile >> "CfgPatches" >> "acme_tempusls")) then { _dev pushBack "Tempus LS" };
if (isClass (configFile >> "CfgPatches" >> "ACM_breathing")) then { _dev pushBack "Pulse oximeter" };
if (isClass (configFile >> "CfgPatches" >> "ACM_Extended")) then { _dev pushBack "Capnometer" };

ACME_batdok_peerList = [];
private _prov = (call ACME_fnc_batdokPeers) apply {
	ACME_batdok_peerList pushBack (_x select 0);
	[format ["u%1", count ACME_batdok_peerList - 1], _x select 1]
};

ACME_batdok_nearList = [];
private _near = [];
{
	if (count _near >= 10) exitWith {};
	if (_x isNotEqualTo _me && {!(_x in ACME_batdok_roster)}) then {
		ACME_batdok_nearList pushBack _x;
		private _cs = ((_x getVariable ["acme_batdok_rec", []]) param [1, []]) param [1, ""];
		if (_cs isEqualTo "") then { _cs = [_x] call ACME_fnc_batdokCallsign };
		private _t = if (alive _x) then { _tri param [_x getVariable ["ace_medical_triageLevel", 0], ""] } else {"Deceased"};
		_near pushBack [format ["n%1", count ACME_batdok_nearList - 1], [_x, false, true] call ace_common_fnc_getName, _cs, _me distance _x, _t];
	};
} forEach (nearestObjects [_me, ["CAManBase"], 12]);

private _pats = [];
{
	private _u = _x;
	private _rec = _u getVariable ["acme_batdok_rec", []];
	if (_rec isEqualTo []) then {
		if ((ACME_batdok_asked getOrDefault [hashValue _u, -1e9]) < time - 5) then {
			ACME_batdok_asked set [hashValue _u, time];
			[_u, "touch", [], _me] remoteExecCall ["ACME_fnc_batdokOp", 2];
		};
		continue;
	};
	_rec params ["_pid", "_info", "_inj", "_man", "_sen", "_xfer"];
	private _rev = _u getVariable ["acme_batdok_rev", 0];
	private _full = -1;
	if ((ACME_batdok_sent getOrDefault [_pid, -1]) isNotEqualTo _rev) then {
		ACME_batdok_sent set [_pid, _rev];
		_full = _info + [_u getVariable ["acme_batdok_log", []], _inj, _u getVariable ["acme_batdok_trend", []], _xfer, _sen];
	};
	private _att = false;
	private _live = [[-1, -1, -1, -1, -1, -1, -1, ""], "none", _now];
	if (_sen isNotEqualTo [] && {_sen select 1}) then {
		([_u, _sen select 0] call ACME_fnc_batdokSense) params ["_on", "_v"];
		_att = _on;
		if (_on) then { _live = [_v + [_man param [7, ""]], "host", _now] };
	};
	if (!_att && {_man isNotEqualTo []}) then { _live = [_man select [0, 8], "manual", _man select 8] };
	_live append [[_u] call ACME_fnc_batdokWounds, [_tri param [_u getVariable ["ace_medical_triageLevel", 0], ""], "Deceased"] select !alive _u, _att];
	_pats pushBack [_pid, _rev, _full, _live];
	if (!isNil "ACME_batdok_want" && {ACME_batdok_want isEqualTo _u}) then {
		ACME_batdok_want = nil;
		ACME_batdok_focus = [((missionNamespace getVariable ["ACME_batdok_focus", [0]]) param [0, 0]) + 1, _pid, "INFO"];
	};
} forEach ACME_batdok_roster;

[_clock, [_me] call ACME_fnc_batdokCallsign, _dev, _prov, _near, _pats, missionNamespace getVariable ["ACME_batdok_focus", [0, "", ""]]]
