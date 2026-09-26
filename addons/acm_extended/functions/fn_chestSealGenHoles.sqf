params ["_patient"];
if (!isServer || {isNull _patient}) exitWith {};

(missionNamespace getVariable ["ACME_CS_holeField", [0.5, 0.285, 0.07, 0.05]]) params ["_cx", "_cy", "_rx", "_ry"];
if !(_cx isEqualType 0 && {_cy isEqualType 0} && {_rx isEqualType 0} && {_ry isEqualType 0} && {finite _cx} && {finite _cy} && {finite _rx} && {finite _ry} && {_rx > 0} && {_ry > 0}) then {
    _cx = 0.5;
    _cy = 0.285;
    _rx = 0.07;
    _ry = 0.05;
};

// the plate-carrier wound bias: weight the wounds to the bottom of the field, under the plate, and to the two upper
// corners, top-left and top-right, beside the plate. push them toward the edge, away from the plated center, and
// multi-hole injuries are later spaced against the actual chest-seal footprint so each remains independently treatable.
// cos and sin are in degrees and screen +y is down, so an angle of about 90 is the bottom, about 225 is top-left
// and about 315 is top-right.
private _zBottom = missionNamespace getVariable ["ACME_CS_zoneBottomWeight", 0.55];
private _zTop    = missionNamespace getVariable ["ACME_CS_zoneTopWeight", 0.45];
private _edgeBias = missionNamespace getVariable ["ACME_CS_edgeBias", 0.60];
if !(_edgeBias isEqualType 0 && {finite _edgeBias} && {_edgeBias >= 0} && {_edgeBias < 1}) then {_edgeBias = 0.60;};
// B69: placed chest-seal art is ~0.05 x 0.05 of body UV. Use axis-aligned center clearance rather than
// Euclidean distance: if either axis differs by at least 0.052, two 0.05-square seals cannot overlap.
private _minSep  = missionNamespace getVariable ["ACME_CS_minHoleSep", 0.052];
if !(_minSep isEqualType 0 && {finite _minSep} && {_minSep >= 0}) then {_minSep = 0.052;};

private _fnc_clearance = {
    params ["_p", "_q"];
    private _dx = abs ((_p select 0) - (_q select 0));
    private _dy = abs ((_p select 1) - (_q select 1));
    _dx max _dy
};

private _fnc_randomPoint = {
    // pick a weighted anatomical zone, then an angle within the arc of that zone and an edge-favored radius.
    private _r = random 1;
    private _arc = if (_r < _zBottom) then {
        [40, 140]  // the bottom, under the plate. it has the widest arc and the most wounds.
    } else {
        if (_r < (_zBottom + (_zTop / 2))) then {
            [200, 250]  // the top-left corner, beside the plate.
        } else {
            [290, 340]  // the top-right corner, beside the plate.
        }
    };
    _arc params ["_a0", "_a1"];
    private _angle  = _a0 + (random (_a1 - _a0));
    private _radius = _edgeBias + (random (1 - _edgeBias));  // 0.60 to 1.0 hugs the rim and clears the center.
    [
        _cx + ((cos _angle) * _rx * _radius),
        _cy + ((sin _angle) * _ry * _radius)
    ]
};

private _fnc_confinePoint = {
    params ["_x", "_y"];
    if !(_x isEqualType 0 && {_y isEqualType 0} && {finite _x} && {finite _y}) exitWith {call _fnc_randomPoint};

    private _nx = (_x - _cx) / _rx;
    private _ny = (_y - _cy) / _ry;
    private _distance = sqrt (((_nx * _nx) + (_ny * _ny)) max 0);
    if (_distance > 0.96) then {
        private _scale = 0.96 / _distance;
        _x = _cx + ((_x - _cx) * _scale);
        _y = _cy + ((_y - _cy) * _scale);
    };
    [_x, _y]
};

private _injuryMap = missionNamespace getVariable ["ACM_breathing_ChestInjury_Chances", createHashMap];
private _eligibleIDs = keys _injuryMap;
private _maxPerSide = missionNamespace getVariable ["ACME_CS_maxHolesPerSide", 4];
if !(_maxPerSide isEqualType 0 && {finite _maxPerSide} && {_maxPerSide >= 1}) then {_maxPerSide = 4;};
_maxPerSide = (floor _maxPerSide) min 4;
// Hard anatomical/UX ceiling. Penetrating trauma may be severe, but the chest-seal workspace never creates more
// than six total external wound sites. Treatment-created holes already present count against the same visual budget.
private _maxTotalHoles = 6;

