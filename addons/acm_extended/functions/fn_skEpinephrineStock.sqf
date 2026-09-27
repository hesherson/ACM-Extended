/* Refresh only the cardiac source row. Unused source volume remains drawable. */
params ["_display"];
if (isNull _display || {!isNil "ACME_infusion_pendingContext" && {!((missionNamespace getVariable ["ACME_infusion_pendingContext", []]) isEqualTo [])}}) exitWith {};
private _list = _display displayCtrl 84006;
private _row = -1;
for "_i" from 0 to ((lbSize _list) - 1) do {if ((_list lbData _i) == "EpinephrineCardiac") exitWith {_row = _i;};};
private _available = [[ACE_player] call ACME_fnc_vialHolder, "EpinephrineCardiac"] call ACME_fnc_infusionVialVolume;
if (_available > 0 && {_row < 0}) then {
    _row = _list lbAdd "Epinephrine 1:10,000 (1 mg / 10 mL)";
    _list lbSetData [_row, "EpinephrineCardiac"];
    _list lbSetPicture [_row, getText (configFile >> "CfgWeapons" >> "ACME_Vial_EpinephrineCardiac" >> "picture")];
};
if (_row >= 0) then {_list lbSetTooltip [_row, "Epinephrine 1:10,000 (0.1 mg/mL)."];};
