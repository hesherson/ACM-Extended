/* Reconcile in-session escrow after packet delay or ownership migration.
   No timeout refund. Exactly the same request is retried; owner receipts are never count-evicted.
   Object deletion/mission shutdown needs administrative reconciliation, not invented delivery. */
{
    private _medic = _x;
    if (isNull _medic || {!local _medic}) then {continue;};
    private _escrow = _medic getVariable ["ACME_medicationEscrow",createHashMap];
    if (count _escrow == 0) then {continue};
    private _dt = [_medic,"medicationEscrow",0,2] call ACME_fnc_clinicalTickDelta;
    {
        private _row = _escrow get _x;
        private _age = (_row select 3) + _dt;
        private _tries = _row select 4;
        private _interval = if (_tries < 10) then {2} else {15};
        _row set [3,_age];
        if (_age >= _interval && {!isNull (_row select 0)}) then {
            _row set [3,0];_row set [4,_tries + 1];
            // Commit BEFORE a synchronous local acknowledgement can delete the record.
            _escrow set [_x,_row];
            [_medic, _escrow] call ACME_fnc_medicationEscrowCommit;
            [_row select 0,"medicationLine",_row select 1] call ACME_fnc_ownerDispatch;
        };
    } forEach (+(keys _escrow));
} forEach (missionNamespace getVariable ["ACME_clinical_ownedUnits",[]]);
