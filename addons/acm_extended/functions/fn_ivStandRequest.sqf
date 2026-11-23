/* B395: the player hangs a casualty's bag on an IV stand (_attach true) or takes it down (false). A provider who is
 * holding that casualty's bag up hands it over: their hold ends quietly and the arm lowers. Otherwise the provider
 * reaches up to the hook (the hold's own raise and lower, arm only). The server decides (fn_ivStandServer.sqf). */
params [["_stand", objNull, [objNull]], ["_patient", objNull, [objNull]], ["_attach", true, [true]], ["_part", "", [""]]];
private _player = call ACME_fnc_controlledProvider;
if (isNull _stand || {isNull _patient} || {isNull _player}) exitWith {};
private _holding = (_player getVariable ["ACME_hang_Active", false]) && {(_player getVariable ["ACME_hang_Patient", objNull]) isEqualTo _patient}
    && {_part == "" || {(toLowerANSI (_player getVariable ["ACME_hang_Part", ""])) in ["", toLowerANSI _part]}};
if (_attach && {_holding}) then {
    [true, _player] call ACME_fnc_hangBagStop;
} else {
    if ((missionNamespace getVariable ["ACME_interventionAnimations", true]) && {isNull objectParent _player}
        && {stance _player != "PRONE"} && {!(_player getVariable ["ACME_hang_Active", false])}) then {
        [_player, "ACME_HangBagArmUp"] call ACME_fnc_hangBagGesture;
        [{
            params ["_player"];
            if (((toLowerANSI gestureState _player) find "acme_hangbagarm") == 0 && {!(_player getVariable ["ACME_hang_Active", false])}) then {
                [_player, "ACME_HangBagArmDown"] call ACME_fnc_hangBagGesture;
            };
        }, [_player], 1.0] call CBA_fnc_waitAndExecute;
    };
};
["ACME_ivStandRequest", [_stand, _patient, _attach, _player, _part]] call CBA_fnc_serverEvent;
