private _now = diag_tickTime;
private _cam = positionCameraToWorld [0, 0, 0];
private _src = +ACME_tempusls_near;
if (!isNull ACME_tempusls_cObj && {!(ACME_tempusls_cObj in _src)}) then { _src pushBack ACME_tempusls_cObj };
private _seen = [];
{
	private _o = _x;
	(_o getVariable ["acme_tempusls_metro", [false, ""]]) params [["_on", false], ["_ratio", ""]];
	private _key = netId _o;
	if (_on && {(_o getVariable ["acme_tempusls_pw", [false]]) select 0} && {(_o distance _cam) < 15}) then {
		_seen pushBack _key;
		(ACME_tempusls_ticks getOrDefault [_key, [0, 0]]) params ["_next", "_n"];
		if (_now >= _next) then {
			private _cycle = [30, 15, 0] select ((["30:2", "15:2", "Cont"] find _ratio) max 0);
			if (_cycle > 0 && {_n >= _cycle}) then {
				ACME_tempusls_ticks set [_key, [_now + 4, 0]];
			} else {
				playSound3D ["\x\ACM\addons\circulation\sound\aed_cprtick.wav", objNull, false, getPosASL _o, 2, 1, 15, 0, true];
				ACME_tempusls_ticks set [_key, [(_next + 60 / 110) max (_now + 0.25), _n + 1]];
			};
		};
	};
} forEach _src;
{
	if !(_x in _seen) then { ACME_tempusls_ticks deleteAt _x };
} forEach (keys ACME_tempusls_ticks);
