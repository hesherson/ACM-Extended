/* Follow the active viewers and reverse from the current position on a quick reopen. */
params ["_args", "_handle"];
_args params ["_chest", "_cargo", "_revision", "_previous"];
private _cabinet = _chest getVariable ["ACME_medicalChestCabinet", objNull];
if (isNull _chest || {isNull _cabinet}
    || {(_chest getVariable ["ACME_medicalChestState", []]) isNotEqualTo [_revision, true]}) exitWith {
    [_handle] call CBA_fnc_removePerFrameHandler;
};

private _now = CBA_missionTime;
private _viewers = (_chest getVariable ["ACME_medicalChestViewers", []]) select {
    _x params ["_actor", "_owner", "_expires"];
    _expires > _now && {!isNull _actor} && {owner _actor == _owner}
        && {alive _actor} && {!(_actor getVariable ["ACE_isUnconscious", false])}
        && {!isNull _cargo} && {_actor distance _cargo <= 4.5}
};
_chest setVariable ["ACME_medicalChestViewers", _viewers];
private _targetOpen = _viewers isNotEqualTo [] && {!(_chest getVariable ["ACME_medicalChestTransition", false])};
private _current = _chest getVariable ["ACME_medicalChestDrawerFraction", 0];
private _delta = ((_now - _previous) max 0) / 0.24;
_args set [3, _now];
private _next = if (_targetOpen) then {(_current + _delta) min 1} else {(_current - _delta) max 0};
if (_next != _current) then {
    private _eased = _next * _next * (3 - 2 * _next);
    [_cabinet, _chest getVariable "ACME_medicalChestDrawerPlan", _eased] call ACME_fnc_medicalChestDrawers;
    _chest setVariable ["ACME_medicalChestDrawerFraction", _next];
    if (_next in [0, 1]) then {
        diag_log format ["[ACME] Medical chest drawers: %1 (%2)", ["shut", "extended"] select (_next == 1), typeOf _cabinet];
    };
};
if (!_targetOpen && {_next == 0}) then {
    _chest setVariable ["ACME_medicalChestDrawerPFH", -1];
    [_handle] call CBA_fnc_removePerFrameHandler;
};
