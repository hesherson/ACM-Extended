/* Bounded, read-only presentation projection. No debug physiology or medication remainders. */
params ["_context"];
if !([_context] call ACME_fnc_reactMedicalValid) exitWith {createHashMap};
_context params ["_medic","_patient"];
private _accesses = [];
private _budget = 128;
private _truncated = false;
private _bagsMap = _patient getVariable ["ACM_circulation_IV_Bags",createHashMap];
if !(_bagsMap isEqualType createHashMap) then {_bagsMap = createHashMap;};
{
    private _part = _x;
    private _partName = ["Head / neck","Torso","Left arm","Right arm","Left leg","Right leg"] select _forEachIndex;
    private _partBags = _bagsMap getOrDefault [_part,[]];
    if !(_partBags isEqualType []) then {_partBags = [];};
    {
        _x params ["_iv","_site"];
        if ([_patient,_part,_iv,_site] call ACME_fnc_transfusionAccessValid) then {
            private _bags = [];
            {
                private _bag = _x;
                if (_bag isEqualType [] && {count _bag >= 5}
                    && {(_bag param [0,0]) isEqualType ""}
                    && {(_bag param [3,-1]) isEqualTo _site} && {(_bag param [4,false]) isEqualTo _iv}) then {
                    // Match the native menu's replacement of spent Y-line placeholders.
                    private _type = _bag select 0;
                    private _replaced = false;
                    if (_type in ["ACME_Empty","ACME_EmptySaline"]) then {
                        private _realTypes = if (_type == "ACME_Empty") then {["Blood","FreshBlood"]} else {["Saline","ACME_SalineY"]};
                        private _minimum = if (_type == "ACME_Empty") then {0.01} else {0.5};
                        _replaced = (_partBags findIf {
                            _x isEqualType [] && {(_x param [0,""]) in _realTypes}
                            && {(_x param [1,0,[0]]) > _minimum}
                            && {(_x param [3,-1]) isEqualTo _site} && {(_x param [4,false]) isEqualTo _iv}
                        }) >= 0;
                    };
                    if (!_replaced) then {
                    if (_budget > 0) then {
                    ([_patient,_part,_x] call ACME_fnc_transfusionBagPresentation) params ["_label","","_thermal","_role","_flowing"];
                    private _remaining = _x param [1,0,[0]];
                    private _capacity = _x param [6,0,[0]];
                    if !(finite _remaining) then {_remaining = 0;};
                    if !(finite _capacity) then {_capacity = 0;};
                    _bags pushBack createHashMapFromArray [
                        ["label",_label select [0,512]], ["remainingMl",round (_remaining max 0)],
                        ["capacityMl",round (_capacity max _remaining max 0)],
                        ["thermal",_thermal select [0,128]], ["role",_role select [0,64]],
                        ["flowing",_flowing],
                        ["marks",[round (_capacity max _remaining max 0)] call ACME_fnc_transfusionGraduations]
                    ];
                    _budget = _budget - 1;
                    } else {_truncated = true;};
                    };
                };
            } forEach _partBags;
            private _siteName = if (_iv) then {["Upper","Middle","Lower"] select _site} else {"IO"};
            _accesses pushBack createHashMapFromArray [
                ["part",_part], ["iv",_iv], ["site",_site],
                ["label",format ["%1 / %2%3",_partName,_siteName,[""," IV"] select _iv]],
                ["bags",_bags]
            ];
        };
    } forEach [[true,0],[true,1],[true,2],[false,0]];
} forEach ["head","body","leftarm","rightarm","leftleg","rightleg"];
createHashMapFromArray [
    ["view","transfusion"], ["patient",createHashMapFromArray [
        ["ref",["encode",_patient] call ACME_fnc_clinicalObjectRef],
        ["epoch",_context select 4], ["name",([_patient] call ace_common_fnc_getName) select [0,256]]
    ]],
    ["accesses",_accesses], ["truncated",_truncated],
    ["capabilities",["native-transfusion"]], ["observations",[]], ["sources",[]]
]
