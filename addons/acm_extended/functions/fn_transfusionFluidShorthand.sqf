/* Presentation aliases only. Clinical bag/drug keys remain unchanged. */
params [["_type", "", [""]], ["_medications", [], [[]]]];
if (_medications isNotEqualTo []) exitWith {
    private _names = [];
    {
        private _name = toLowerANSI (_x param [11, ""]);
        private _abbr = switch (_name) do {
            case "calciumchloride": {"CaCl"};
            case "calciumgluconate": {"CaGlu"};
            case "tranexamicacid";
            case "txa": {"TXA"};
            case "propofol": {"PRO"};
            default {[_x param [11, ""]] call ACME_fnc_infusionName};
        };
        if (_abbr != "") then {_names pushBackUnique _abbr;};
    } forEach _medications;
    _names joinString "/"
};
switch (toLowerANSI _type) do {
    case "blood";
    case "freshblood": {"B"};
    case "plasma": {"P"};
    case "saline";
    case "acme_saliney": {"NS"};
    case "plasmalyte": {"PL"};
    case "mannitol": {"Mtol"};
    case "hts";
    case "hts3": {"HTS"};
    case "magnesium": {"Mg"};
    case "calciumchloride": {"CaCl"};
    case "calciumgluconate": {"CaGlu"};
    case "tranexamicacid";
    case "txa": {"TXA"};
    case "propofol": {"PRO"};
    case "esmolol": {"Esm"};
    case "fbtk": {"FBTK"};
    default {_type select [0,5]};
}
