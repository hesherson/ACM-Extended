params [["_cls", ""], ["_part", ""], ["_item", ""]];
private _cfg = configFile >> "ace_medical_treatment_actions" >> _cls;
if (!isClass _cfg) exitWith {[]};
private _low = toLowerANSI _cls;
private _site = [_part] call ACME_fnc_batdokPart;
private _starts = { params ["_s", "_list"]; (_list findIf { (_s find _x) == 0 }) >= 0 };
private _event = {
	params ["_name", ["_note", ""]];
	if (_note isEqualTo "") then { _note = _site };
	["event", _name, ["name", _name, "note", _note, "site", _site]]
};

private _events = [
	["cpr", "CPR"], ["aed_shock", "Defibrillation"], ["aed_applypads", "Defib pads applied"],
	["placepulseoximeter", "Pulse oximeter placed"], ["pressurecuff_attach", "BP cuff applied"],
	["acme_attachemma", "Capnometer attached"], ["usebvm", "BVM ventilation"], ["acme_connectetvent", "Ventilator connected"]
];
private _ev = _events findIf { (_low find (_x select 0)) == 0 };
if (_ev >= 0) exitWith { [(_events select _ev) select 1] call _event };

if ([_low, ["check", "inspect", "diagnose", "acme_debug", "acme_toggle", "acme_rhythm", "acme_tune", "acme_feel", "acme_assess",
	"acme_read", "acme_check", "aed_", "measure", "usestethoscope", "opentransfusion", "acme_ivminigame", "acme_openairway",
	"acme_ventopen", "acme_syringekit", "usesyringe", "acme_flush", "bodybag", "grave", "slapawake", "shakeawake", "cancelrecovery",
	"headturn", "acme_elevatehead", "acme_lowerhead", "acme_hangbag", "acme_exposechest", "acme_coverchest", "acme_inflict",
	"acme_stopdirect", "acme_manual", "begin", "recoveryposition", "acme_swap", "acme_disconnect", "acme_burp", "acme_adjust",
	"pressurecuff_remove", "removepulseoximeter", "acme_drain", "drainfluid", "acme_reseal", "resealchest", "acme_prephpmk",
	"inspectiv", "acme_autobp"]] call _starts) exitWith {[]};
if ((getText (_cfg >> "category")) isEqualTo "examine") exitWith {[]};

private _dn = getText (_cfg >> "displayName");
if ((_dn select [0, 5]) == "call ") then {
	private _r = call compile _dn;
	_dn = if (isNil "_r" || {!(_r isEqualType "")}) then {_cls} else {_r};
};
if (_dn isEqualTo "") then { _dn = _cls };

if ([_low, ["remove", "acme_remove", "extubate", "acme_extubate", "acme_unwrap"]] call _starts) exitWith { [_dn] call _event };

private _cb = toLowerANSI getText (_cfg >> "callbackSuccess");
if ((_cb find "fnc_ivbag") >= 0) exitWith {
	if (isClass (configFile >> "CfgPatches" >> "ACM_circulation")) exitWith {[]};
	private _iv = configFile >> "ace_medical_treatment" >> "IV" >> _cls;
	private _type = getText (_iv >> "type");
	private _vol = getNumber (_iv >> "volume");
	if (_vol <= 0) then { _vol = 1000 };
	private _name = switch (_type) do { case "Blood": {"Whole blood"}; case "Plasma": {"Plasma"}; case "Saline": {"Normal saline"}; default {[_type, "Fluid"] select (_type isEqualTo "")} };
	["fluid", format ["%1 %2 mL IV", _name, _vol], ["name", _name, "volume", str _vol, "route", "IV"]]
};

private _bits = _cls splitString "_";
if (count _bits == 3 && {parseNumber (_bits select 1) > 0} && {(_bits select 2) in ["IV", "IM", "IO"]}) exitWith {
	private _key = format ["STR_ACM_Circulation_%1_%2", "Medication", _bits select 0];
	private _name = if (isLocalized _key) then {localize _key} else {_bits select 0};
	private _dose = _bits select 1;
	private _route = _bits select 2;
	["medication", format ["%1 %2 mL %3", _name, _dose, _route], ["name", _name, "dose", _dose, "unit", "mL", "route", _route]]
};

