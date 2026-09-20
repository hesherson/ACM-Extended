// the hang bag availability. it needs a patient with at least one hung iv bag, in ACM_circulation_IV_Bags, and a
// medic who is on foot and not already holding a bag up, because you raise an existing bag for gravity flow.
// the ACE condition args are [_medic, _patient, _bodyPart].
params ["_medic", "_patient"];
if (isNull _patient || {isNull _medic}) exitWith { false };
if !(missionNamespace getVariable ["ACME_sys_hang", true]) exitWith { false };
if (_medic getVariable ["ACME_hang_Active", false]) exitWith { false };
if (!isNull objectParent _medic) exitWith { false };

// The patient has one elevated bag workspace. Do not let a second provider enter the prep sequence while a live
// active holder owns it. Stale reservations from an ended/dead holder are ignored and replaced at commit time.
private _holder = _patient getVariable ["ACME_hang_Medic", objNull];
if (!isNull _holder && {!(_holder isEqualTo _medic)}
    && {alive _holder} && {_holder getVariable ["ACME_hang_Active", false]}) exitWith { false };

private _ivBags = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
if !(_ivBags isEqualType createHashMap) exitWith { false };
((values _ivBags) findIf { _x isEqualType [] && {count _x > 0} }) > -1
