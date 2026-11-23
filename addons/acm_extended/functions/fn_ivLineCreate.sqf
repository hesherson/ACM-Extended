/*
    Creates the physical IV-line rope between two rope-capable endpoint objects.

    The line is the ENGINE DEFAULT rope (plain ropeCreate), exactly as ACE fastroping deploys its ropes
    (ace_fastroping_fnc_deployRopes: ropeCreate [_dummy,[0,0,0],_hook,[0,0,0],0.5]). That rope is binarized
    into the engine, ALWAYS renders, and collides with terrain. no custom segment .p3d, nothing to
    binarize, no "p3d not found", no distorted geometry. Both endpoints must be rope-capable physics objects
    (ace_fastroping_helper), which is why the caller ropes helper-to-helper rather than to the soldier/bag.

    Set ACME_hang_ropeClass to a real binarized rope class (e.g. "ace_refuel_fuelHose") to use a thicker
    visible hose instead; "" (default) uses the thin engine default rope.

    Arguments:
    0: Start object  <OBJECT>   (rope-capable)
    1: Start attachment point: model-space offset or selection/memory-point name <ARRAY or STRING>
    2: End object    <OBJECT>   (rope-capable)
    3: End attachment point: model-space offset or selection/memory-point name <ARRAY or STRING>
    4: Rope length in meters; use -1 to calculate distance plus 0.12 m of slack <NUMBER>
    5: Segment count (engine default rope ignores this; kept for back-compat) <NUMBER>
    6: Optional rope class; empty string uses the engine-default fallback <STRING>

    Returns:
    Rope object, or objNull on failure.
*/
params [
    ["_fromObject", objNull, [objNull]],
    ["_fromPoint", [0, 0, 0], [[], ""]],
    ["_toObject", objNull, [objNull]],
    ["_toPoint", [0, 0, 0], [[], ""]],
    ["_length", -1, [0]],
    ["_segments", 32, [0]],
    ["_ropeClass", "", [""]]
];

if (isNull _fromObject || {isNull _toObject}) exitWith {
    objNull
};

private _resolveWorldPoint = {
    params ["_object", "_point"];
    if (_point isEqualType "") exitWith {
        _object modelToWorldVisual (_object selectionPosition _point)
    };
    _object modelToWorldVisual _point
};

if (_length < 0) then {
    private _fromWorld = [_fromObject, _fromPoint] call _resolveWorldPoint;
    private _toWorld = [_toObject, _toPoint] call _resolveWorldPoint;
    _length = 0.05 max ((_fromWorld distance _toWorld) + 0.12);
};

_fromObject enableRopeAttach true;
_toObject enableRopeAttach true;

private _rope = objNull;

if (_ropeClass isEqualTo "") then {
    // the engine default rope: the proven, model-free, terrain-colliding rope, in the ACE fastroping form.
    _rope = ropeCreate [_fromObject, _fromPoint, _toObject, _toPoint, _length];
} else {
    // a custom binarized rope class, in the 8-element form ending in the classname. the two slots before the classname
    // must be [], because a nil there collapses the array and ropecreate rejects it.
    _rope = ropeCreate [
        _fromObject,
        _fromPoint,
        _toObject,
        _toPoint,
        _length,
        [],
        [],
        _ropeClass,
        // B395: the segment count (9th argument, engine maximum 63); without it the engine made about 20 for a
        // 3 m line, which showed as straight pieces
        ((round _segments) max 2) min 63
    ];
};

_rope
