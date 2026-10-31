// Keep preflight, pending-ID reservation and any legacy source debit in one frame.
if (canSuspend) exitWith {isNil {_this call ACME_fnc_preparedAttachRequest;};};
params ["_args"];
_args params ["_medic", "_patient", "_target", "_item", "_action", "_vehicle", "_part", "_iv", "_site", "_volume", "_prepared", "_index", "_label"];
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
private _key = format ["prepared:%1:%2:%3:%4", clientOwner, netId _patient, _epoch, _prepared select 0];
private _inflight = missionNamespace getVariable ["ACME_preparedPending", createHashMap];
if (((values _inflight) findIf {(!(_x select 2)) && {(((_x select 0) select 10) select 0) == (_prepared select 0)}}) >= 0) exitWith {};
private _blocked = [_patient, _part, _iv, _site] call ACME_fnc_preparedAttachBlockReason;
if (_blocked != "") exitWith {[_medic, [_blocked] call ACME_fnc_preparedAttachMessage] call ACME_fnc_clinicalNotice;};
private _staged = _args param [13, []];
if ((_prepared param [15, ""]) == "" && {_staged isEqualTo []}) then {
    private _taken = false;
    if ((_prepared param [11, 0]) == 2 && {!isNull _vehicle}) then {
        private _cargo = getItemCargo _vehicle;
        private _ci = (_cargo select 0) find _item;
        if (_ci >= 0 && {((_cargo select 1) select _ci) > 0}) then {
            _vehicle addItemCargoGlobal [_item, -1];
            _taken = true;
        };
    } else {_taken = [_target, _item] call ACME_fnc_itemTake;};
    if (!_taken) then {_blocked = "prepared-set-missing";};
};
if (_blocked != "") exitWith {[_medic, [_blocked] call ACME_fnc_preparedAttachMessage] call ACME_fnc_clinicalNotice;};
private _serial = (missionNamespace getVariable ["ACME_preparedRequestSerial", 0]) + 1;
missionNamespace setVariable ["ACME_preparedRequestSerial", _serial];
private _id = format ["%1:%2", _key, _serial];
private _physical = !(_staged isEqualTo []) || {(_prepared param [15,""]) != ""};
if (_physical) then {
    private _receipt = [_medic,"prepared",_prepared select 0,_id] call ACME_fnc_inventoryLedgerReserve;
    if (_receipt isEqualTo []) then {_blocked = "prepared-set-missing";};
};
if (_blocked != "") exitWith {[_medic,[_blocked] call ACME_fnc_preparedAttachMessage] call ACME_fnc_clinicalNotice;};
private _pending = missionNamespace getVariable ["ACME_preparedPending", createHashMap];
if (_id in _pending) exitWith {};
_pending set [_id, [_args, CBA_missionTime, false, _epoch]];
missionNamespace setVariable ["ACME_preparedPending", _pending];
private _source = findDisplay 86000;
if (!isNull _source) then {_source closeDisplay 1;};
if (_physical) then {
    private _intents = _medic getVariable ["ACME_inventoryActionIntents",createHashMap]; _intents set [_id,["preparedAttach",[_args,_id,_epoch],0]]; _medic setVariable ["ACME_inventoryActionIntents",_intents,true];
    [_medic,_id,{
        params ["_accepted","_request"];
        _request params ["_args","_id","_epoch"];
        if (_accepted) then {[_args select 1,"preparedAttach",_request] call ACME_fnc_ownerDispatch;}
        else {[_args select 0,_id,false] call ACME_fnc_inventoryLedgerSettle; [_id,false,"","prepared-set-missing"] call ACME_fnc_preparedAttachAck;};
    },[_args,_id,_epoch]] call ACME_fnc_inventoryLedgerClaim;
} else {[_patient,"preparedAttach",[_args,_id,_epoch]] call ACME_fnc_ownerDispatch;};
