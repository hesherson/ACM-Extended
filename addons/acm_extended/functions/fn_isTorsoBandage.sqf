/* Deliberately not the whole Bandage category (tourniquets/splints/devices live there too). */
params ["_medic", "_patient", "_part", "_class"];
_medic isNotEqualTo _patient && {(toLowerANSI _part) in ["body", "torso", "chest", "abdomen"]}
    && {(toLowerANSI _class) in ["basicbandage", "fielddressing", "packingbandage", "elasticbandage", "quikclot", "pressurebandage", "emergencytraumadressing"]}
