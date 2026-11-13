/* Cooler holdover is independent of the refrigerated product's shelf life. */
params ["_class"];
if !(["real"] call ACME_fnc_bloodTiming) exitWith {
    getNumber(configFile >> "CfgWeapons" >> _class >> "ACME_coolerColdChainTime")
};
private _index = ["ACME_BloodCooler_CSWB1U","ACME_BloodCooler_CSWB2U","ACME_BloodCooler_CSWB4U"] find _class;
if (_index < 0) exitWith {0};
private _policy = missionNamespace getVariable ["ACME_clinicalTiming",[]];
3600 * (_policy param [4+_index,[24,24,48] select _index])
