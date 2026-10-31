/* Supplement action config checks, including the dead-casualty menu bypass. */
params ["_medic", "_action"];
private _policy = switch (_action) do {
    case "ACME_PerformThoracostomy": {["thoracostomy", false]};
    case "ACME_InsertChestTube": {["chestTube", false]};
    case "ACME_DrainFluid_ACCUVAC";
    case "ACME_DrainFluid_SuctionBag";
    case "ACME_ResealChestTube";
    case "ACME_CloseIncision";
    case "ACME_SutureChestTube": {["thoracostomy", true]};
    case "ACME_IntubateStart": {["intubation", false]};
    case "ACME_Extubate";
    case "ACME_OpenAirwayView": {["intubation", true]};
    case "ACME_VentMaskCPAP";
    case "ACME_ConnectNIVVent";
    case "ACME_ConnectETVent": {["ventilator", false]};
    case "ACME_DisconnectETVent";
    case "ACME_VentOpenPatient": {["ventilator", true]};
    case "ACME_PerformNARSPEAR": {["ncd", false]};
    case "ACME_SyringeKit_DrawPatient": {["medicationPreparation", false]};
    case "ACME_PushDoseEpi": {["pushDoseEpi", false]};
    case "ACME_OsmoBolus_HTS";
    case "ACME_OsmoBolus_Mannitol": {["htsBolus", false]};
    default {[]};
};
if (_policy isEqualTo []) exitWith {true};
[_medic, _policy select 0, _policy select 1] call ACME_fnc_procedureAllowed
