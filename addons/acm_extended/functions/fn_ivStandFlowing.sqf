/* B395: true if the casualty has an IV bag that is still running (the same test fn_hangBagTick.sqf uses to lower a
 * held bag that ran dry): a bag that is not an empty marker or the clamped saline reserve, with fluid left, and
 * not disconnected. Optional _part restricts it to one limb. */
params [["_patient", objNull, [objNull]], ["_part", "", [""]]];
if (isNull _patient) exitWith {false};
private _ivBags = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
if !(_ivBags isEqualType createHashMap) exitWith {false};
private _gone = _patient getVariable ["ACME_IV_DisconnectedBagUIDs", []];
_part = toLower _part;
private _found = false;
{
    if (_part == "" || {toLower _x == _part}) then {
        if ((_y findIf {
            _x isEqualType [] && {!((_x param [0, ""]) in ["ACME_Empty", "ACME_EmptySaline", "ACME_SalineY"])}
                && {(_x param [1, 0]) > 0.5} && {!((_x param [8, ""]) in _gone)}
        }) >= 0) then {_found = true;};
    };
} forEach _ivBags;
_found
