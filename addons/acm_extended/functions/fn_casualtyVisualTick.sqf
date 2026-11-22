/*
 * On every machine with a screen, twice a second: what is seen on and under the casualties near the camera that
 * is no part of what they wear. Made here, for this screen only, from what every machine knows of a casualty
 * (his public state): nothing is sent, and who joins late sees it as everybody does.
 *   on his face  an airway adjunct that is in place ("NPA, OPA and ET tube. all should physically show them on
 *                the face when applying any of those and having them successfully established", 2026-11-20):
 *                the NPA's trumpet at his right nostril, the OPA's flange on his lips, the i-gel's stem out of
 *                his mouth (the user's reference pictures, 2026-11-20), the ET tube out of the left corner of his mouth (tools/build_airway_adjuncts.py). Fixed to his head, turning with it.
 *   under him    the HPMK laid out under one who is prepped for it ("prep HPMK should put the blanket under the
 *                patient and show it actually underneath the patient", 2026-11-20): on the ground under him,
 *                along him, or on the litter he lies on if there is a model of it for that litter (config value
 *                acmeHpmkUnder). The half he lies on is pressed flat (tools/build_hpmk_staged.py).
 * His mouth is held open while an OPA, an i-gel or an ET tube is in it.
 * Looked at: men within 40 m of the camera, alive or dead. Nothing is shown of one who sits in a vehicle.
 * Settings for tests: ACME_faceVisual_<npa|opa|igel|ett> = [point of his head, offset, direction, up].
 * Arguments: none.
 */
