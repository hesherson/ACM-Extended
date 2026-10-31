/* Request one owner snapshot before opening. A delayed reply cannot steal
 * focus after another patient or form has superseded this request. */
private _acmeReconcile = "B291:DD1380OwnerSnapshot";
params ["_medic", "_patient"];
if (!hasInterface || {isNull _medic} || {isNull _patient}
    || {!local _medic} || {!(_medic isEqualTo ACE_player)} || {!alive _medic}) exitWith {false};
private _sameVehicle = !isNull objectParent _medic && {objectParent _medic isEqualTo objectParent _patient};
if (!_sameVehicle && {_medic distance _patient > 6}) exitWith {false};
private _sourceDisplay = findDisplay 38580;
if (dialog && {isNull _sourceDisplay}) exitWith {false};
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
private _generation = (uiNamespace getVariable ["DD1380_generation", 0]) + 1;
uiNamespace setVariable ["DD1380_generation", _generation];
private _id = format ["DD1380:%1:%2:%3", clientOwner, _generation, serverTime];
private _request = [_medic, _patient, _epoch, _id];
uiNamespace setVariable ["DD1380_openRequest", _request + [_sourceDisplay]];
["LNX_DD1380_DocumentRequest", _request, _patient] call CBA_fnc_targetEvent;
[{
    params ["_medic", "_patient", "_epoch", "_id"];
    if (((uiNamespace getVariable ["DD1380_openRequest", []]) param [3, ""]) isEqualTo _id) then {
        uiNamespace setVariable ["DD1380_openRequest", nil];
        if (_medic isEqualTo ACE_player) then {["The card could not be loaded. Try opening it again."] call ace_common_fnc_displayTextStructured;};
    };
}, _request, 10] call CBA_fnc_waitAndExecute;
true
