/* Owner-local epochs are private. Remote readers use the existing published owner period. */
params ["_actor"];
if (isNull _actor) exitWith {[]};
private _kit=_actor getVariable ["ACME_equipmentKitEpoch",0];
if !(_kit isEqualType 0) exitWith {[]};
// owner returns zero on clients. A local owner uses clientOwner directly.
if (local _actor) exitWith {[_kit,[clientOwner,_actor getVariable ["ACME_providerLocalityEpoch",0]]]};
if (!isServer) exitWith {[]};
private _period=_actor getVariable ["ACME_vent_batterySwapOwnerPeriod",[]];
if !(_period isEqualType [] && {count _period==2} && {_kit isEqualType 0}
    && {(_period select 0) isEqualTo owner _actor} && {(_period select 1) isEqualType 0}) exitWith {[]};
[_kit,+_period]
