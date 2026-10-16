/* One lifecycle bridge per machine. Owner transfer resumes only a live exact
 * floor context; loss retires the local worker without clearing the new owner. */
if (missionNamespace getVariable ["ACME_flightContainmentInstalled",false]) exitWith {};
missionNamespace setVariable ["ACME_flightContainmentInstalled",true];
private _handler = ["CAManBase","Local", {
    params ["_patient","_local"];
    private _ticket = (_patient getVariable ["ACME_flightContainmentLocalSerial",0]) + 1;
    _patient setVariable ["ACME_flightContainmentLocalSerial",_ticket,false];
    if (!_local) exitWith {[_patient,-1,true] call ACME_fnc_flightContainmentStop;};
    private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
    // Public context can arrive after Local. Bounded adoption handles that order
    // without an endless scanner or accepting an old owner's later callback.
    {
        [{
            params ["_patient","_ticket","_epoch","_owner"];
            if (!local _patient || {clientOwner != _owner}
                || {(_patient getVariable ["ACME_flightContainmentLocalSerial",-1]) != _ticket}
                || {([_patient] call ACME_fnc_clinicalEpoch) != _epoch}) exitWith {};
            if !((_patient getVariable ["ACME_flightContainmentContext",[]]) isEqualTo []) then {
                [_patient,true] call ACME_fnc_flightContainmentBegin;
            };
        },[_patient,_ticket,_epoch,clientOwner],_x] call CBA_fnc_waitAndExecute;
    } forEach [0,0.5,2];
},true,[],true] call CBA_fnc_addClassEventHandler;
missionNamespace setVariable ["ACME_flightContainmentLocalHandler",_handler];
