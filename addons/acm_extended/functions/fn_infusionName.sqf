/* B227: presentation only; never use the display alias as a medication lookup key. */
params [["_name", "", [""]]];
private _alias = switch (toLowerANSI _name) do {
    case "amiodarone": {"Ami"}; case "epinephrine": {"Epi"};
    case "norepinephrine": {"Norepi"}; case "calciumchloride": {"CaCl"};
    case "calciumgluconate": {"CaGlu"}; case "lidocaine": {"Lido"};
    case "magnesium": {"Mag"}; case "magnesiumsulfate": {"Mag"};
    case "fentanyl": {"Fent"}; case "ketamine": {"Ket"};
    case "propofol": {"Prop"}; case "rocuronium": {"Roc"}; default {""};
};
if (_alias != "") exitWith {_alias};
private _text = localize format ["STR_ACM_Circulation_Medication_%1", _name];
if (_text == "" || {_text == format ["STR_ACM_Circulation_Medication_%1", _name]}) then {_text = _name;};
_text