if !(missionNamespace getVariable ["ACME_sys_casualtyVisuals", true]) exitWith {
    {{deleteVehicle _x} forEach (values (_y select 1))} forEach ACME_casualtyVisuals;
    ACME_casualtyVisuals = createHashMap;
};
private _camera = positionCameraToWorld [0, 0, 0];
private _seen = [];
{
    private _unit = _x;
    private _want = createHashMap;           // slot -> model
    if (isNull objectParent _unit) then {
        if ((_unit getVariable ["ACM_airway_AirwayItem_Nasal", ""]) == "NPA") then {_want set ["npa", "\acm_extended\models\acme_face_npa.p3d"];};
        if ((_unit getVariable ["ACM_airway_AirwayItem_Oral", ""]) == "OPA") then {_want set ["opa", "\acm_extended\models\acme_face_opa.p3d"];};
        if ((_unit getVariable ["ACM_airway_AirwayItem_Oral", ""]) == "SGA") then {_want set ["igel", "\acm_extended\models\acme_face_igel.p3d"];};
        if (_unit getVariable ["ACME_ETT_Inserted", false]) then {_want set ["ett", "\acm_extended\models\acme_face_ett.p3d"];};
        if ((_unit getVariable ["ACME_hpmk_state", ""]) == "prepped") then {
            private _litter = _unit getVariable ["acme_sked_litter", objNull];
            private _model = if (isNull _litter) then {
                ["", "\acme_hpmk\hpmk_under_ground.p3d"] select (isNull attachedTo _unit)
            } else {getText (configOf _litter >> "acmeHpmkUnder")};
            if (_model != "") then {_want set ["prep", _model];};
        };
    };
    // His mouth open round what is in it ("i would like the mouth posed open so that all of the different airways look
    // like they are actually in the mouth", 2026-11-20): the face the game gives the dead has the jaw dropped, and it
    // holds on the living (tried in game: of the game's faces it is the only one with the mouth open). Set on this
    // machine, again each time (the game may set a face of its own), and given back when the mouth is free.
    if ((["opa", "igel", "ett"] findIf {_x in _want}) >= 0) then {
        _unit setMimic "dead";
        _unit setVariable ["ACME_mouthOpen", true];
    } else {
        if (_unit getVariable ["ACME_mouthOpen", false]) then {
            _unit setMimic "";
            _unit setVariable ["ACME_mouthOpen", nil];
        };
    };
    private _key = hashValue _unit;
    private _entry = ACME_casualtyVisuals getOrDefault [_key, []];
    if (count _want == 0 && {_entry isEqualTo []}) then {continue;};
    if (_entry isEqualTo []) then {
        _entry = [_unit, createHashMap];
        ACME_casualtyVisuals set [_key, _entry];
    };
    _seen pushBack _key;
    private _have = _entry select 1;         // slot -> object
    {
        if ((_want getOrDefault [_x, ""]) != (_y getVariable ["ACME_visualModel", ""])) then {
            deleteVehicle _y;
            _have deleteAt _x;
        };
    } forEach +_have;
    {
        private _slot = _x;
        private _object = _have getOrDefault [_slot, objNull];
        if (isNull _object) then {
            // (the command takes a path without the leading backslash that a config value has)
            _object = createSimpleObject [[_y, _y select [1]] select ((_y select [0, 1]) == "\"), getPosWorld _unit, true];
            _object setVariable ["ACME_visualModel", _y];
            _have set [_slot, _object];
            if (_slot != "prep") then {
                // (from his eye point, in the axes of his head: to his right, out of his face, to the top of his head.
                // Places tried in game, 2026-11-20: nearer his face the NPA and the OPA lay half inside it.
                // The middle of his face is 10 mm to the right of his eye point: what goes in his mouth is put
                // there, and the NPA 9 mm further, in his right nostril ("the NPA needs to be in one or the other
                // nostril, not in the middle of the nostril. the igel needs to be in the middle of the lips").)
                (missionNamespace getVariable ["ACME_faceVisual_" + _slot, switch (_slot) do {
                    // (2026-11-21, measured on four of the game's faces with the mouth open: the gap between the
                    // lips is 88 mm below the eye point, 10 mm to its right, its front 36 to 45 mm out. What goes
                    // in the mouth is put in that gap: "they must be IN the mouth". The NPA 7 mm right of the
                    // middle: the narrow noses have the nostril no further out.)
                    case "npa": {["pilot", [0.017, 0.0507, -0.0627], [0, 1, 0], [0, 0, 1]]};
                    case "opa": {["pilot", [0.010, 0.049, -0.088], [0, 1, 0], [0, 0, 1]]};      // (at 0.045 the fullest upper lip stood through the flange)
                    case "igel": {["pilot", [0.010, 0.040, -0.088], [0, 1, 0], [0, 0, 1]]};
                    default {["pilot", [0.010, 0.040, -0.088], [0, 1, 0], [0, 0, 1]]};
                }]) params ["_point", "_offset", "_dir", "_up"];
                _object attachTo [_unit, _offset, _point, true];
                _object setVectorDirAndUp [_dir, _up];
            };
        };
        if (_slot == "prep") then {
            private _litter = _unit getVariable ["acme_sked_litter", objNull];
            if (!isNull _litter) then {
                if ((attachedTo _object) isNotEqualTo _litter) then {_object attachTo [_litter, [0, 0, 0]];};
            } else {
                if (!isNull attachedTo _object) then {detach _object;};
                // on the ground under him: its middle under his pelvis, along him toward his head, lying as the
                // ground (or the floor) lies there. Laid anew only when he has been moved or turned.
                // (his pelvis and his neck: the middles of their hit boxes. He has no bone point named pelvis:
                // asked for one, the game gives the place he stands on, and the sheet lay askew beside him.)
                private _pelvis = _unit modelToWorldVisualWorld (_unit selectionPosition ["pelvis", "FireGeometry", "AveragePoint"]);
                private _head = _unit modelToWorldVisualWorld (_unit selectionPosition ["neck", "FireGeometry", "AveragePoint"]);
                private _along = _head vectorDiff _pelvis;
                _along set [2, 0];
                if (vectorMagnitude _along < 0.15) then {_along = vectorDir _unit;};
                _along = vectorNormalized _along;
                private _was = _object getVariable ["ACME_visualAt", []];
                if (_was isEqualTo [] || {((_was select 0) distance2D _pelvis) > 0.2} || {((_was select 1) vectorDotProduct _along) < 0.97}) then {
                    _object setVariable ["ACME_visualAt", [_pelvis, _along]];
                    private _under = lineIntersectsSurfaces [_pelvis vectorAdd [0, 0, 0.4], _pelvis vectorAdd [0, 0, -1.5], _unit, objNull, true, 1, "GEOM", "NONE"];
                    private _place = +_pelvis;
                    private _normal = [0, 0, 1];
                    if (_under isEqualTo []) then {
                        _place set [2, getTerrainHeightASL _pelvis];
                        _normal = surfaceNormal _pelvis;
                    } else {
                        _place = (_under select 0) select 0;
                        _normal = (_under select 0) select 1;
                    };
                    _object setPosASL _place;
                    _object setVectorDirAndUp [_along vectorDiff (_normal vectorMultiply (_along vectorDotProduct _normal)), _normal];
                };
            };
        };
    } forEach _want;
    if (count _have == 0) then {
        ACME_casualtyVisuals deleteAt _key;
        _seen deleteAt (count _seen - 1);
    };
} forEach (_camera nearObjects ["CAManBase", 40]);
// what belongs to one who is gone, or out of sight
{
    if !(_x in _seen) then {
        if ((_y select 0) getVariable ["ACME_mouthOpen", false]) then {
            (_y select 0) setMimic "";
            (_y select 0) setVariable ["ACME_mouthOpen", nil];
        };
        {deleteVehicle _x} forEach (values (_y select 1));
        ACME_casualtyVisuals deleteAt _x;
    };
} forEach +ACME_casualtyVisuals;
