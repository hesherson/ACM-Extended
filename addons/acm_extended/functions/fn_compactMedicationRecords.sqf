/* Merge nearby post-peak infusion samples of the same class, route and site.
 * This keeps long infusions bounded while retaining delivered mass and timing.
 * Boluses, bindable paralysis entries and still-absorbing pulses stay distinct. */
params ["_records","_now"];
private _cohorts = createHashMap;
private _result = [];
{
    private _record = _x;
    call {
        if ((_record param [16,""]) != "ACME_infusionPulse"
            || {(_record select 0) in ["Rocuronium","Rocuronium_IV","Sugammadex_IV","Adenosine_IV"]}
            || {_now - (_record select 1) < ((_record select 2) + (_record select 8) + 30)}) exitWith {_result pushBack _record;};
        private _age = _now - (_record select 1);
        private _window = 30;
        if (_age > ((_record select 3) + 300) && {_age > 1800}) then {_window = 300;};
        if (_age > 21600) then {_window = 3600;};
        // Older post-effect tails can share a wider time bucket. Route, site and phase remain distinct.
        private _key = str [_record select 0,_window,floor ((_record select 1)/_window),_record select 2,_record select 3,
            _record select 7,_record select 8,_record select 13,_record select 14];
        private _idx = _cohorts getOrDefault [_key,-1];
        if (_idx < 0) exitWith {_cohorts set [_key,_result pushBack _record];};
        private _prior = +(_result select _idx);
        private _dose = _record select 12;
        private _sum = (_prior select 12) + _dose;
        if (_sum > 0) then {
            _prior set [1,(_prior select 1) + ((_record select 1)-(_prior select 1))*_dose/_sum];
            _prior set [12,_sum];
            {_prior set [_x,(_prior select _x) + (_record select _x)];} forEach [4,5,6,9,10,11];
            _result set [_idx,_prior];
        };
    };
} forEach _records;
_result
