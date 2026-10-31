#include "..\script_component.hpp"
/*
 * Author: ACM Extended Fork
 * Circulation-owned mutation endpoint for ACM's IV-bag state map.
 *
 * B204: structured public writes are deduplicated on the patient owner. The map is mutable by reference, so the
 * cache stores a serialized fingerprint rather than the HashMap itself.
 */
params [
    ["_patient", objNull, [objNull]],
    ["_bags", createHashMap, [createHashMap]],
    ["_public", true, [true]]
];
if (isNull _patient) exitWith {false};

if (!_public || {!local _patient}) exitWith {
    // Local staging must not retain an old publication fingerprint. The mutable bag map may have changed
    // and returned to that old value between two public commits.
    _patient setVariable ["ACME_ivBagsPublishedSig", nil, false];
    _patient setVariable [QGVAR(IV_Bags), _bags, _public];
    true
};

private _sig = str _bags;
private _old = _patient getVariable [QGVAR(IV_Bags), createHashMap];
private _published = _patient getVariable ["ACME_ivBagsPublishedSig", ""];
if ((str _old) isEqualTo _sig && {_published isEqualTo _sig}) exitWith {true};

_patient setVariable ["ACME_ivBagsPublishedSig", _sig, false];
_patient setVariable [QGVAR(IV_Bags), _bags, true];

if (missionNamespace getVariable ["ACME_net_count", false]) then {
    private _sent = missionNamespace getVariable ["ACME_net_sent", createHashMap];
    _sent set ["ACM_circulation_IV_Bags", (_sent getOrDefault ["ACM_circulation_IV_Bags", 0]) + 1];
    missionNamespace setVariable ["ACME_net_sent", _sent];
};
true
