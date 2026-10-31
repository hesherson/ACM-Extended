"""Production resource-return dependencies with explicit Arma boundaries.

Config, native inventory and wire transport are fixture inputs. Private source
and recipient decisions, conservation, ordering and validation remain live SQF.
"""
import re
from test_menu_death_lifecycle import read, adapt
from test_b156_procedure_supplies import primitives
from test_historical_medication_rows import iteration_scopes


def function(name):
    s=read(name).replace('canSuspend','false')
    s=re.sub(r'\bfinite (_\w+|\([^()]*\))',r'(\1 call _resourceFinite)',s)
    s=s.replace('local _provider','_resourceLocal').replace('local _patient','true')
    s=s.replace('uniformItems _provider','_resourceUnitItems').replace('vestItems _provider','[]').replace('backpackItems _provider','[]')
    s=s.replace('nearestObject [_provider,"WeaponHolder"]','_resourceNearHolder')
    s=re.sub(r'itemCargo (_\w+)',r'(\1 getVariable ["items",[]])',s)
    s=s.replace('isClass (configFile >> "CfgWeapons" >> _class)','(_class != "Invalid")').replace('isClass (configFile >> "CfgWeapons" >> _value)','(_value != "Invalid")')
    s=s.replace('(_placement select 1) isEqualType objNull','((_placement select 1) isEqualType profileNamespace || {(_placement select 1) isEqualType objNull})')
    return f'ACME_fnc_{name}={{'+primitives(adapt(iteration_scopes(s)))+'};'


def definitions():
    return r'''
        private _resourceFinite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
        private _resourceUnitItems=[];private _resourceLocal=true;
        private _resourceNearHolder=objNull;
        if (isNil {missionNamespace getVariable "ACME_syringeDeliveryMachineNonce"}) then {missionNamespace setVariable ["ACME_syringeDeliveryMachineNonce","machineA"];};
        if (isNil "ACM_circulation_fnc_getReturnVolume") then {ACM_circulation_fnc_getReturnVolume={params ["_ml"];floor (_ml/250)*250};};
        if (isNil "ACM_circulation_fnc_formatFluidBagName") then {ACM_circulation_fnc_formatFluidBagName={params ["_type","_volume"];format ["%1_%2",_type,_volume]};};
        if (isNil "ACM_circulation_fnc_generateBloodType") then {ACM_circulation_fnc_generateBloodType={2};};
        if (isNil "ACM_circulation_fnc_getFreshBloodEntry") then {ACM_circulation_fnc_getFreshBloodEntry={params ["_id"];[missionNamespace getVariable ["ACM_circulation_FreshBloodList",createHashMap],[_id,[]]] call _mapDefault};};
    '''+''.join(function(n) for n in ['syringeDeliveryCopy','freshBloodResolve','resourceReturnProductsValid','resourceReturnProducts','resourceReturnSource','resourceReturnReceive'])
