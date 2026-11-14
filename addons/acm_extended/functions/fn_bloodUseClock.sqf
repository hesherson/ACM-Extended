/* Portable use exposure: live clocks use mission time; saves contain age only.
 * Unknown/malformed claimed clocks fail closed. Missing legacy clocks start now.
 * [metadata, operation, initialWarmOrOfflineSeconds] */
params [["_meta",[]],["_mode","start"],["_seconds",0]];
private _live=_meta isEqualType [] && {count _meta==3} && {(_meta select 0) in ["bloodUseV1","bloodUseSpoiledV1"]}
    && {(_meta select 1) isEqualType 0} && {finite (_meta select 1)} && {(_meta select 1)>=0}
    && {(_meta select 2) isEqualType 0} && {finite (_meta select 2)};
private _saved=_meta isEqualType [] && {count _meta==2} && {(_meta select 0) in ["bloodUseAgeV1","bloodUseSpoiledAgeV1"]}
    && {(_meta select 1) isEqualType 0} && {finite (_meta select 1)} && {(_meta select 1)>=0} && {(_meta select 1)<=1e9};
if (_mode=="validLive") exitWith {_live};
if (_mode=="validSaved") exitWith {_saved};
private _limit = ["spiked"] call ACME_fnc_bloodTiming;
private _age = _limit;
if (_live) then {_age = (_meta select 1) + ((([true] call ACME_fnc_clinicalClock) - (_meta select 2)) max 0);};
if (_saved) then {_age = _meta select 1;};
private _latched=(_live || {_saved}) && {(_meta select 0) in ["bloodUseSpoiledV1","bloodUseSpoiledAgeV1"]};
private _policy=(["real"] call ACME_fnc_bloodTiming)
    && {(["spoil"] call ACME_fnc_bloodTiming)};
private _expired=_latched || {_policy && {_age>=_limit}};
if (_mode=="age") exitWith {_age};
if (_mode=="expired") exitWith {_expired};
if (_mode=="snapshot") exitWith {[["bloodUseAgeV1","bloodUseSpoiledAgeV1"] select _expired,_age min 1e9]};
if (!(_seconds isEqualType 0) || {!finite _seconds} || {_seconds<0} || {_seconds>1e9}) then {_seconds=_limit;};
if (_mode=="restore") exitWith {
    private _restoredAge=if (_saved) then {((_meta select 1)+_seconds) min 1e9} else {_limit};
    [["bloodUseV1","bloodUseSpoiledV1"] select (!_saved || {_latched} || {_policy && {_restoredAge>=_limit}}),_restoredAge,([true] call ACME_fnc_clinicalClock)]
};
if (_live) exitWith {private _copy=+_meta;if (_expired) then {_copy set [0,"bloodUseSpoiledV1"];};_copy};
[["bloodUseV1","bloodUseSpoiledV1"] select (_meta isNotEqualTo [] || {_policy && {_seconds>=_limit}}),if (_meta isEqualTo []) then {_seconds} else {_limit},([true] call ACME_fnc_clinicalClock)]
