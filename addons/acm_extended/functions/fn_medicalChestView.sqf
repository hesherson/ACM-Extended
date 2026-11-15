/* A client reports its confirmed native Gear session to the server. */
params [
    ["_cargo", objNull, [objNull]], ["_actor", objNull, [objNull]],
    ["_revision", -1, [0]], ["_viewing", false, [false]]
];
if (!isServer || {isNull _actor} || {isNull _cargo} || {!(_cargo isKindOf "ACME_MedicalChestCargo")}
    || {isRemoteExecuted && {remoteExecutedOwner != owner _actor}}) exitWith {};
private _chest = _cargo getVariable ["ACME_medicalChestAnchor", objNull];
if (isNull _chest || {(_chest getVariable ["ACME_medicalChestCargo", objNull]) isNotEqualTo _cargo}
    || {(_chest getVariable ["ACME_medicalChestState", []]) isNotEqualTo [_revision, true]}
    || {_chest getVariable ["ACME_medicalChestTransition", false]}) exitWith {};

private _viewers = _chest getVariable ["ACME_medicalChestViewers", []];
private _index = _viewers findIf {(_x select 0) isEqualTo _actor};
if (!_viewing) exitWith {
    if (_index >= 0) then {
        _viewers deleteAt _index;
        _chest setVariable ["ACME_medicalChestViewers", _viewers];
    };
};
if (!alive _actor || {_actor getVariable ["ACE_isUnconscious", false]}
    || {_actor distance _cargo > 4.5}) exitWith {};
private _entry = [_actor, owner _actor, CBA_missionTime + 3];
if (_index >= 0) then {_viewers set [_index, _entry];} else {_viewers pushBack _entry;};
_chest setVariable ["ACME_medicalChestViewers", _viewers];

if ((_chest getVariable ["ACME_medicalChestDrawerPFH", -1]) < 0) then {
    private _handle = [ACME_fnc_medicalChestDrawerTick, 0.03, [_chest, _cargo, _revision, CBA_missionTime]] call CBA_fnc_addPerFrameHandler;
    _chest setVariable ["ACME_medicalChestDrawerPFH", _handle];
};
