// Client-only visual registration. Clinical dose handling remains owned by ACM/ACE.
if (hasInterface) then {
    // Local medication receipt is authoritative for the five-minute analgesic ketamine perception window. Any new
    // IV/IM/esketamine dose refreshes the window without changing ACM/ACE pharmacokinetics.
    ["ace_medical_treatment_medicationLocal", {
        params ["_patient", "_bodyPart", "_medication", "_dose", "_injection"];
        if (isNull _patient || {_patient != player} || {!(_medication isEqualType "")}) exitWith {};
        if ((toLowerANSI _medication) in ["ketamine","ketamine_iv","esketamine"]) then {
            uiNamespace setVariable ["ACME_VFX_KetLastDoseAt",diag_tickTime];
        };
    }] call CBA_fnc_addEventHandler;
    [{call ACME_fnc_visualFxTick}, (missionNamespace getVariable ["ACME_visualFx_updateSec",0.12]), []] call CBA_fnc_addPerFrameHandler;
};
