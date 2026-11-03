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
private _age=if (_live) then {(_meta select 1)+((CBA_missionTime-(_meta select 2)) max 0)} else {14400};
private _latched=(_live || {_saved}) && {(_meta select 0) in ["bloodUseSpoiledV1","bloodUseSpoiledAgeV1"]};
private _policy=missionNamespace getVariable ["ACME_persistentCampaignTiming",false]
    && {missionNamespace getVariable ["ACME_bloodSpoilEnabled",true]};
private _expired=_latched || {_policy && {_age>=14400}};
if (_mode=="age") exitWith {_age};
if (_mode=="expired") exitWith {_expired};
if (_mode=="snapshot") exitWith {[["bloodUseAgeV1","bloodUseSpoiledAgeV1"] select _expired,_age min 1e9]};
if (!(_seconds isEqualType 0) || {!finite _seconds} || {_seconds<0} || {_seconds>1e9}) then {_seconds=14400;};
if (_mode=="restore") exitWith {
    private _restoredAge=if (_saved) then {((_meta select 1)+_seconds) min 1e9} else {14400};
    [["bloodUseV1","bloodUseSpoiledV1"] select (!_saved || {_latched} || {_policy && {_restoredAge>=14400}}),_restoredAge,CBA_missionTime]
};
if (_live) exitWith {private _copy=+_meta;if (_expired) then {_copy set [0,"bloodUseSpoiledV1"];};_copy};
[["bloodUseV1","bloodUseSpoiledV1"] select (_meta isNotEqualTo [] || {_policy && {_seconds>=14400}}),if (_meta isEqualTo []) then {_seconds} else {14400},CBA_missionTime]
