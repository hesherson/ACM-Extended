/* B236. Retire only this provider's exact binding before settling/refunding.
   Same-token owner replies remain idempotent through the clinical receipt log. */
params ["_medic","_token","_receipt"];
if (isNull _medic || {!local _medic} || {count _receipt!=4}) exitWith {};
private _scopes=missionNamespace getVariable ["ACME_IV_SupplyScopes",createHashMap];
private _id=_receipt select 3;
private _scope=_scopes getOrDefault [_id,[]];
if (count _scope==8 && {(_scope select 7) isEqualTo _medic} && {(_scope select 4)==_token}
    && {(_scope select 0) isEqualTo _receipt}) then {_scopes deleteAt _id;};
private _bindings=+(_medic getVariable ["ACME_IV_SupplyBindings",[]]);
_bindings=_bindings select {!((_x param [4,""])==_token && {(_x param [0,[]]) isEqualTo _receipt})};
_medic setVariable ["ACME_IV_SupplyBindings",_bindings,true];
