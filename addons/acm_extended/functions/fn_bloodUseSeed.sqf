/* Seed from the actual debited holder (medic, patient, removed carrier or vehicle).
 * Class-identical bags use the oldest available exposure, never a younger guess. */
params ["_row","_holder",["_class",""]];
if (([_row,"prepared","get"] call ACME_fnc_bloodUseRow) isNotEqualTo []) exitWith {[_row,"prepared"] call ACME_fnc_bloodUseRow};
private _started=[_row,"prepared"] call ACME_fnc_bloodUseRow;
if (_started isEqualTo _row || {isNull _holder}) exitWith {_started};
if (_class=="") then {_class=_row param [1,""];};
private _warm=0;
private _sample=([] call ACME_fnc_clinicalClock);
private _exposure=_holder getVariable ["ACME_bloodExposure",[[],_sample]];
if (_exposure isEqualType [] && {count _exposure==2} && {(_exposure select 0) isEqualType []} && {(_exposure select 1) isEqualType 0}) then {
    {
        if ((_x param [0,""])==_class) then {_warm=_warm max ((_x select 2)+((_sample-(_exposure select 1)) max 0));};
    } forEach (_exposure select 0);
};
private _pending=_holder getVariable ["ACME_bloodSeedPending",createHashMap];
{
    private _seed=_pending get _x;
    if ((_seed param [0,""])==_class) then {_warm=_warm max ((_seed select 2)+((_sample-(_seed select 3)) max 0));};
} forEach keys _pending;
if ((_class find "ACME_FreshBloodBag_") == 0) then {
    private _limit = [_class] call ACME_fnc_bloodWarmLimit;
    _warm = if (_warm >= _limit) then {["spiked"] call ACME_fnc_bloodTiming} else {0};
} else {
    if (_warm >= ([_class] call ACME_fnc_bloodWarmLimit)) then {_warm = ["spiked"] call ACME_fnc_bloodTiming;};
};
[_started,"prepared","set",0,[[],"start",_warm] call ACME_fnc_bloodUseClock] call ACME_fnc_bloodUseRow
