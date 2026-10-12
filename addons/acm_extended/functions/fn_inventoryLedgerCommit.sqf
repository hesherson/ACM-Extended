/* Source-funded payloads only. Losing native custody never creates a replacement token. */
if (canSuspend) exitWith {private _ok = false; isNil {_ok = _this call ACME_fnc_inventoryLedgerCommit;}; _ok};
params ["_owner", "_kind", "_rows"];
if (isNull _owner || {!local _owner} || {!(_kind in ["prepared","syringe"])}) exitWith {false};
private _tracked = missionNamespace getVariable ["ACME_inventoryTracked",[]]; _tracked pushBackUnique _owner; missionNamespace setVariable ["ACME_inventoryTracked",_tracked];
private _cache = _owner getVariable ["ACME_inventoryPayloadCache",createHashMap];
private _pending = _owner getVariable ["ACME_inventoryPending",createHashMap];
private _index = missionNamespace getVariable ["ACME_inventoryLedgerIndex",createHashMap];
private _native = [_owner,_kind] call ACME_fnc_inventoryLedgerNative;
private _escrow = _owner getVariable ["ACME_inventoryEscrow",createHashMap];
{
    private _payload = +_x;
    private _sid = _payload param [0,""];
    if (_sid == "") then {continue;};
    private _key = _kind + ":" + _sid;
    private _token = _index getOrDefault [_key,0];
    if (_token == 0 || {_key in _pending}) then {
        private _previous = _pending getOrDefault [_key,[]];
        _pending set [_key,[_kind,_sid,_payload,_owner getVariable ["ACME_equipmentKitEpoch",0],0,0,"pending"]];
        _owner setVariable ["ACME_inventoryPending",_pending,true];
        _cache set [_key,[_payload,0]];
        ["ACME_inventoryBroker",["register",_owner,_kind,_sid,_payload,""]] call CBA_fnc_serverEvent;
    } else {
        private _held = (_native findIf {(_x select 0) == _token}) >= 0;
        private _reserved = (values _escrow findIf {(_x param [0,0]) == _token}) >= 0;
        if (_held || {_reserved}) then {
            private _record = missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
            private _incoming = str _token in (_owner getVariable ["ACME_inventoryIncoming",createHashMap]) || {_kind in (_owner getVariable ["ACME_inventoryIncomingKinds",[]])};
            if (_held && {count _record >= 7} && {_incoming || {(_record select 3) isNotEqualTo _owner}}) then {
                [_owner,_kind,_token,_incoming] call ACME_fnc_inventoryLedgerAdopt;
            } else {
            if (_payload isEqualTo (_record param [2,[]])) then {continue;};
            private _previousCache = _cache getOrDefault [_key,[[],0]];
            private _mutations = _owner getVariable ["ACME_inventoryMutations",createHashMap];
            private _editing = (keys _mutations) findIf {((_mutations get _x) param [0,""]) == _sid};
            if (_editing >= 0) then {
                _mutations set [(keys _mutations) select _editing,_payload];
                _owner setVariable ["ACME_inventoryMutations",_mutations,true];
            } else {
                if (_held) then {
                    private _serial = (missionNamespace getVariable ["ACME_inventoryEditSerial",0])+1; missionNamespace setVariable ["ACME_inventoryEditSerial",_serial];
                    private _request = format ["inventory-edit:%1:%2:%3",clientOwner,_token,_serial];
                    private _receipt = [_owner,_kind,_sid,_request] call ACME_fnc_inventoryLedgerReserve;
                    if (_receipt isEqualTo []) then {continue;};
                    _mutations set [_request,_payload]; _owner setVariable ["ACME_inventoryMutations",_mutations,true];
                    [_owner,_request,{
                        params ["_accepted","_args"]; _args params ["_owner","_request"];
                        private _latest = (_owner getVariable ["ACME_inventoryMutations",createHashMap]) getOrDefault [_request,[]];
                        [_owner,_request,false,if (_accepted) then {_latest} else {[]}] call ACME_fnc_inventoryLedgerSettle;
                    },[_owner,_request]] call ACME_fnc_inventoryLedgerClaim;
                } else {
                    // Already-reserved workers own their exact receipt until final settlement.
                    ["ACME_inventoryBroker",["update",_owner,_kind,_sid,_payload,""]] call CBA_fnc_serverEvent;
                };
            };
            _cache set [_key,[_payload,((_record param [6,0]) max (_previousCache param [1,0]))+1]];
            };
        };
    };
} forEach _rows;
_owner setVariable ["ACME_inventoryPayloadCache",_cache];
_owner setVariable ["ACME_inventoryPending",_pending,true];
_owner setVariable ["ACME_inventoryKnown_" + _kind,_rows apply {_x select 0},true];
true
