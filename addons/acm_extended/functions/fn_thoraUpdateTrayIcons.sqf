// Refresh the role-filtered thoracostomy tray rows. Tube exists only for Doctor; seal remains a full-width row;
// this function never resizes/rebuilds controls, so repeated refreshes cannot squash either icon.
disableSerialization;
private _display = uiNamespace getVariable ["ACME_Thora_DLG", displayNull];
if (isNull _display) exitWith {};
private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
private _medic = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
private _held = uiNamespace getVariable ["ACME_Thora_Held", ""];
private _closed = !isNull _patient && {_patient getVariable [format ["ACME_thora_closed_%1", _side], false]};
private _sealed = !isNull _patient && {_patient getVariable [format ["ACME_thora_sealed_%1", _side], false]};
private _isDoctor = !isNull _medic && {[_medic, 2] call ace_medical_treatment_fnc_isMedic};
private _canTube = _isDoctor && {[_medic, "chestTube"] call ACME_fnc_procedureAllowed};
private _canSeal = !isNull _medic && {[_medic, "thoracostomySeal"] call ACME_fnc_procedureAllowed};
uiNamespace setVariable ["ACME_Thora_CanTube", _canTube];
uiNamespace setVariable ["ACME_Thora_SeparateClosureSlots", true];

{
    private _bg = _x;
    private _tool = _bg getVariable ["thoraTool", ""];
    private _ic = _bg getVariable ["thoraIcon", controlNull];
    private _btn = _bg getVariable ["thoraBtn", controlNull];
    private _countCtrl = _bg getVariable ["thoraCount", controlNull];
    private _count = -1;
    private _allowed = true;

    // A tube row from an older/reused display must disappear completely for non-doctors, including its hitbox.
    if (_tool == "tube" && {!_canTube}) then {
        _bg ctrlShow false;
        if (!isNull _ic) then {_ic ctrlShow false;};
        if (!isNull _btn) then {_btn ctrlEnable false; _btn ctrlShow false;};
        if (!isNull _countCtrl) then {_countCtrl ctrlShow false;};
        continue;
    } else {
        _bg ctrlShow true;
        if (!isNull _ic) then {_ic ctrlShow true;};
        if (!isNull _btn) then {_btn ctrlShow true;};
        if (!isNull _countCtrl) then {_countCtrl ctrlShow true;};
    };

    private _tex = switch (_tool) do {
        case "chlorhexidine": {format ["\acm_extended\ui\items\chlorhexidine_%1_ca.paa", _side]};
        case "scalpel": {"\x\acm\addons\airway\ui\surgical_airway\inv_scalpel.paa"};
        case "kelly": {"\acm_extended\ui\items\kelly_clamps_icon_ca.paa"};
        case "finger": {format ["\acm_extended\ui\items\thoracostomy_finger_%1_ca.paa", _side]};
        case "tube": {format ["\acm_extended\ui\items\chest_tube_%1_placed_ca.paa", ["left", "right"] select (_side == "left")]};
        case "seal": {"\x\acm\addons\breathing\ui\chestseal_ca.paa"};
        default {""};
    };
    if (!isNull _ic && {_tex != ""}) then {_ic ctrlSetText _tex;};

    if (_tool == "tube") then {
        _allowed = _canTube && {!_closed} && {!_sealed};
        _count = if (_allowed) then {[_medic, "ACM_ChestTubeKit"] call ace_common_fnc_getCountOfItem} else {0};
    };
    if (_tool == "seal") then {
        _allowed = _canSeal && {!_closed} && {!_sealed};
        _count = if (_allowed) then {[_medic, "ACM_ChestSeal"] call ace_common_fnc_getCountOfItem} else {0};
    };
    private _locked = (_tool in ["tube", "seal"]) && {!_allowed || {_count <= 0}};
    private _selected = _held == _tool;
    _bg setVariable ["thoraLocked", _locked];
    _bg ctrlSetBackgroundColor ([[0,0,0,0.85], [0.20,0.28,0.18,0.9]] select _selected);
    if (!isNull _ic) then {
        _ic ctrlSetTextColor (if (_selected) then {[0,0,0,1]} else {if (_locked) then {[0.4,0.4,0.4,0.5]} else {[1,1,1,0.85]}});
    };
    if (!isNull _countCtrl && {_count >= 0}) then {
        _countCtrl ctrlSetStructuredText parseText format ["<t align='right' size='0.72' color='%1'>x%2</t>", if (_count > 0) then {"#ffffff"} else {"#ff6666"}, _count];
    };
    if (!isNull _btn) then {
        // A selected closure remains clickable even if the last item was just consumed, so it can be put down cleanly.
        _btn ctrlEnable (!_locked || {_selected});
        if (_tool == "tube") then {_btn ctrlSetTooltip (if (_allowed) then {"Place a chest tube"} else {"Chest tube permission required"});};
        if (_tool == "seal") then {_btn ctrlSetTooltip (if (_allowed) then {"Place a chest seal"} else {"Chest seal permission required"});};
    };
} forEach (uiNamespace getVariable ["ACME_Thora_SlotBGs", []]);
