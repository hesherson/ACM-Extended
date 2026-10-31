/* Built-in FBTK tubing: one click, exact selected inventory, no staging timer.
   The owner still validates IV-only access and commits once before consumption. */
private _d=findDisplay 86000;
private _m=ACE_player;
if (isNull _d || {isNull _m} || {!local _m}) exitWith {false};
if ((_m getVariable ["ACME_fbtkPending",[]]) isNotEqualTo []) exitWith {false};
private _list=_d displayCtrl 86005;private _i=lbCurSel _list;
if (_i<0) exitWith {false};
private _class=((_list lbData _i) splitString "|") param [0,""];
if !(_class in ["ACM_FieldBloodTransfusionKit_250","ACM_FieldBloodTransfusionKit_500"]) exitWith {false};
private _p=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull];
private _part=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""];
private _iv=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true];
private _site=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1];
if (!_iv) exitWith {["FBTK requires IV access.",3,_m] call ace_common_fnc_displayTextStructured;false};
private _reason=[_p,_part,true,_site] call ACME_fnc_preparedAttachBlockReason;
if (_reason!="") exitWith {
    [if (_reason=="line-occupied") then {"There is already a bag on this line."} else {"Select a free IV line."},3,_m] call ace_common_fnc_displayTextStructured;
    false
};
private _mode=missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_Inventory",0];
private _receipt=[_m,_p,_class,_mode,objectParent _m] call ACME_fnc_transfusionTakeSelected;
if (_receipt isEqualTo []) exitWith {["That bag is no longer available.",3,_m] call ace_common_fnc_displayTextStructured;false};
private _epoch=[_p] call ACME_fnc_clinicalEpoch;
private _token="fbtk:"+(_receipt select 3);private _deadline=serverTime+10;
private _args=[_m,_part,_site,_class,_token,_epoch,_deadline];
_m setVariable ["ACME_fbtkPending",[_p,_token,_receipt,_args,_d]];
[_p,"fbtkHang",_args] call ACME_fnc_ownerDispatch;
[{_this call ACME_fnc_fbtkHangRetry;},[_m,_token],1] call CBA_fnc_waitAndExecute;
true
