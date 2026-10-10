/* B227: existing owner maintenance cadence; no per-click scheduler. Legacy jobs are cancelled on upgrade.
 * Both priming and flushing follow actual patient admission and the same saline ledger. */
params ["_p"];
if (isNull _p || {!local _p}) exitWith {};
private _jobs = _p getVariable ["ACME_yFlushJobs", createHashMap];
if (count _jobs == 0) exitWith {};
private _map = _p getVariable ["ACM_circulation_IV_Bags", createHashMap];
private _changed = false; private _topology = false;
{
    private _key = _x; private _job = _jobs get _key;
    if !([_job,_key] call ACME_fnc_yServiceJobValid) then {_jobs deleteAt _key; _topology = true; continue;};
    _job params ["_part","_iv","_site","_id","_remaining","_rate","_last","_medic","_epoch","_queue","_kind","_total","_delivered"];
    if (!alive _p || {_epoch != ([_p] call ACME_fnc_clinicalEpoch)}
        || {!([_p,_part,_iv,_site] call ACME_fnc_isYLineAccess)}
        || {!([_p,_part,_iv,_site] call ACME_fnc_transfusionAccessValid)}) then {_jobs deleteAt _key; _topology = true; continue;};
    private _arr = _map getOrDefault [_part, []];
    private _idx = _arr findIf {(_x param [8, ""]) == _id && {(_x param [3,-1]) == _site} && {(_x param [4,true]) isEqualTo _iv}};
    if (_idx < 0) then {_jobs deleteAt _key; _topology = true; continue;};
    private _e = +(_arr select _idx);
    if ((_e param [1,0]) <= 0.001 || {!((_e param [0, ""]) in ["Saline","ACME_SalineY"])}
        || {((_p getVariable ["ACME_infusion_BagMedications", []]) findIf {(_x param [23, ""]) == _id}) >= 0}) then {_jobs deleteAt _key; _topology = true; continue;};
    private _dt = ((serverTime - _last) max 0) min 1;
    private _pi = ACME_infusion_bodyParts find _part;
    private _drain = (_rate * _dt) min _remaining min (_e select 1);
    private _pass = 1;
    // Priming is also patient fluid now; it cannot bypass an occluded/stopped access or zero perfusion.
    call {
        // A late blood attach cannot bypass empty-blood-only servicing.
        private _blood = (_arr findIf {(_x param [0, ""]) in ["Blood","FreshBlood"] && {(_x param [1,0]) > 0.01} && {(_x param [3,-1]) == _site} && {(_x param [4,true]) isEqualTo _iv}}) >= 0;
        private _flow = if (_iv) then {((_p getVariable ["ACM_circulation_FluidBagsFlow_IV", [[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1]]]) select _pi) param [_site,0]} else {(_p getVariable ["ACM_circulation_FluidBagsFlow_IO", [1,1,1,1,1,1]]) param [_pi,0]};
        if ((_kind == "flush" && {_blood}) || {_flow <= 0} || {([_p,_pi,_iv,_site,-1] call ACM_circulation_fnc_getIVFlowRate) <= 0}) then {_drain = 0;};
        private _co = [_p] call ace_medical_status_fnc_getCardiacOutput;
        if !(_co isEqualType 0 && {finite _co}) then {_co = 0;};
        private _perfusing = ([_p] call ACM_core_fnc_cprActive) || {
            !(_p getVariable ["ace_medical_inCardiacArrest", false]) && {_co > 0.0001}
        };
        if (!_perfusing) then {_drain = 0;};
        _pass = [_p,_part,if (_iv) then {_site} else {-1}] call ACME_fnc_medicationLineFraction;
        if (_iv && {missionNamespace getVariable ["ACM_circulation_IVComplications", false]}) then {
            private _rows = _p getVariable ["ACM_circulation_IV_Complication_Placement_Flow", [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]]];
            private _c = (((_rows select _pi) param [_site,0]) max 0) min 2;
            _drain = _drain * ([1,0.9,0.85] select _c);
        };
    };
    if (_drain > 0) then {
        call {
            private _admitted = _drain * _pass;
            [_p,_part,_idx,_e,_drain,_admitted,_dt,true] call ACME_fnc_fluidCommit;
            [_p,[["salineVolume",(_p getVariable ["ACM_circulation_Saline_Volume",0]) + _admitted / 1000]],true] call ACM_circulation_fnc_setRuntimeState;
            if (!_iv && {_admitted > 0}) then {[_p,_part,"fluid"] call ACME_fnc_ioPainResponse;};
        };
        _e set [1,((_e select 1)-_drain) max 0];
        if ((_e select 1) <= 0.001) then {_e set [0,"ACME_EmptySaline"];};
        _arr set [_idx,_e]; _map set [_part,_arr]; _changed = true;
        _remaining = (_remaining - _drain) max 0; _delivered = _delivered + _drain;
    };
    _job set [4,_remaining]; _job set [6,serverTime]; _job set [12,_delivered];
    if (_remaining <= 0.001) then {
        if (_kind == "prime" && {_delivered >= 24.999}) then {
            private _primed = _p getVariable ["ACME_YLinePrimed",createHashMap]; _primed set [_key,true];
            [_p,"ACME_YLinePrimed",_primed] call ACME_fnc_setVarNet;
        };
        if (_kind == "flush" && {_delivered >= 24.999}) then {
            {private _m = _p getVariable [_x,createHashMap]; _m set [_key,0]; [_p,_x,_m] call ACME_fnc_setVarNet;} forEach ["ACME_YLineUnitsSinceFlush","ACME_YLineVolSinceFlush"];
            private _dirty = _p getVariable ["ACME_YLineDirty",createHashMap]; _dirty set [_key,false];
            [_p,"ACME_YLineDirty",_dirty] call ACME_fnc_setVarNet;
            [_p,"ACME_bloodLineDirty",((keys _dirty) findIf {_dirty get _x}) >= 0] call ACME_fnc_setVarNet;
        };
        _topology = true;
        if (_queue isEqualTo []) then {_jobs deleteAt _key;} else {
            private _next = _queue deleteAt 0;
            _job set [4,_next]; _job set [9,_queue]; _job set [11,_next]; _job set [12,0];
            _job set [5,_next / ((missionNamespace getVariable ["ACME_YFlushSeconds",5]) max 0.1)];
            _jobs set [_key,_job];
        };
    } else {_jobs set [_key,_job];};
} forEach keys _jobs;
if (_changed) then {[_p,_map,true] call ACME_fnc_ivBagsCommit;};
_p setVariable ["ACME_yFlushJobs", _jobs, false];
private _lastNet = _p getVariable ["ACME_yFlushJobsNetAt",-1];
// Publish remaining work with EVERY debit, not just once a second. On locality transfer a
// newer bag volume must not be paired with an older job remainder and repeat part of a flush.
if (_changed || {_topology} || {_lastNet < 0} || {diag_tickTime - _lastNet >= 1}) then {
    _p setVariable ["ACME_yFlushJobsNetAt",diag_tickTime,false];
    [_p,"ACME_yFlushJobs",_jobs] call ACME_fnc_setVarNet;
};
