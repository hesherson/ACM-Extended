/* Only runs while this one token is pending; no mission-wide worker. */
params ["_medic","_token"];
if (isNull _medic || {!local _medic}) exitWith {};
private _p=_medic getVariable ["ACME_IV_FinishPending",[]];
if (count _p<9 || {(_p select 1)!=_token}) exitWith {};
if (serverTime>(_p select 5)+2) exitWith {
    // Unknown result: do not recreate a syringe the patient owner may have used.
    if ((_p select 6) isNotEqualTo []) then {
        [_medic,_token,_p select 6] call ACME_fnc_ivSupplyRelease;
        [_p select 6,false] call ACME_fnc_treatmentSupplyRefund;
    };
    if ((_p select 7) call ACME_fnc_ivMinigameViewValid) then {[] call ACME_fnc_ivFieldClear;};
    _medic setVariable ["ACME_IV_FinishPending",[]];
    private _d=(_p select 7) select 0;
    if (!isNull _d) then {_d setVariable ["ACME_IV_FinishBusy",false];_d setVariable ["ACME_IV_FinishActive",[]];};
    if ((_p select 7) call ACME_fnc_ivMinigameViewValid) then {
        ["IV procedure timed out. Recheck the catheter.",3,_medic] call ace_common_fnc_displayTextStructured;
        [] call ACME_fnc_ivMinigameRefreshBandSlot;
    };
};
private _phase="begin";
private _d=(_p select 7) select 0;
if (_p select 8) then {_phase="cancel";} else {
    private _active=if (isNull _d) then {[]} else {_d getVariable ["ACME_IV_FinishActive",[]]};
    if (count _active>=3) then {_phase=if (_active select 2) then {"finish"} else {""};};
    if (!((_p select 7) call ACME_fnc_ivMinigameViewValid)) then {_phase="cancel";};
};
if (_phase!="") then {
    [_p select 0,"ivFinish",[_medic,_phase,_p select 2,_p select 3,_token,_p select 4,_p select 5,_p select 6]] call ACME_fnc_ownerDispatch;
};
[{_this call ACME_fnc_ivFinishRetry;},[_medic,_token],1] call CBA_fnc_waitAndExecute;
