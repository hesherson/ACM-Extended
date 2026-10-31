/* Scheduler maintains throttles/pending tails; actual delivered mg originate only in fluidCommit.
 * B246: bag registration/owner recovery enroll immediately and the shared 1 Hz discovery pass
 * repairs missed legacy transitions. This 4 Hz worker never scans every owned unit.
 */
private _patients = ACME_infusion_activePatients select {!isNull _x && {alive _x} && {local _x}};
private _kept = [];
{
    private _p = _x;
    private _entries = _p getVariable ["ACME_infusion_BagMedications", []];
    private _updated = [];
    {
        private _e = _x;
        private _id = _e param [23, ""];
        if (_id == "") then {
            // In-session legacy adoption is deliberately slot-exact, never nearest-volume rebinding.
            _id = [_p, _e select 1, _e select 2] call ACME_fnc_bagIdentity;
            _e set [23, _id];
        };
        private _found = [_p, _e select 1, _e select 2, _e select 3, _e select 4, _e select 5, _e select 6, _e select 7, _e select 8, _e select 10, _id] call ACME_fnc_findTrackedBag;
        if (_found isEqualTo []) then {
            [_p, _e, true] call ACME_fnc_infusionDeliver;
            private _pi = ACME_infusion_bodyParts find toLowerANSI (_e select 1);
            _p setVariable [format ["ACME_clampRate_%1_%2_%3", _pi, _e select 5, _e select 4], -1, false];
            // A reserved move is still the same bag. Preserve it while the identified move transaction is active.
            if (_id in keys (_p getVariable ["ACME_bagMoves", createHashMap])) then {_e set [17, 0]; _updated pushBack _e;};
            continue;
        };
        _found params ["_part", "_index", "_bag"];
        _e set [1, _part]; _e set [2, _index]; _e set [4, _bag select 3]; _e set [5, _bag select 4];
        [_p, _e] call ACME_fnc_infusionFlow;
        // No new flow commits means no active infusion-rate contribution, but existing medication history remains.
        if ((CBA_missionTime - (_e param [18, 0])) > 1.5) then {_e set [17, 0];};
        [_p, _e, (_bag select 1) <= 0.01] call ACME_fnc_infusionDeliver;
        _updated pushBack _e;
    } forEach _entries;
    [_p, _updated] call ACME_fnc_infusionMedicationStateCommit;
    // The signature change to [] publishes the final clear immediately. Do not retain
    // an empty patient afterward or the 1 s structured-state snapshot cadence becomes
    // a permanent post-treatment heartbeat.
    if !(_updated isEqualTo []) then {_kept pushBack _p;};
} forEach _patients;
ACME_infusion_activePatients = _kept;