private _meds = [
	["morphine", "Morphine", "10", "mg", "IM"], ["epinephrine", "Epinephrine", "1", "mg", "IM"], ["adenosine", "Adenosine", "6", "mg", "IM"],
	["painkillers", "Painkillers", "1", "tab", "PO"], ["paracetamol", "Paracetamol", "1", "g", "PO"], ["penthrox", "Methoxyflurane", "3", "mL", "Other"],
	["naloxone", "Naloxone", "4", "mg", "IN"], ["fentanyllozenge", "Fentanyl", "800", "mcg", "Other"], ["atna", "ATNAA", "1", "dose", "IM"],
	["midazolam", "Midazolam", "10", "mg", "IM"], ["acme_esketamine", "Esketamine", "28", "mg", "IN"], ["acme_givecalcium", "Calcium gluconate", "1", "g", "IV"],
	["acme_givemagnesium", "Magnesium sulfate", "2", "g", "IV"], ["acme_pushdoseepi", "Epinephrine", "10", "mcg", "IV"],
	["acme_osmobolus_hts", "Hypertonic saline 23.4%", "30", "mL", "IV"], ["acme_osmobolus_mannitol", "Mannitol", "1", "g/kg", "IV"],
	["ammoniainhalant", "Ammonia inhalant", "1", "dose", "Other"]
];
private _m = _meds findIf { (_low find (_x select 0)) == 0 };
if (_m >= 0 || {(getText (_cfg >> "category")) isEqualTo "medication"}) exitWith {
	private _e = if (_m >= 0) then { _meds select _m } else {
		private _w = _dn splitString " ";
		private _n = if (count _w > 1 && {(toLowerANSI (_w select 0)) in ["inject", "administer", "use", "give", "push", "apply"]}) then { (_w select [1]) joinString " " } else {_dn};
		["", _n, "1", "dose", "Other"]
	};
	_e params ["", "_name", "_dose", "_unit", "_route"];
	["medication", format ["%1 %2 %3 %4", _name, _dose, _unit, _route], ["name", _name, "dose", _dose, "unit", _unit, "route", _route]]
};

private _tx = [
	["applytourniquet", "Tourniquet"], ["acme_applyaajt", "Junctional tourniquet"], ["acme_applyxstat", "Hemostatic dressing"],
	["acme_packjunctional", "Hemostatic dressing"], ["acme_wrapjunctional", "Pressure dressing"], ["quikclot", "Hemostatic dressing"],
	["packingbandage", "Hemostatic dressing"], ["elasticbandage", "Pressure dressing"], ["pressurebandage", "Pressure dressing"],
	["emergencytraumadressing", "Pressure dressing"], ["elasticwrap", "Pressure dressing"], ["fielddressing", "Field dressing"],
	["basicbandage", "Field dressing"], ["applychestseal", "Chest seal"], ["acme_applychestseal", "Chest seal"], ["performncd", "Needle decompression"],
	["acme_performnarspear", "Needle decompression"], ["performthoracostomy", "Finger thoracostomy"], ["acme_performthoracostomy", "Finger thoracostomy"],
	["insertchesttube", "Chest tube"], ["acme_insertchesttube", "Chest tube"], ["insertnpa", "Airway adjunct"], ["insertopa", "Airway adjunct"],
	["insertigel", "Airway adjunct"], ["establishsurgicalairway", "Surgical airway"], ["acme_intubatestart", "Intubation"], ["splint", "Splint"],
	["applysamsplint", "Splint"], ["fracturerealignment", "Fracture reduction"], ["insertiv", "IV access"], ["acme_place18g", "IV access"],
	["acme_establishej", "IV access"], ["insertio", "IO access"], ["acme_wraphpmk", "Hypothermia prevention"], ["acme_applynrb", "Oxygen"],
	["acme_directpressure", "Direct pressure"], ["stitch", "Wound closure"], ["surgicalkit", "Wound closure"], ["usesuctionbag", "Airway suction"],
	["useaccuvac", "Airway suction"], ["personalaidkit", "Personal aid kit"], ["washeyes", "Eye irrigation"], ["acme_closeincision", "Wound closure"],
	["closeincision", "Wound closure"], ["acme_suturechesttube", "Chest tube secured"], ["surgicalairway_securestrap", "Surgical airway secured"]
];
private _t = _tx findIf { (_low find (_x select 0)) == 0 };
private _name = if (_t >= 0) then { (_tx select _t) select 1 } else {
	private _w = _dn splitString " ";
	if (count _w > 1 && {(toLowerANSI (_w select 0)) in ["apply", "insert", "use", "perform", "establish", "place", "begin", "start"]}) then { (_w select [1]) joinString " " } else {_dn}
};
private _detail = if (_t >= 0 && {_name in ["Airway adjunct", "IV access", "IO access", "Splint", "Chest tube"]}) then {_dn} else {""};
private _label = if (_site isEqualTo "") then {_name} else {format ["%1 · %2", _name, _site]};
["treatment", _label, ["name", _name, "site", [_site, "Other"] select (_site isEqualTo ""), "note", _detail]]