private _fnc_mkHole = {
    params ["_side", ["_sealed", false]];
    private _icon = format ["\acm_extended\ui\holes\hole%1_ca.paa", 1 + floor random 8];
    // spacing: same-side seals must not stack. try several biased candidates, keep the one furthest from the existing
    // same-side holes, and stop early once a candidate clears _minSep. _frontPts and _backPts are seeded below.
    private _pts = if (_side == "back") then { _backPts } else { _frontPts };
    private _best = call _fnc_randomPoint;
    private _bestSep = 99;
    { private _d = [_best, _x] call _fnc_clearance; if (_d < _bestSep) then {_bestSep = _d}; } forEach _pts;
    if (_minSep > 0 && {count _pts > 0} && {_bestSep < _minSep}) then {
        for "_try" from 1 to 48 do {
            private _cand = call _fnc_randomPoint;
            private _sep = 99;
            { private _d = [_cand, _x] call _fnc_clearance; if (_d < _sep) then {_sep = _d}; } forEach _pts;
            if (_sep > _bestSep) then { _best = _cand; _bestSep = _sep; };
            if (_bestSep >= _minSep) exitWith {};
        };

        // If random weighted sampling still clusters a 3rd/4th wound, search a deterministic lattice over the same
        // three authored thorax arcs. This preserves the plate-carrier zones but gives multi-hole injuries a reliable
        // seal-safe fallback instead of accepting a close overlap merely because 48 random draws were unlucky.
        if (_bestSep < _minSep) then {
            {
                private _arcFallback = _x;
                _arcFallback params ["_a0", "_a1"];
                for "_ai" from 0 to 20 do {
                    private _angle = _a0 + ((_a1 - _a0) * (_ai / 20));
                    {
                        private _radiusFallback = _x;
                        private _cand = [
                            _cx + ((cos _angle) * _rx * _radiusFallback),
                            _cy + ((sin _angle) * _ry * _radiusFallback)
                        ];
                        private _sep = 99;
                        { private _d = [_cand, _x] call _fnc_clearance; if (_d < _sep) then {_sep = _d}; } forEach _pts;
                        if (_sep > _bestSep) then { _best = _cand; _bestSep = _sep; };
                    } forEach [0.60, 0.70, 0.80, 0.90, 0.96];
                };
            } forEach [[40,140], [200,250], [290,340]];
        };
    };
    _pts pushBack _best;
    [_side, _best select 0, _best select 1, _sealed, _sealed, _icon]
};

// Native seals may precede the first minigame session. Their snapshot covers
// only already-present records; newly tracked genuine injury events stay open.
private _nativeCount = _patient getVariable ["ACME_ptx_nativeSealCount", -1];
if !(_nativeCount isEqualType 0 && {finite _nativeCount}) then {_nativeCount = -1;};
_nativeCount = (floor _nativeCount) max -1;
private _nativeHoleCount = _patient getVariable ["ACME_ptx_nativeSealHoleCount", -1];
if !(_nativeHoleCount isEqualType 0 && {finite _nativeHoleCount}) then {_nativeHoleCount = -1;};
_nativeHoleCount = (floor _nativeHoleCount) max -1;

private _tracked = +(_patient getVariable ["ACME_CS_penetratingWounds", []]);
_tracked = _tracked select {
    _x isEqualType [] && {count _x >= 1} && {
        private _id = _x param [0, -1];
        (_id isEqualType 0) && {_id in _eligibleIDs}
    }
};

private _existingCounts = createHashMap;
{
    private _id = _x param [0, -1];
    _existingCounts set [_id, (_existingCounts getOrDefault [_id, 0]) + 1];
} forEach _tracked;

private _open = (_patient getVariable ["ace_medical_openWounds", createHashMap]) getOrDefault ["body", []];
{
    if (_x isEqualType [] && {count _x >= 2}) then {
        private _id = _x param [0, -1];
        private _amount = _x param [1, 0];
        if ((_id isEqualType 0) && {_amount isEqualType 0} && {_amount > 0} && {_id in _eligibleIDs}) then {
            private _wanted = ((ceil _amount) max 1) min _maxPerSide;
            private _have = _existingCounts getOrDefault [_id, 0];
            for "_i" from (_have + 1) to _wanted do {
                _tracked pushBack [_id, -1, -1];
            };
            if (_wanted > _have) then {_existingCounts set [_id, _wanted];};
        };
    };
} forEach _open;

_patient setVariable ["ACME_CS_penetratingWounds", _tracked, true];
_patient setVariable ["ACME_CS_hasPenetratingChestWound", count _tracked > 0, true];

private _stored = _patient getVariable ["ACME_CS_holeData", []];
private _holes = [];
{
    if (_x isEqualType [] && {count _x >= 6}) then {
        private _hole = (_x select [0, 6]) + [controlNull, controlNull];
        if (_forEachIndex < _nativeHoleCount) then {_hole set [3, true]; _hole set [4, true];};
        _holes pushBack _hole;
    };
} forEach _stored;

// a migration: pull previously stored edge holes into the seal-safe inner thorax ellipse. this preserves the found
// and sealed state and the icon choice while guaranteeing the full seal stays on the body.
{
    if (_x isEqualType [] && {count _x >= 3}) then {
        private _point = [_x select 1, _x select 2] call _fnc_confinePoint;
        _x set [1, _point select 0];
        _x set [2, _point select 1];
    };
} forEach _holes;

