/* Pure presentation choice. Injury priority: any TBI history, arm fracture, significant torso, default.
 * Native RTMs are inherited by one-shot wrappers; no clinical state is changed here. */
params [["_tbi",false,[false]], ["_arms",false,[false]], ["_torso",false,[false]], ["_sample",-1,[0]]];
private _pool = ["ACME_WakeDefaultA", "ACME_WakeDefaultB", "ACME_WakeHeadC"];
if (_torso) then {_pool = ["ACME_WakeBodyA", "ACME_WakeBodyB"];};
if (_arms) then {_pool = ["ACME_WakeArmsA", "ACME_WakeArmsB", "ACME_WakeArmsC"];};
if (_tbi) then {_pool = ["ACME_WakeHeadA", "ACME_WakeHeadB", "ACME_WakeHeadC"];};
if (_sample < 0) then {_sample = random 1;};
_pool select ((floor (((_sample max 0) min 1) * count _pool)) min (count _pool - 1))
