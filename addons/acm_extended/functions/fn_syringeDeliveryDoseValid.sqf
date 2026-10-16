/* Prove every submitted medication milligram is funded by this exact syringe
 * delta. Duplicate source entries aggregate; missing/extra drugs cannot pass.
 */
if (isNil "_this") exitWith {false};
if !(_this isEqualType [] && {count _this == 3}) exitWith {false};
private _row = _this select 0;
private _delta = _this select 1;
private _doses = _this select 2;
if (isNil "_row" || {isNil "_delta"} || {isNil "_doses"}) exitWith {false};
if (([_row,_delta] call ACME_fnc_syringeDeliveryDelta) isEqualTo []) exitWith {false};
if !(_doses isEqualType [] && {count _doses > 0}) exitWith {false};
private _kind = if (count _row > 6) then {_row select 6} else {""};
if (isNil "_kind" || {!(_kind isEqualType "")}) exitWith {false};
private _epiMix = _kind == "epiMixB12";
private _sourceParts = if (count (_row select 5) > 0) then {
    (_delta select 2) apply {[_x select 1,_x select 2]}
} else {[_row select 0,_delta select 0]};
// The ordinary source has one pair, matching the mixture array contract.
if (count (_row select 5) == 0) then {_sourceParts = [_sourceParts];};
private _expected = [];
private _valid = true;
{
    private _source = _x select 0;
    private _ml = _x select 1;
    if (isNil "_source" || {!(_source isEqualType "")} || {_source == ""}) then {
        _valid = false;
        continue;
    };
    if (_ml == 0) then {continue;};
    private _conc = getNumber (configFile >> "ACM_Medication" >> "Concentration" >> _source >> "concentration");
    private _mg = _conc * _ml;
    if (!finite _conc || {_conc <= 0} || {!finite _mg} || {_mg <= 0}) then {
        _valid = false;
        continue;
    };
    private _at = _expected findIf {(_x select 0) == _source};
    if (_at < 0) then {_expected pushBack [_source,_mg];} else {
        private _part = +(_expected select _at);
        _part set [1,(_part select 1) + _mg];
        _expected set [_at,_part];
    };
} forEach _sourceParts;
if (!_valid || {count _expected == 0}) exitWith {false};

private _actual = [];
{
    if (isNil "_x") then {_valid = false; continue;};
    if !(_x isEqualType [] && {count _x >= 4}) then {_valid = false; continue;};
    private _class = _x select 0;
    private _mg = _x select 1;
    private _iv = _x select 2;
    private _label = _x select 3;
    if (isNil "_class" || {isNil "_mg"} || {isNil "_iv"} || {isNil "_label"}) then {_valid = false; continue;};
    if !(_class isEqualType "" && {_class != ""}
        && {_mg isEqualType 0} && {finite _mg} && {_mg > 0}
        && {_iv isEqualType true} && {_label isEqualType ""}) then {_valid = false; continue;};
    private _seconds = if (count _x > 4) then {_x select 4} else {5};
    private _prepared = if (count _x > 5) then {_x select 5} else {false};
    private _rateMeta = if (count _x > 6) then {_x select 6} else {[]};
    if (isNil "_seconds" || {isNil "_prepared"} || {isNil "_rateMeta"}) then {_valid = false; continue;};
    if !(_seconds isEqualType 0 && {finite _seconds} && {_seconds > 0}
        && {_prepared isEqualType true} && {_rateMeta isEqualType []}
        && {[_class,_iv,true,_prepared] call ACME_fnc_medicationRouteAllowed}) then {_valid = false; continue;};
    private _source = (_class splitString "_") param [0,""];
    // The measured pressor recipe uses the diluted cardiac source but native
    // Epinephrine_IV delivery. Its concentration remains the source's 0.1 mg/mL.
    if (_epiMix && {_class == "Epinephrine_IV"} && {_label == "B13_MEASURED_EPI"} && {_iv}) then {
        _source = "EpinephrineCardiac";
    };
    if ((_expected findIf {(_x select 0) == _source}) < 0) then {_valid = false; continue;};
    private _at = _actual findIf {(_x select 0) == _source};
    if (_at < 0) then {_actual pushBack [_source,_mg];} else {
        private _part = +(_actual select _at);
        _part set [1,(_part select 1) + _mg];
        _actual set [_at,_part];
    };
} forEach _doses;
if (!_valid || {count _actual != count _expected}) exitWith {false};
{
    private _source = _x select 0;
    private _wanted = _x select 1;
    private _at = _actual findIf {(_x select 0) == _source};
    if (_at < 0) then {_valid = false; continue;};
    private _submitted = (_actual select _at) select 1;
    if (!finite _wanted || {!finite _submitted}
        || {abs (_submitted - _wanted) > _wanted * 0.00001}) then {_valid = false;};
} forEach _expected;
_valid
