// Restock and expiration use their own schedule, separate from door and delivery leases.
if (!isServer || {!(["enabled"] call ACME_fnc_bloodTiming)}) exitWith {};
private _registered = missionNamespace getVariable ["ACME_bloodFridges", []];
if (_registered isEqualTo []) exitWith {};
private _fridges = _registered select {!isNull _x};
if (count _fridges != count _registered) then {ACME_bloodFridges = _fridges;};
// the interval restock, in configurable in-game hours and minutes since the last restock of each fridge.
// the interval is read live from the addon options, in hours and minutes, defaulting to 24 h. each fridge stores its
// own last-restock time in in-game hours, so a fridge regenerates on its own schedule from when it was placed. a
// per-fridge override, ACME_bf_regenMins, set by eden or zeus, wins over the global setting.
// the elapsed in-game time is derived from dateToNumber, a fraction of the in-game year, so it follows the time
// acceleration of the mission exactly. an interval of 0 disables regeneration.
private _yearHours = 365.25 * 24;
private _sampledAt = [] call ACME_fnc_clinicalClock;
private _nowGameHours = (dateToNumber date) * _yearHours;
{
    private _fridge = _x;
    if (!isNull _fridge) then {[_fridge, _sampledAt] call ACME_fnc_bloodFridgeExpire;};
    if (!isNull _fridge && {(["enabled"] call ACME_fnc_bloodTiming)}
        && {_fridge getVariable ["ACME_bf_restock", true]}) then {
        // the per-fridge interval override, in minutes, or the global hours plus minutes setting.
        private _intervalMins = _fridge getVariable ["ACME_bf_regenMins", -1];
        if (_intervalMins < 0) then {
            _intervalMins = ((missionNamespace getVariable ["ACME_bf_regenHours", 24]) * 60)
                          + (missionNamespace getVariable ["ACME_bf_regenMinutes", 0]);
        };
        if (_intervalMins > 0) then {
            private _intervalHours = (_fridge getVariable ["ACME_bf_restoreRestockDelayMins",_intervalMins]) / 60;
            private _last = _fridge getVariable ["ACME_bf_lastRestockGH", -1];
            if (_last < 0) then {
                // the first tick after placement: anchor the clock and do not restock yet.
                [_fridge, "ACME_bf_lastRestockGH", _nowGameHours] call ACME_fnc_setVarNet;
            } else {
                // guard the year-rollover wrap, because dateToNumber resets at jan 1: if now is below last, re-anchor.
                if (_nowGameHours < _last) then {
                    [_fridge, "ACME_bf_lastRestockGH", _nowGameHours] call ACME_fnc_setVarNet;
                } else {
                    if ((_nowGameHours - _last) >= _intervalHours) then {
                        _fridge setVariable ["ACME_bf_lotStart",_sampledAt,true];
                        [_fridge, "ACME_bf_stock", +(_fridge getVariable ["ACME_bf_default", []])] call ACME_fnc_setVarNet;
                        [_fridge, "ACME_bf_lastRestockGH", _nowGameHours] call ACME_fnc_setVarNet;
                        _fridge setVariable ["ACME_bf_restoreRestockDelayMins",nil,false];
                    };
                };
            };
        };
    };
} forEach _fridges;
