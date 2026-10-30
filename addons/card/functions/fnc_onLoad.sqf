#include "..\ui\idc_macros.hpp"
params ["_display", ["_page", 1]];
private _context = uiNamespace getVariable ["DD1380_context", []];
if (count _context != 7 || {!(_page in [1, 2])}) exitWith {_display closeDisplay 0;};
_context params ["_medic", "_patient", "_epoch"];
if (isNull _patient || {!(_medic isEqualTo ACE_player)}
    || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {_display closeDisplay 0;};
_display setVariable ["DD1380_context", _context];
_display setVariable ["DD1380_page", _page];
uiNamespace setVariable ["TCCC_Card", _page];
private _draft = _context select 6;
{
    private _index = _x;
    {
        if (_index in [0, 1, 3]) then {
            (_display displayCtrl _x) cbSetChecked _y;
        } else {
            (_display displayCtrl _x) ctrlSetText _y;
        };
    } forEach (_draft select _index);
} forEach (if (_page == 1) then {[0, 1, 2]} else {[0, 3, 4]});

if (_page == 1) then {
    (_display displayCtrl IDC_DD1380_PATIENT_NAME) ctrlSetText ([_patient] call ace_common_fnc_getName);
    (_display displayCtrl IDC_DD1380_PATIENT_LAST4) ctrlSetText (((name _patient) call ace_dogtags_fnc_ssn) select [7, 4]);
    (_display displayCtrl IDC_DD1380_PATIENT_DATE) ctrlSetText ([date] call DD1380_card_fnc_getDate);
    private _times = _patient getVariable ["ACM_disability_Tourniquet_Time", []];
    if !(_times isEqualType []) then {_times = [];};
    {
        _x params ["_part", "_index", "_typeId", "_timeId"];
        private _applied = [_patient, _part] call ace_medical_treatment_fnc_hasTourniquetAppliedTo;
        private _time = _times param [_index, ""];
        if !(_time isEqualType "") then {_time = "";};
        (_display displayCtrl _typeId) ctrlSetText (if (_applied) then {"CAT"} else {""});
        (_display displayCtrl _timeId) ctrlSetText (if (_applied) then {_time} else {""});
    } forEach [
        ["leftarm", 2, IDC_DD1380_L_ARM_TYPE, IDC_DD1380_L_ARM_TIME],
        ["rightarm", 3, IDC_DD1380_R_ARM_TYPE, IDC_DD1380_R_ARM_TIME],
        ["leftleg", 4, IDC_DD1380_L_LEG_TYPE, IDC_DD1380_L_LEG_TIME],
        ["rightleg", 5, IDC_DD1380_R_LEG_TYPE, IDC_DD1380_R_LEG_TIME]
    ];
};
