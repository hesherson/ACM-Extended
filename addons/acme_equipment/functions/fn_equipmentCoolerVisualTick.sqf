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
        if (!isNull _visual) then {
            _visual setPosWorld getPosWorldVisual _box;
            _visual setVectorDirAndUp [vectorDirVisual _box,vectorUpVisual _box];
            _box hideObject true;
            private _slots = switch (typeOf _box) do {
                case "ACME_BloodCoolerBox_CSWB1U": {[[0,-0.006,0.023]]};
                case "ACME_BloodCoolerBox_CSWB2U": {[[-0.00675,-0.0323,-0.0008],[-0.00675,-0.0323,0.0372]]};
                default {[[-0.01785,-0.0956,0.00575],[-0.01985,-0.0614,0.00775],[-0.01735,-0.0272,0.00675],[-0.01935,0.007,0.00525]]};
            };
            private _cargo = itemCargo _box select {([_x] call ACME_fnc_coolerBagVolume) > 0};
            _cargo sort true;
            private _wanted = _cargo select [0,count _slots];
            private _drawn = _box getVariable ["ACME_eqBagVisuals",[]];
            if (_wanted isNotEqualTo (_drawn apply {_x select 0})) then {
                {_x params ["","_prop"];deleteVehicle _prop;} forEach _drawn;
                _drawn = _wanted apply {
                    private _volume = [_x] call ACME_fnc_coolerBagVolume;
                    private _path = format ["\z\ace\addons\medical_treatment\data\IVBag_%1ml.p3d",_volume];
                    private _prop = createSimpleObject [_path,getPosWorld _visual,true];
                    private _texture = if ((_x find "ACME_SpoiledBlood") == 0) then {
                        "#(argb,8,8,3)color(0.22,0.12,0.09,1,CO)"
                    } else {format ["\z\ace\addons\medical_treatment\data\IVBag_blood_%1ml_ca.paa",_volume]};
                    _prop setObjectTexture [0,_texture];
                    _prop setObjectScale (([0.56,0.74,0.78] select (((count _slots) - 1) min 2)) * ([1,0.8] select (_volume > 500)));
                    [_x,_prop]
                };
                _box setVariable ["ACME_eqBagVisuals",_drawn];
            };
            private _direction = vectorDirVisual _box;
            private _up = vectorUpVisual _box;
            {
                _x params ["","_prop"];
                private _offset = _slots select _forEachIndex;
                _prop setPosWorld (_box modelToWorldVisualWorld _offset);
                _prop setVectorDirAndUp (if (count _slots == 4) then {[_direction vectorCrossProduct _up,_direction vectorMultiply -1]} else {[_direction,_up]});
            } forEach _drawn;
        };
    } else {
        if (!isNull _visual) then {
            deleteVehicle _visual;
            {_x params ["","_prop"];deleteVehicle _prop;} forEach (_box getVariable ["ACME_eqBagVisuals",[]]);
            _box setVariable ["ACME_eqOpenVisual",objNull];
            _box setVariable ["ACME_eqBagVisuals",[]];
        };
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
