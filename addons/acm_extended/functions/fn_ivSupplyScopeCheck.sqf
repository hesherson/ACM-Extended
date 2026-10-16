/* B236. -1 = binding has not replicated yet (retry, do not reject/refund);
   0 = malformed or different scope; 1 = exact provider-issued reservation.
   The clinical owner still validates the live catheter/epoch/timing separately. */
params ["_medic","_patient","_uid","_action","_token","_epoch","_deadline","_receipt"];
if !(_receipt isEqualType [] && {count _receipt==4}
    && {(_receipt select 0) isEqualType objNull} && {(_receipt select 1) isEqualType ""}
    && {(_receipt select 2) isEqualType objNull} && {(_receipt select 3) isEqualType ""}
    && {(_receipt select 3)!=""} && {count (_receipt select 3)<=120}) exitWith {0};
private _item=switch (_action) do {case "flush":{"ACM_SalineFlush_10"};case "field14":{"ACM_IV_14g"};case "field16":{"ACM_IV_16g"};default{""};};
if (_item=="" || {(_receipt select 1)!=_item}) exitWith {0};
private _bindings=_medic getVariable ["ACME_IV_SupplyBindings",[]];
if !(_bindings isEqualType [] && {count _bindings<=64}) exitWith {0};
private _i=_bindings findIf {_x isEqualType [] && {count _x==8}
    && {(_x select 0) isEqualType []} && {count (_x select 0)==4}
    && {((_x select 0) param [3,""])==(_receipt select 3)}};
if (_i<0) exitWith {-1};
if ((_bindings select _i) isEqualTo [_receipt,_patient,_uid,_action,_token,_epoch,_deadline,_medic]) then {1} else {0}
