/* Model-space anchors use screen-facing memory points to locate the opposite side of the case. */
params ["_object","_kind",["_patient",false]];
if (_patient) exitWith {
    private _selection = switch (_kind) do {
        case "spo2": {"righthand"};
        case "nibp": {"rightarm"};
        case "capno": {"head"};
        case "temp": {"spine2"};
        default {"spine3"};
    };
    private _point = _object selectionPosition [_selection,"Memory"];
    if (_point isEqualTo [0,0,0]) then {_point = _object selectionPosition _selection;};
    if (_point isEqualTo [0,0,0]) then {_point = _object selectionPosition "pelvis";};
    _point
};
private _box = boundingBoxReal _object;
_box params ["_min","_max"];
private _bl = _object selectionPosition ["scr_bl","Memory"];
private _right = (_object selectionPosition ["scr_br","Memory"]) vectorDiff _bl;
private _up = (_object selectionPosition ["scr_tl","Memory"]) vectorDiff _bl;
private _frontY = (_right vectorCrossProduct _up) select 1;
private _minSide = _frontY >= 0;
private _port = switch (_kind) do {
    case "ecg": {0.25};
    case "spo2": {0.39};
    case "nibp": {0.50};
    case "capno": {0.61};
    case "temp": {0.72};
    case "usb": {0.84};
    default {0.33};
};
[
    linearConversion [0,1,_port,_min select 0,_max select 0],
    ((_box select ([1,0] select _minSide)) select 1),
    linearConversion [0,1,0.38,_min select 2,_max select 2]
]
