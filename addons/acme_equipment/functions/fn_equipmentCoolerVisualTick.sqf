/* Keep the one cargo/ledger object. Only the presentation changes; concurrent viewers share its open state. */
private _boxes=missionNamespace getVariable ["ACME_eqCoolerVisuals",[]];
{
    private _box=_x;if (isNull _box) then {continue;};
    private _visual=_box getVariable ["ACME_eqOpenVisual",objNull];
    private _open=_box getVariable ["ACME_eqCoolerOpen",false] && {ACE_player distance _box<120};
    if (_open) then {
        if (isNull _visual) then {
            private _index=["ACME_BloodCoolerBox_CSWB1U","ACME_BloodCoolerBox_CSWB2U","ACME_BloodCoolerBox_CSWB4U"] find (typeOf _box);
            if (_index>=0) then {
                private _model=format ["\acme_bloodcooler\bloodcooler%1u_open.p3d",[1,2,4] select _index];
                _visual=createSimpleObject [_model,getPosWorld _box,true];
                _box setVariable ["ACME_eqOpenVisual",_visual];
                _visual disableCollisionWith _box;
            };
        };
        if (!isNull _visual) then {_visual setPosWorld getPosWorldVisual _box;_visual setVectorDirAndUp [vectorDirVisual _box,vectorUpVisual _box];_box hideObject true;};
    } else {
        if (!isNull _visual) then {deleteVehicle _visual;_box setVariable ["ACME_eqOpenVisual",objNull];};
        _box hideObject false;
    };
} forEach _boxes;
missionNamespace setVariable ["ACME_eqCoolerVisuals",_boxes select {!isNull _x}];
private _box=uiNamespace getVariable ["ACME_CLR_Box",objNull];
if (!isNull _box && {!isNull (uiNamespace getVariable ["ACME_CLR_DLG",displayNull])}) then {
    if (!alive ACE_player || {ACE_player distance _box>4.5} || {_box getVariable ["ACME_coolerRetired",false]} || {_box getVariable ["ACME_coolerPacking",false]}) then {closeDialog 0;} else {
        if (diag_tickTime>=(_box getVariable ["ACME_eqHeartbeat",0])) then {_box setVariable ["ACME_eqHeartbeat",diag_tickTime+2];[ACE_player,_box,true] remoteExecCall ["ACME_fnc_equipmentCoolerLease",2];};
        call ACME_fnc_coolerRefresh;
    };
};

{
    if ((_x getVariable ["ACME_eq_kind",""])=="vent") then {[_x] call ACME_fnc_equipmentVentScreen;};
} forEach (nearestObjects [ACE_player,["ACME_VentwaySparrow_Bare"],8]);

private _cargo=uiNamespace getVariable ["ACME_eqCargoBox",objNull];
if (!isNull _cargo && {!isNull findDisplay 602} && {diag_tickTime>=(_cargo getVariable ["ACME_eqCargoHeartbeat",0])}) then {
    _cargo setVariable ["ACME_eqCargoHeartbeat",diag_tickTime+2];
    [ACE_player,_cargo,true] remoteExecCall ["ACME_fnc_equipmentCoolerLease",2];
};
