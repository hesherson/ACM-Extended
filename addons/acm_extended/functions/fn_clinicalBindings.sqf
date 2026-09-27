/* Read-only. Returns [allPresent, [[function, expectedMarkerFound], ...]]. */
private _checks = [];
{
    _x params ["_name", "_marker"];
    private _code = missionNamespace getVariable [_name, {}];
    private _ok = _code isEqualType {} && {(toLowerANSI str _code find toLowerANSI _marker) >= 0};
    _checks pushBack [_name, _ok];
    } forEach [
    ["ACM_core_fnc_onCardiacArrest", "NA4:onCardiacArrest"],
    ["ACM_core_fnc_onUnconscious", "NA4:onUnconscious"],
    ["ACM_circulation_fnc_setIVLocal", "NA4:setIVLocal"],
    ["ACM_circulation_fnc_getIVFlowRate", "NA4:getIVFlowRate"],
    ["ace_medical_status_fnc_getBloodPressure", "NA3:getBloodPressure"],
    ["ace_medical_status_fnc_getBloodVolumeChange", "NA4:getBloodVolumeChange"],
    ["ace_medical_vitals_fnc_updateHeartRate", "NA3:updateHeartRate"],
    ["ace_medical_vitals_fnc_updatePeripheralResistance", "NA3:updatePeripheralResistance"],
    ["ACM_circulation_fnc_updateCirculationState", "NA4:updateCirculationState"],
    ["ACM_breathing_fnc_updateRespirationRate", "NA3:updateRespirationRate"],
    ["ACM_breathing_fnc_getEtCO2", "NA3:getEtCO2"],
    ["ace_medical_treatment_fnc_medicationLocal", "NA3:medicationLocal"],
    ["ace_medical_damage_fnc_woundsHandlerBase", "NA3:woundsHandlerBase"],
    ["ace_medical_fnc_serializeState", "NA3:serializeState"],
    ["ace_medical_fnc_deserializeState", "NA4:deserializeState"],
    ["ACM_circulation_fnc_handleCardiacArrest", "NA4:handleCardiacArrest"],
    ["ACM_circulation_fnc_handleReversibleCardiacArrest", "NA4:handleReversibleCardiacArrest"],
    ["ace_medical_treatment_fnc_ivBagLocal", "NA3:ivBagLocal"],
    ["ace_medical_vitals_fnc_handleUnitVitals", "NA3:handleUnitVitals"],
    ["ACM_circulation_fnc_getBloodVolumeChange", "B106:volumeCanonical"],
    ["ace_medical_status_fnc_getBloodVolumeChange", "B106:volumeBridge"],
    ["ACM_circulation_fnc_setIV", "B106:setIVReconciled"],
    ["ACM_airway_fnc_handleAirway", "B106:airwayWakeGuard"],
    ["ACM_airway_fnc_handleAirwayCollapse", "B125:airwayCollapseWakeClear"],
    ["ACM_core_fnc_getUpPrompt", "B106:getUpLifecycle"],
    ["ACM_core_fnc_addVehiclePatientActions", "B106:vehicleUnloadGuard"],
    ["ACM_disability_fnc_handleFracture", "B106:fracturePainChance"],
    ["ACM_damage_fnc_wrapBodyPartLocal", "B106:wrappedWoundReopen"],
    ["ace_dragging_fnc_canCarry", "B106:ace321Carry"],
    ["ace_dragging_fnc_canDrag", "B106:ace321Drag"],
    ["ace_interact_menu_fnc_compileMenuSelfAction", "B106:ace321SelfMenu"]
];
private _all = (_checks findIf {!(_x select 1)}) < 0;
[_all, _checks]
