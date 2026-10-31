/* The server moves an exact physical item; repeated input retries the same receipt. */
private _owner=ACE_player;
if (isNull _owner || {!local _owner} || {!alive _owner}) exitWith {};
private _pending=_owner getVariable ["ACME_coolerTake4UPending",[]];
if (_pending isNotEqualTo []) exitWith {["ACME_coolerTake4U",_pending] call CBA_fnc_serverEvent;};
private _source=[_owner] call ACME_fnc_coolerFind4U;
if (_source isEqualTo []) exitWith {["No nearby cargo holds an available Golden Hour 4U.",2] call ace_common_fnc_displayTextStructured;};
private _destination=objNull;
{if (!isNull _x) exitWith {_destination=_x;};} forEach [backpackContainer _owner,vestContainer _owner,uniformContainer _owner];
if (isNull _destination) exitWith {["Wear a container before taking the 4U.",2] call ace_common_fnc_displayTextStructured;};
private _sequence=(missionNamespace getVariable ["ACME_coolerTake4USequence",0])+1;
missionNamespace setVariable ["ACME_coolerTake4USequence",_sequence];
private _request=format ["cooler-take4:%1:%2:%3",clientOwner,diag_tickTime,_sequence];
_pending=[_owner,_source select 0,_source select 1,_source select 2,_request,
    _owner getVariable ["ACME_equipmentKitEpoch",0],_owner getVariable ["ACME_providerLocalityEpoch",0],_destination];
_owner setVariable ["ACME_coolerTake4UPending",_pending,true];
["ACME_coolerTake4U",_pending] call CBA_fnc_serverEvent;
