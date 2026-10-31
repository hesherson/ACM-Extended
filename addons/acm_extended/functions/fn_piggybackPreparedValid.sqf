/* Shared provider/owner carrier check. Propofol stays in its own authenticated emulsion bottle. */
params ["_set","_prepared","_type",["_carrierVolume",0]];
private _kind = _set param [8,"yset"];
if (_kind in ["yset","bagOnly"]) exitWith {false};
if (_prepared isEqualTo []) exitWith {_type != "ACME_Propofol" && {_kind != "propofol"}};
private _sid = _set param [0,""];
private _components = [_prepared] call ACME_fnc_preparedComponents;
private _volume = _prepared param [10,0];
if (_sid == "" || {(_prepared param [0,""]) != _sid} || {(_prepared param [15,""]) != _sid}
    || {(_prepared param [2,""]) != (_set param [2,""])}
    || {!(_volume isEqualType 0)} || {!finite _volume} || {_volume <= 1}
    || {_components isEqualTo []}) exitWith {false};
if (_type == "ACME_Propofol") exitWith {
    _kind == "propofol" && {_carrierVolume == 50} && {_volume == 50}
        && {(_set param [1,""]) == "ACM_Vial_Propofol"}
        && {(_prepared param [1,""]) == "ACM_Vial_Propofol"}
        && {(_set param [2,""]) == "ACME_PropofolIV_50"}
        && {(_set param [9,0]) == 50}
        && {(_prepared param [17,""]) == "propofol-bottle"}
        && {_components isEqualTo [["Propofol",500,1]]}
};
_type == "Saline" && {_kind != "propofol"}
    && {(_prepared param [17,""]) != "propofol-bottle"}
    && {(_prepared param [1,""]) != "ACM_Vial_Propofol"}
    && {(_set param [1,""]) != "ACM_Vial_Propofol"}
    && {(_components findIf {(_x param [0,""]) == "Propofol"}) < 0}
