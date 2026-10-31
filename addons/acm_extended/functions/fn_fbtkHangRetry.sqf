/* Bounded retransmission. Unknown outcome never creates a speculative refund. */
params ["_m","_token"];
if (isNull _m || {!local _m}) exitWith {};
private _p=_m getVariable ["ACME_fbtkPending",[]];
if (count _p<5 || {(_p select 1)!=_token}) exitWith {};
if (serverTime>((_p select 3) select 6)+2) exitWith {
    [_p select 2,false] call ACME_fnc_treatmentSupplyRefund;
    _m setVariable ["ACME_fbtkPending",[]];
    ["Collection request timed out. Recheck the line.",3,_m] call ace_common_fnc_displayTextStructured;
};
[_p select 0,"fbtkHang",_p select 3] call ACME_fnc_ownerDispatch;
[{_this call ACME_fnc_fbtkHangRetry;},[_m,_token],1] call CBA_fnc_waitAndExecute;
