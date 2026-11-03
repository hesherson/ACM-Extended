/* Spoilage replaces each bag in its existing native container, even when the kit is full.
   It never creates a ground holder, and a failed removal never authorizes a replacement. */
params ["_unit",["_rem",[]],["_add",[]]];
if (isNull _unit || {!local _unit}) exitWith {};
private _spoiled=0;
{
    private _new=_x;
    private _old=_rem param [_forEachIndex,""];
    if ((_new find "ACME_SpoiledBlood")==0) then {
        private _containers=[uniformContainer _unit,vestContainer _unit,backpackContainer _unit] select {!isNull _x};
        private _destination=(_containers select {_old in itemCargo _x}) param [0,_containers param [0,objNull]];
        if (!isNull _destination && {[_unit,_old] call ACME_fnc_itemTake}) then {
            _destination addItemCargoGlobal [_new,1];_spoiled=_spoiled+1;
        };
    } else {
        if (_old!="") then {[_unit,_old] call ACME_fnc_itemTake;};
        if (_unit canAdd _new) then {_unit addItem _new;} else {
            private _holder=createVehicle ["GroundWeaponHolder",getPosATL _unit,[],0.5,"CAN_COLLIDE"];
            _holder addItemCargoGlobal [_new,1];
        };
    };
} forEach _add;
if (_spoiled>0 && {_unit isEqualTo ACE_player}) then {
    [format ["%1 blood bag(s) lost the cold chain and spoiled. Spoiled bags remain in your kit.",_spoiled],3] call ace_common_fnc_displayTextStructured;
};
