/* Resolve the confirmed plunger against exact source stock before UI rounding.
   Endpoint draws keep every remaining fraction. Display rounding must never create
   solution, a repeated confirmation loop, or an implicit selection of another vial. */
params ["_drawn", "_session", "_stock", "_size"];
if (([_drawn, _session, _stock, _size] findIf {!(_x isEqualType 0) || {!finite _x}}) >= 0) exitWith {[false, 0, 0]};
private _limit = (_session min _stock min _size) max 0;
if (_drawn <= 0 || {_size <= 0}) exitWith {[false, 0, _limit]};
if (_drawn > _limit + 0.000001) exitWith {[false, _limit, _limit]};
private _amount = if (abs (_drawn - _limit) <= 0.000001) then {_limit} else {((round (_drawn * 100)) / 100) min _limit};
[_amount > 0, _amount, _limit]
