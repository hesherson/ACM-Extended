/* B227: shared pressure model for delivery and UI. New packets use serverTime across owner migration.
 * Legacy two-slot cuffs are read in their original owner clock. Zero/deflated cuff gives no boost. */
params [["_cuff", [], [[]]], ["_halfLife", -1, [0]]];
if (_cuff isEqualTo []) exitWith {0};
if (_halfLife < 0) then {_halfLife = missionNamespace getVariable ["ACME_pi_bleedHalfLifeSec",60];};
private _now = if ((_cuff param [2, ""]) == "server") then {serverTime} else {CBA_missionTime};
private _elapsed = (_now - (_cuff param [0,_now])) max 0;
private _p = (((_cuff param [1,0]) max 0) min 1) * (2 ^ (-_elapsed / (_halfLife max 0.1)));
if (_p < 0.08) then {0} else {_p min 1}
