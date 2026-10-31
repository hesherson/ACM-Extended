/* Reserve a single token before any provider-local solution debit. */
params ["_owner","_row"];
if (isNull _owner || {!local _owner} || {(_row param [13,"",[""]]) != "inventoryB279"}) exitWith {""};
private _sid = _row param [11,"",[""]];
if (_sid == "" || {!([_owner,"syringe",_sid] call ACME_fnc_inventoryLedgerPossessed)}) exitWith {""};
private _serial = (_owner getVariable ["ACME_syringeInventoryRequestSerial",0]) + 1;
_owner setVariable ["ACME_syringeInventoryRequestSerial",_serial,false];
private _request = format ["syringeB279:%1:%2:%3",clientOwner,floor (diag_tickTime * 1000),_serial];
private _receipt = [_owner,"syringe",_sid,_request] call ACME_fnc_inventoryLedgerReserve;
if (_receipt isEqualTo []) exitWith {""};
_request
