// Fast server callback for door leases and delivery acknowledgements.
if (!isServer) exitWith {};
// The grant outlives its furniture object and cosmetic door lease. Continue
// delivery even if Zeus removed the fridge after its stock was committed.
private _fridges = missionNamespace getVariable ["ACME_bloodFridges", []];
private _grantKeys = missionNamespace getVariable ["ACME_bf_activeGrants", []];
if (_fridges isEqualTo [] && {_grantKeys isEqualTo []}) exitWith {};
if !(_grantKeys isEqualTo []) then {
    private _serverGrants=missionNamespace getVariable ["ACME_bf_serverGrants",createHashMap];
    private _returns=missionNamespace getVariable ["ACME_resourceReturns",createHashMap];
    private _activeGrants=[];
    {
        private _grant=_serverGrants get _x;
        if ((_grant select 3)=="pending") then {
            private _bridge=_grant param [6,""];
            private _journal=_returns getOrDefault [_bridge,[]];
            private _unit=_grant select 0;
            if (count _journal>=11 && {(_journal select 4)=="delivered"}) then {
                _grant set [3,"delivered"];_serverGrants set [_x,_grant];
                private _anchor=_grant select 5;
                if (!isNull _anchor) then {private _localGrants=_anchor getVariable ["ACME_bf_grants",createHashMap];_localGrants set [_x,_grant];_anchor setVariable ["ACME_bf_grants",_localGrants];};
                if (!isNull _unit) then {
                    private _pending=_unit getVariable ["ACME_bf_pendingGrants",createHashMap];_pending deleteAt _x;_unit setVariable ["ACME_bf_pendingGrants",_pending,true];
                    ["ACME_bfGive",[_anchor,_grant select 2,_unit,_grant select 1,"delivered",_bridge],_unit] call CBA_fnc_targetEvent;
                };
            } else {
                // Dispatch, retries and ownership proof all belong to the generic
                // journal. Never send another native Give while its outcome is held.
                if (_journal isEqualTo [] && {_bridge!=""}) then {
                    ["fridgeStock",[_unit,_grant select 5,_bridge,[["item",_grant select 2]]]] call ACME_fnc_resourceReturnBroker;
                };
                if (count _journal>=11 && {(_journal select 4)=="orphaned"}) then {
                    // Retain canonical orphaned custody without a permanent idle
                    // poll. Mission recovery must explicitly resolve the journals.
                    _grant set [3,"orphaned"];_serverGrants set [_x,_grant];
                    private _anchor=_grant select 5;
                    if (!isNull _anchor) then {private _localGrants=_anchor getVariable ["ACME_bf_grants",createHashMap];_localGrants set [_x,_grant];_anchor setVariable ["ACME_bf_grants",_localGrants];};
                } else {_activeGrants pushBack _x;};
            };
        };
    } forEach _grantKeys;
    missionNamespace setVariable ["ACME_bf_serverGrants",_serverGrants];
    missionNamespace setVariable ["ACME_bf_activeGrants",_activeGrants];
};
if (_fridges isEqualTo []) exitWith {};

// the viewer-driven open and close.
private _now = diag_tickTime;
private _timeout = missionNamespace getVariable ["ACME_bf_viewTimeout", 0.9];
{
    private _anchor = _x;
    if (!isNull _anchor) then {
        private _open = _anchor getVariable ["ACME_bf_open", false];
        private _openObj = _anchor getVariable ["ACME_bf_openObj", objNull];
        private _viewers = _anchor getVariable "ACME_bf_viewers";
        private _takers = _anchor getVariable "ACME_bf_takers";
        if (!_open && {isNull _openObj}
            && {isNil "_viewers" || {count _viewers == 0}}
            && {isNil "_takers" || {count _takers == 0}}) then {continue;};
        private _live = false;
        {
            if ((_now - (_viewers get _x)) <= _timeout) then {_live = true;} else {_viewers deleteAt _x;};
        } forEach (if (isNil "_viewers") then {[]} else {keys _viewers});
        {
            (_takers get _x) params ["_unit", "_token", "_until"];
            if (!isNull _unit && {alive _unit} && {_now < _until} && {_unit distance _anchor <= 4.5}) then {
                _live = true;
            } else {_takers deleteAt _x;};
        } forEach (if (isNil "_takers") then {[]} else {keys _takers});

        // Retire a pre-B216 twin from a saved running mission without hiding the stock/interaction anchor.
        if (!isNull _openObj) then {
            _openObj hideObjectGlobal true;
            _anchor hideObjectGlobal false;
            _anchor setVariable ["ACME_bf_openObj", objNull, true];
            _anchor animateSource ["Door_1_noSound_source", [0, 1] select _open, true];
        };

        if (_live && !_open) then {
            [_anchor, "ACME_bf_open", true] call ACME_fnc_setVarNet;
            _anchor animateSource ["Door_1_noSound_source", 1, 2];
            private _near = allPlayers select {alive _x && {(_x distance _anchor) <= 80}}; if !(_near isEqualTo []) then {["ACME_worldSfx", [_anchor, "ACME_BloodFridgeDoorOpen"], _near] call CBA_fnc_targetEvent;};
        };
        if (!_live && _open) then {
            [_anchor, "ACME_bf_open", false] call ACME_fnc_setVarNet;
            _anchor animateSource ["Door_1_noSound_source", 0, 2];
            private _near = allPlayers select {alive _x && {(_x distance _anchor) <= 80}}; if !(_near isEqualTo []) then {["ACME_worldSfx", [_anchor, "ACME_BloodFridgeDoorClose"], _near] call CBA_fnc_targetEvent;};
        };
    };
} forEach _fridges;
