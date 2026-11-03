/* The mission preset changes duration, never capacity or custody identity. */
params ["_class"];
if !(missionNamespace getVariable ["ACME_persistentCampaignTiming",false]) exitWith {
    getNumber(configFile >> "CfgWeapons" >> _class >> "ACME_coolerColdChainTime")
};
private _index=["ACME_BloodCooler_CSWB1U","ACME_BloodCooler_CSWB2U","ACME_BloodCooler_CSWB4U"] find _class;
if (_index<0) exitWith {0};
private _keys=["ACME_persistentCooler1Hours","ACME_persistentCooler2Hours","ACME_persistentCooler4Hours"];
3600*(missionNamespace getVariable [_keys select _index,[48,24,72] select _index])
