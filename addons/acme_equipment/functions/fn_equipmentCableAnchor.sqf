/* ASL endpoints. Port coordinates are model-relative fractions, not hardcoded world altitude. */
params ["_object","_kind",["_patient",false]];
if (isNull _object) exitWith {[]};
if (_patient) exitWith {
    private _selection=switch (_kind) do {
        case "spo2": {"righthand"};case "nibp": {"rightarm"};case "capno": {"head"};case "temp": {"spine2"};default {"spine3"};
    };
    private _point=_object selectionPosition _selection;
    if (_point isEqualTo [0,0,0]) then {_point=_object selectionPosition "pelvis";};
    (_object modelToWorldVisualWorld _point) vectorAdd [0,0,0.04]
};
private _box=boundingBoxReal _object;private _min=_box select 0;private _max=_box select 1;
private _fraction=switch (_kind) do {
    case "usb": {[0.85,0.85,0.25]};case "ecg": {[0.05,0.45,0.6]};case "spo2": {[0.05,0.55,0.5]};
    case "nibp": {[0.05,0.65,0.4]};case "capno": {[0.05,0.35,0.45]};case "temp": {[0.05,0.25,0.35]};default {[0.15,0.7,0.3]};
};
private _point=[];
for "_i" from 0 to 2 do {_point pushBack ((_min select _i)+((_max select _i)-(_min select _i))*(_fraction select _i));};
_object modelToWorldVisualWorld _point
