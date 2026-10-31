/* No periodic metadata writes: timestamps age every physical carrier even in cargo.
 * This pass only imports legacy issue items and settles actual spoilage. */
if (!hasInterface || {!(missionNamespace getVariable ["ACME_sys_bloodChain",true])}) exitWith {};
private _p=ACE_player;
if (isNull _p || {!local _p}) exitWith {};
private _seeds=_p getVariable ["ACME_bloodSeedPending",createHashMap];
{
    private _seed=_seeds get _x;
    if (serverTime-(_seed select 4)>=2) then {
        _seed set [4,serverTime];
        ["ACME_bloodExposureRequest",["seed",_p,_seed select 0,_seed select 1,_seed select 2,_seed select 3,_seed select 5]] call CBA_fnc_serverEvent;
    };
} forEach (keys _seeds);
private _pending=missionNamespace getVariable ["ACME_bloodExposurePending",createHashMap];
{
    private _row=_pending get _x;
    if ((_row select 0) isNotEqualTo _p || {serverTime-(_row select 3)>30} || {(_row select 4)!=(_p getVariable ["ACME_equipmentKitEpoch",0])} || {(_row select 5)!=(_p getVariable ["ACME_providerLocalityEpoch",0])}) then {
        _pending deleteAt _x;
    } else {
        if (serverTime-(_row select 7)>=2) then {
            _row set [7,serverTime];
            ["ACME_bloodExposureRequest",["read",_p,_row select 2,_row select 6]] call CBA_fnc_serverEvent;
        };
    };
} forEach (keys _pending);
missionNamespace setVariable ["ACME_bloodExposurePending",_pending];
private _base=["ACME_BloodCooler_CSWB1U","ACME_BloodCooler_CSWB2U","ACME_BloodCooler_CSWB4U"];
{
    if (_x in _base) then {[_p,_x] call ACME_fnc_coolerIssue;};
} forEach ((uniformItems _p)+(vestItems _p)+(backpackItems _p));
call ACME_fnc_coolerAutoStore;
if (missionNamespace getVariable ["ACME_bloodSpoilEnabled",true]) then {
    private _limit=missionNamespace getVariable ["ACME_bloodLooseSpoilTime",1800];
    {
        _x params ["_sid","_raw"];
        private _state=[_raw] call ACME_fnc_coolerAdvance;
        if (((_state select 2) findIf {(_x select 1)>=_limit})>=0) then {
            [_p,_sid,{
                params ["_owner","_sid","_state"];
                private _kept=[];
                {
                    if ((_x select 1)<(missionNamespace getVariable ["ACME_bloodLooseSpoilTime",1800]) || {!([_owner,_x,false] call ACME_fnc_coolerGiveBag)}) then {_kept pushBack _x;};
                } forEach (_state select 2);
                _state set [2,_kept];[false,_state]
            }] call ACME_fnc_coolerMutate;
        };
    } forEach ([_p] call ACME_fnc_coolerRows);
};
if (!isNull (uiNamespace getVariable ["ACME_CLR_DLG",displayNull])) then {call ACME_fnc_coolerRefresh;};