// Preserve every existing hole, including treatment-created punctures. A joining
// viewer must never delete another provider's work.
// Preserve record indices: treatment requests and native coverage snapshots
// refer to these identities. Regrouping by face can reassign an existing seal.
_holes = _holes select {(_x select 0) in ["front", "back"]};

// seed the same-side point lists from any existing holes, so newly generated wounds space against them too. it is
// used by the rejection sampling of _fnc_mkHole above.
private _frontPts = [];
private _backPts = [];
{
    if (_x isEqualType [] && {count _x >= 3}) then {
        private _pt = [_x select 1, _x select 2];
        if ((_x select 0) == "back") then { _backPts pushBack _pt } else { _frontPts pushBack _pt };
    };
} forEach _holes;

private _processed = _patient getVariable ["ACME_CS_processedPenetratingCount", -1];
if !(_processed isEqualType 0 && {finite _processed}) then {_processed = -1;};
if (_processed < 0) then {
    _processed = if (count _holes > 0) then {count _tracked} else {0};
};
// later experimental builds could leave a processed count behind with no persistent hole records. in that state the
// original generator would appear to have no wounds to convert. reset only that stale combination, so the same
// casualty can be retested without respawning or manually clearing variables.
if (count _holes == 0 && {count _tracked > 0}) then {_processed = 0;};
_processed = ((floor _processed) max 0) min count _tracked;

private _exitFactor = missionNamespace getVariable ["ACME_CS_exitFactor", 0.6];
if !(_exitFactor isEqualType 0 && {finite _exitFactor} && {_exitFactor >= 0}) then {_exitFactor = 0.6;};
private _frontCount = {(_x select 0) == "front"} count _holes;
private _backCount = {(_x select 0) == "back"} count _holes;
private _totalCount = count _holes;

for "_recordIndex" from _processed to ((count _tracked) - 1) do {
    private _record = _tracked select _recordIndex;
    private _id = _record param [0, -1];
    private _damage = _record param [1, -1];
    private _stamp = _record param [2, -1];
    // Backfilled ACE open-wound records are historical, not a new impact.
    // They can already have been covered by the native instant-seal action.
    private _historical = (_stamp isEqualType 0) && {finite _stamp} && {_stamp < 0};
    private _coveredRecord = (_recordIndex < _nativeCount) || {_nativeCount >= 0 && {_historical}};
    private _curve = _injuryMap getOrDefault [_id, [0.25, 0, 1, 0.3]];
    _curve params ["_minDamage", "_minChance", "_maxDamage", "_maxChance"];

    // Exact live impacts scale exit-wound probability from their actual damage. Historical ACE backfill has no
    // trustworthy damage value, so use the midpoint of that wound type instead of pretending every old wound was
    // maximum-energy trauma.
    private _injuryChance = (_minChance + _maxChance) * 0.5;
    if (_damage isEqualType 0 && {finite _damage} && {_damage >= 0}) then {
        _injuryChance = linearConversion [_minDamage, _maxDamage, _damage, _minChance, _maxChance, true];
    };
    if !(_injuryChance isEqualType 0 && {finite _injuryChance}) then {_injuryChance = _maxChance;};

    // Every eligible penetrating event can contribute an entrance wound, but neither live impacts nor historical
    // backfill may bypass the chest-wide visual cap. Damage affects whether the same track also produces an exit.
    if (_totalCount < _maxTotalHoles && {_frontCount < _maxPerSide}) then {
        _holes pushBack ((["front", _coveredRecord] call _fnc_mkHole) + [controlNull, controlNull]);
        _frontCount = _frontCount + 1;
        _totalCount = _totalCount + 1;
    };

    private _exitChance = (_injuryChance * _exitFactor) max 0 min 1;
    if (_totalCount < _maxTotalHoles && {_backCount < _maxPerSide} && {random 1 < _exitChance}) then {
        _holes pushBack ((["back", _coveredRecord] call _fnc_mkHole) + [controlNull, controlNull]);
        _backCount = _backCount + 1;
        _totalCount = _totalCount + 1;
    };
};
_processed = count _tracked;

// Closed pleural air and hemothorax do not create external skin wounds.
// Genuine tracked penetrating wounds above are the only source of new holes.

if ((_patient getVariable ["ACME_CS_processedPenetratingCount", -1]) != _processed) then {
    _patient setVariable ["ACME_CS_processedPenetratingCount", _processed, true];
};
private _data = _holes apply {_x select [0, 6]};
if (!(_data isEqualTo (_patient getVariable ["ACME_CS_holeData", []])) || {count (_patient getVariable ["ACME_CS_netSnapshot", []]) == 0}) then {
    _patient setVariable ["ACME_CS_holeData", _data, true];
    [_patient] call ACME_fnc_chestSealBumpVer;
};

