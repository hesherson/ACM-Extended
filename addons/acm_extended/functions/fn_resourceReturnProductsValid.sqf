/* JSON-safe canonical source proof, shared by server admission and receiver. */
params ["_products"];
if (isNil "_products") exitWith {false};
if !(_products isEqualType [] && {count _products <= 32}) exitWith {false};
private _seen = createHashMap;
private _ok = true;
{
    if !(_x isEqualType [] && {count _x == 2}) exitWith {_ok = false;};
    if (isNil {_x select 0} || {isNil {_x select 1}}) exitWith {_ok = false;};
    _x params ["_kind","_value"];
    if !(_kind in ["item","used"]) exitWith {_ok = false;};
    if (_kind == "item") then {
        if !(_value isEqualType "" && {count _value > 0} && {count _value <= 256}
            && {isClass (configFile >> "CfgWeapons" >> _value)}) exitWith {_ok = false;};
    } else {
        if !(_value isEqualType [] && {count _value in [8,9,10]}) exitWith {_ok = false;};
        if (([0,1,2,3,4,5,6,7] findIf {isNil {_value select _x}}) >= 0) exitWith {_ok = false;};
        _value params ["_id","_type","_remaining","_access","_blood","_volume","_name","_freshId"];
        private _bagOnly = count _value == 10;
        if (_bagOnly && {isNil {_value select 9} || {(_value select 9) isNotEqualTo "bagOnly"}}) exitWith {_ok = false;};
        if !(_id isEqualType "" && {count _id > 0} && {count _id <= 256} && {!(_id in _seen)}
            && {_type isEqualType ""} && {count _type > 0} && {count _type <= 128}
            && {!(_type in ["FBTK","ACME_Empty","ACME_EmptySaline","ACME_Propofol"])}
            && {_remaining isEqualType 0} && {finite _remaining} && {_remaining > 0}
            && {_volume isEqualType 0} && {finite _volume} && {_volume > 0} && {_volume <= 1e6} && {_remaining <= _volume}
            && {_access isEqualType 0} && {finite _access} && {_access == floor _access} && {_access >= 0} && {_access <= 32}
            && {_blood isEqualType 0} && {finite _blood} && {_blood == floor _blood} && {_blood >= -1} && {_blood <= 7}
            && {_name isEqualType ""} && {count _name <= 256} && {_freshId isEqualTo -1}) exitWith {_ok = false;};
        if (_type == "FreshBlood") then {
            if !(count _value in [9,10]) exitWith {_ok = false;};
            private _meta = _value select 8;
            if (isNil "_meta") exitWith {_ok = false;};
            if (_meta isNotEqualTo ["freshMissingV1"]) then {
                if (_blood < 0) exitWith {_ok = false;};
                if !(_meta isEqualType [] && {count _meta == 4}) exitWith {_ok = false;};
                if (([0,1,2,3] findIf {isNil {_meta select _x}}) >= 0) exitWith {_ok = false;};
                if ((_meta select 0) isNotEqualTo "freshV1" || {!((_meta select 1) isEqualType true)}
                    || {!((_meta select 2) isEqualType 0)} || {!finite (_meta select 2)} || {abs (_meta select 2) > 1e9}
                    || {(_meta select 3) isNotEqualTo _blood}) exitWith {_ok = false;};
            };
        } else {
            if (_bagOnly) then {
                if (isNil {_value select 8} || {(_value select 8) isNotEqualTo []}) then {_ok = false;};
            } else {if (count _value != 8) then {_ok = false;};};
        };
        _seen set [_id,true];
    };
    if (!_ok) exitWith {};
} forEach _products;
_ok
