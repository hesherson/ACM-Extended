/* Owner-only preparation of immutable source-funded return descriptors.
 * [mode,patient,request,bags] -> [valid,products]. No inventory mutation here.
 * Fresh products carry donor facts directly; no old session registry ID survives. */
params ["_mode","_patient","_request","_bags"];
if !(_mode in ["remove","pull","discard"] && {_request isEqualType ""} && {_request != ""} && {count _request <= 128}
    && {_bags isEqualType []} && {count _bags <= 32}) exitWith {[false,[]]};
private _products = [];
private _ok = true;
{
    if !(_x isEqualType [] && {count _x >= 7}) exitWith {_ok = false;};
    private _bag = _x;
    if (([0,1,2,3,4,5,6] findIf {isNil {_bag select _x}}) >= 0) exitWith {_ok = false;};
    _bag params ["_type","_remaining","_access","","","_blood","_volume"];
    if !(_type isEqualType "" && {_remaining isEqualType 0} && {finite _remaining} && {_remaining >= 0}
        && {_volume isEqualType 0} && {finite _volume} && {_volume > 0} && {_remaining <= _volume}
        && {_access isEqualType 0} && {finite _access} && {_blood isEqualType 0} && {finite _blood}) exitWith {_ok = false;};
    private _returned = if (_mode == "remove") then {[_remaining] call ACM_circulation_fnc_getReturnVolume} else {_remaining};
    if (_mode == "remove" && {_type == "FBTK"}) then {
        private _tol = missionNamespace getVariable ["ACME_fbtk_fullToleranceMl",1];
        if (!(_tol isEqualType 0) || {!finite _tol}) then {_tol = 1;};
        _tol = (_tol max 0) min 5;
        if (_remaining >= ((_volume - _tol) max 0)) then {_returned = _volume;};
    };
    if (_type in ["ACME_Empty","ACME_EmptySaline"]) then {_returned = 0;};
    private _fresh = [];
    if (_type == "FreshBlood") then {
        private _entry = [_bag param [7,-1],_bag param [10,[],[[]]],_blood] call ACME_fnc_freshBloodResolve;
        _fresh = if (_entry isEqualTo []) then {["freshMissingV1"]} else {["freshV1",_entry select 3,_entry select 4,_entry select 2]};
        if (_entry isNotEqualTo []) then {_blood = _entry select 2;} else {if !(_blood in [0,1,2,3,4,5,6,7]) then {_blood = -1;};};
        // Returning a partial fresh bag never rounds away donor-bearing product.
        _returned = _remaining;
    };
    if (_type == "FBTK" && {_returned > 0}) then {
        _blood = [_patient] call ACM_circulation_fnc_generateBloodType;
        _fresh = ["freshV1",alive _patient,CBA_missionTime,_blood];
        _type = "FreshBlood";
    };
    if (_returned > 0 && {_type != "FBTK"}) then {
        if (_mode != "remove" || {_type == "FreshBlood"}) then {
            private _id = format ["used_%1:%2:%3",_mode,_request,_forEachIndex];
            private _name = switch (_type) do {
                case "ACME_SalineY": {"Saline"}; case "PlasmaLyte": {"Plasma-Lyte A"};
                case "FreshBlood": {"Fresh blood"}; default {_type};
            };
            private _row = [_id,_type,_returned,_access,_blood,_volume,_name,-1];
            if (_type == "FreshBlood") then {_row pushBack _fresh;};
            _products pushBack ["used",_row];
        } else {
            private _class = [_type,_returned,_blood] call ACM_circulation_fnc_formatFluidBagName;
            if !(_class isEqualType "" && {_class != ""} && {isClass (configFile >> "CfgWeapons" >> _class)}) exitWith {_ok = false;};
            _products pushBack ["item",_class];
        };
    };
    if (_mode == "remove" && {_type == "FBTK"} && {_returned <= 0}) then {
        private _class = format ["ACM_FieldBloodTransfusionKit_%1",_volume];
        if !(isClass (configFile >> "CfgWeapons" >> _class)) exitWith {_ok = false;};
        _products pushBack ["item",_class];
    };
} forEach _bags;
if (_ok) then {_ok = [_products] call ACME_fnc_resourceReturnProductsValid;};
[_ok,if (_ok) then {_products} else {[]}]
