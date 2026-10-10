/* B227 owner-local queue. Replayed/delayed requests cannot double-debit or queue on a new patient epoch. */
params [["_p",objNull,[objNull]],["_medic",objNull,[objNull]],["_part","",[""]],
    ["_iv",true,[true]],["_site",-1,[0]],["_epoch",-1,[0]],["_mode","",[""]],
    ["_request","",[""]],["_issued",-1,[0]],["_reserveId","",[""]],["_jobId","",[""]]];
if (isNull _p || {!local _p} || {!alive _p} || {isNull _medic} || {!alive _medic}
    || {_medic getVariable ["ACE_isUnconscious", false]} || {_epoch != ([_p] call ACME_fnc_clinicalEpoch)}
    || {([_medic, _p] call ACME_fnc_patientInteractionDistance) > 5}) exitWith {};
if (_request == "" || {count _request > 128} || {_reserveId == ""} || {count _reserveId > 128}
    || {!(_mode in ["prime","flush","cancel"])} || {!finite _issued} || {!finite _epoch}
    || {serverTime - _issued > 10} || {_issued > serverTime + 2}
    || {!(_part in ["head","body","leftarm","rightarm","leftleg","rightleg"])}
    || {!(_site in (if (_iv) then {[0,1,2]} else {[0]}))}) exitWith {};
private _receipts = _p getVariable ["ACME_yServiceReceipts", createHashMap];
if (_request in _receipts) exitWith {};
{if (serverTime - (_receipts get _x) > 12) then {_receipts deleteAt _x;};} forEach keys _receipts;
// Never evict a live receipt to make room: its request could still be replayed.
if (count _receipts >= 512) exitWith {};
_receipts set [_request, serverTime]; [_p,"ACME_yServiceReceipts",_receipts] call ACME_fnc_setVarNet;
_part = toLowerANSI _part;
if !([_p, _part, _iv, _site] call ACME_fnc_isYLineAccess) exitWith {[_medic, "No Y tubing on that access site."] call ACME_fnc_clinicalNotice;};
if !([_p, _part, _iv, _site] call ACME_fnc_transfusionAccessValid) exitWith {};
private _key = toLowerANSI format ["%1#%2#%3", _part, _iv, _site];
private _refill = (_p getVariable ["ACME_yRefillClaims", createHashMap]) getOrDefault [_key, []];
if (count _refill >= 4 && {serverTime - (_refill select 3) < 30}) exitWith {
    [_medic, "Finish replacing the bag before servicing this line."] call ACME_fnc_clinicalNotice;
};
private _jobs = _p getVariable ["ACME_yFlushJobs", createHashMap];
([_p,_part,_iv,_site] call ACME_fnc_yServiceState) params ["_reserve","_reserved","_blood","_dirty","_primed","_running","_id","_job"];
// A delayed click must not service a replacement bag installed at the same site.
if (_id != _reserveId || {_job isNotEqualTo [] && {(_job param [3, ""]) != _reserveId}}) exitWith {};
if (_job isNotEqualTo [] && {!([_job,_key] call ACME_fnc_yServiceJobValid)}) exitWith {};
if (((_p getVariable ["ACME_infusion_BagMedications", []]) findIf {(_x param [23, ""]) == _reserveId}) >= 0) exitWith {};
if (_mode == "cancel") exitWith {
    if ((_job param [13, ""]) != _jobId) exitWith {};
    // Right click removes the last QUEUED flush only. Fluid already delivered is never refunded.
    private _queue = +(_job param [9, []]);
    if (_running == "flush" && {_queue isNotEqualTo []}) then {
        _queue deleteAt (count _queue - 1); _job set [9, _queue]; _jobs set [_key, _job];
        [_p, "ACME_yFlushJobs", _jobs] call ACME_fnc_setVarNet;
    };
};
([_mode,_reserve,_reserved,_blood,_dirty,_primed,_running] call ACME_fnc_yServicePlan) params ["_ok","_total","_reason"];
if (!_ok) exitWith {[_medic,_reason] call ACME_fnc_clinicalNotice;};
if (_job isNotEqualTo [] && {count (_job param [9,[]]) >= 100}) exitWith {};
if (_job isNotEqualTo []) then {
    private _queue = +(_job param [9, []]); _queue pushBack _total;
    _job set [9, _queue];
} else {
    if (_id == "") then {
        private _bags = (_p getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_part, []];
        private _index = _bags findIf {(_x param [0, ""]) in ["Saline","ACME_SalineY"] && {(_x param [3,-1]) == _site} && {(_x param [4,true]) isEqualTo _iv}};
        if (_index >= 0) then {_id = [_p, _part, _index] call ACME_fnc_bagIdentity;};
    };
    if (_id != "") then {_job = [_part,_iv,_site,_id,_total,_total / ((missionNamespace getVariable ["ACME_YFlushSeconds",5]) max 0.1),serverTime,_medic,_epoch,[],_mode,_total,0,_request];};
};
if (_job isEqualTo []) exitWith {};
_jobs set [_key,_job];
[_p, "ACME_yFlushJobs", _jobs] call ACME_fnc_setVarNet;
