/* B278: presentation only; never use a display name or alias as a medication lookup key.
 * The optional full-name mode is for single-medication infusion titles. Existing
 * callers retain the canonical compact aliases used for mixtures and rates. */
params [["_name", "", [""]], ["_full", false, [true]]];
private _alias = switch (toLowerANSI _name) do {
    case "amiodarone": {"Ami"}; case "epinephrine": {"Epi"};
    case "norepinephrine": {"Norepi"}; case "calciumchloride": {"CaCl"};
    case "calciumgluconate": {"CaGlu"}; case "lidocaine": {"Lido"};
    case "magnesium": {"Mag"}; case "magnesiumsulfate": {"Mag"};
    case "fentanyl": {"Fent"}; case "ketamine": {"Ket"};
    case "propofol": {"Prop"}; case "rocuronium": {"Roc"};
    case "tranexamicacid"; case "txa": {"TXA"}; default {""};
};
if (!_full && {_alias != ""}) exitWith {_alias};
private _text = localize format ["STR_ACM_Circulation_Medication_%1", _name];
if (_text == "" || {_text == format ["STR_ACM_Circulation_Medication_%1", _name]}) then {
    _text = switch (toLowerANSI _name) do {
        case "calciumchloride": {"Calcium Chloride"};
        case "calciumgluconate": {"Calcium Gluconate"};
        case "tranexamicacid"; case "txa": {"Tranexamic Acid"};
        case "magnesiumsulfate": {"Magnesium Sulfate"};
        default {_name};
    };
};
_text
