/* For live loose/cooler rows, donor identity preserves the collection clock even while refrigerated.
 * Prepared/hung rows carry their own post-spike deadline and donor metadata. */
params ["_class"];
if ((_class find "ACM_FreshBloodBag_") != 0) exitWith {["warm"] call ACME_fnc_bloodTiming};
if !(["real"] call ACME_fnc_bloodTiming) exitWith {["warm"] call ACME_fnc_bloodTiming};
private _limit = ["fresh"] call ACME_fnc_bloodTiming;
private _parts = _class splitString "_";
private _id = _parts param [3,""];
if (_id == "") exitWith {_limit};
private _entry = [parseNumber _id] call ACME_fnc_freshBloodResolve;
if (_entry isEqualTo []) exitWith {_limit};
if ((([true] call ACME_fnc_clinicalClock) - (_entry select 4)) >= _limit) exitWith {0};
_limit
