/* B275: one read-only presentation for a physical UID, shared by both native bag panes.
 * A fitted downstream warmer colors only the bag currently delivering fluid.
 * No inventory discovery, state mutation, list rebuild or additional UI worker. */
params ["_patient","_part","_bag",["_label",""]];
_bag params [["_type",""],["_remaining",0],"",["_site",-1],["_iv",true],["_bloodType",-1],["_volume",0],"",["_uid",""]];
if (_label == "") then {
    private _class = [_type,_volume,_bloodType] call ACM_circulation_fnc_formatFluidBagName;
    private _cfg = configFile >> "CfgWeapons" >> _class;
    _label = getText (_cfg >> "shortName");
    if (_label == "") then {_label = getText (_cfg >> "displayName");};
    if (_label == "") then {_label = _type;};
};
{_label = [_label,_x,""] call CBA_fnc_replace;} forEach [" [Warmed]"," [Cooled]"," [Y]"," [PiB]"," · Primary"," · Secondary"];
if (_type == "ACME_Empty") then {_label = "[Empty Blood Bag]";};
if (_type == "ACME_EmptySaline") then {_label = "[Empty Saline Bag]";};
if (_type in ["Saline","ACME_SalineY"]) then {_label = "Saline";};
if !(_type in ["ACME_Empty","ACME_EmptySaline"]) then {_label = [_label,_remaining] call ACME_fnc_fluidLabelVolume;};
private _isY = [_patient,_part,_iv,_site] call ACME_fnc_isYLineAccess;
private _role = [_patient,_part,_uid] call ACME_fnc_piggybackRole;
if (_isY) then {_label = _label + " [Y]";};
if (_role != "") then {_label = _label + " [PiB]" + format [" · %1",_role];};
private _partIdx = ["head","body","leftarm","rightarm","leftleg","rightleg"] find toLowerANSI _part;
private _flowing = false;
if (_partIdx >= 0 && {_remaining > 0.01}) then {
    private _siteOpen = if (_iv) then {
        (((_patient getVariable ["ACM_circulation_FluidBagsFlow_IV",[[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1]]]) param [_partIdx,[]]) param [_site,0]) > 0
    } else {((_patient getVariable ["ACM_circulation_FluidBagsFlow_IO",[1,1,1,1,1,1]]) param [_partIdx,0]) > 0};
    private _clamp = -1;
    private _entryIndex = (_patient getVariable ["ACME_infusion_BagMedications",[]]) findIf {(_x param [23,""]) == _uid};
    if (_entryIndex >= 0) then {
        private _entry = (_patient getVariable ["ACME_infusion_BagMedications",[]]) select _entryIndex;
        private _drops = _entry param [21,60];
        if ((_entry param [22,-1]) >= 0) then {_drops = [(_entry param [22,0]) max 0 min 1] call ACME_fnc_clampPositionToDrops;};
        _clamp = (_drops / ((_entry param [20,20]) max 1)) / 60;
    };
    _flowing = _siteOpen && {([_patient,_partIdx,_iv,_site,_clamp,_uid] call ACM_circulation_fnc_getIVFlowRate) > 0};
    ([_patient,_part,_iv,_site,_uid] call ACME_fnc_piggybackFlow) params ["_held","_secondary"];
    if (_held) then {_flowing = false;};
    if (_isY) then {
        private _serviceState = [_patient,_part,_iv,_site] call ACME_fnc_yServiceState;
        private _service = _serviceState param [5,""];
        private _primed = _serviceState param [4,true];
        if (_type in ["Saline","ACME_SalineY","ACME_EmptySaline"]) then {
            _flowing = _flowing && {_service != ""};
        } else {if (_service != "" || {!_primed}) then {_flowing = false;};};
    };
};
if (_flowing) then {
    private _co = [_patient] call ace_medical_status_fnc_getCardiacOutput;
    if !(_co isEqualType 0 && {finite _co}) then {_co = 0;};
    private _perfusing = ([_patient] call ACM_core_fnc_cprActive) || {
        !(_patient getVariable ["ace_medical_inCardiacArrest",false]) && {_co > 0.0001}
    };
    _flowing = _perfusing && {
        ([_patient,_part,if (_iv) then {_site} else {-1}] call ACME_fnc_medicationLineFraction) > 0
    } && {!(_uid in (_patient getVariable ["ACME_detachedBags",[]]))}
        && {!(_uid in (_patient getVariable ["ACME_IV_DisconnectedBagUIDs",[]]))};
};
private _color = if (_role != "") then {[0.79,0.73,0.89,1]} else {[1,1,1,1]};
private _thermal = "";
if ([_patient,_part,_iv,_site] call ACME_fnc_lineWarmer) then {
    _thermal = "LW Quantum · Inline";
    if (_flowing && {_type in ["Blood","FreshBlood","Saline","ACME_SalineY","Plasma"]}) then {
        _color = [1,0.55,0.13,1];
        _thermal = "LW Quantum · Warming" + ([".","..","..."] select ((floor diag_tickTime) mod 3));
    };
} else {
    if (_type in ["Blood","FreshBlood"] && {_patient getVariable ["ACME_coldBlood",false]}) then {_color = [0.45,0.72,1,1];};
};
[_label,_color,_thermal,_role,_flowing]
