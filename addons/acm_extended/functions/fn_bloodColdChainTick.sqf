// the server-authoritative blood cold-chain pass. it runs on the server, the one machine that can see every holder
// at once, which is what lets the freshness of a bag survive a hand-off. the reads are global, and the writes,
// meaning the spoil and the auto-fill on a person, are remoteexec'd to the owner of the item through
// ACME_fnc_ccApply.
// on freshness that survives a hand-off: each blood bag carries a warm time that begins the instant it enters the
// inventory of any holder and only advances while the bag is not kept cold by a cooler. the state is a per-holder
// ledger keyed by netid. when a bag leaves a holder its age goes into a short-lived floating pool, per class, and
// when a bag appears at another holder it pulls an age from that pool first, so a hand-off inherits the clock,
// and it only starts fresh, at warm 0, if the pool is empty, meaning genuinely new blood.
// coolers are tracked the same way, so their coolant clock survives a hand-off, and a cooler only auto-fills its
// rated o- blood when it is new to the world, so a handed-off cooler does not duplicate blood.
// B287: historical interval arguments are accepted but no synthetic age is added.
// Every record carries its last server-time sample; a repeated no-age nudge at
// the same timestamp charges zero and a delayed callback catches up exactly.
private _arguments = [];
if !(isNil "_this") then {if (_this isEqualType []) then {_arguments = _this;};};
private _excludeBox = _arguments param [1, objNull];
if !(missionNamespace getVariable ["ACME_sys_bloodChain", true]) exitWith {};  // the system toggle. fully off means this stops.
if (!isServer) exitWith {};
private _now = serverTime;
// Every entry path, including loadout nudges and the ordinary periodic scan,
// must release deployed sources before discovering plain receiver inventory.
// A FULL box reconciliation already released its own removals and excludes
// that in-progress box while synchronizing newly admitted cargo.
private _boxes = (allMissionObjects "ACME_BloodCoolerBox_CSWB1U")
    + (allMissionObjects "ACME_BloodCoolerBox_CSWB2U")
    + (allMissionObjects "ACME_BloodCoolerBox_CSWB4U");
{
    if !(_x isEqualTo _excludeBox) then {[_x, _now, "release"] call ACME_fnc_coolerBoxReconcile;};
} forEach _boxes;

private _loose    = missionNamespace getVariable ["ACME_bloodLooseSpoilTime", 1800];
private _fillType = missionNamespace getVariable ["ACME_coolerFillType", "ON"];
private _ttl      = missionNamespace getVariable ["ACME_bloodFloatTTL", 180];
private _store    = missionNamespace getVariable ["ACME_ccByHolder", createHashMap];
private _bagFloat = missionNamespace getVariable ["ACME_ccBagFloat", createHashMap];
private _cooFloat = missionNamespace getVariable ["ACME_ccCoolFloat", createHashMap];

private _volOf    = ACME_fnc_coolerBagVolume;
private _isBag    = { params ["_c"]; (_c find "ACM_BloodBag_" == 0) || {_c find "ACM_FreshBloodBag_" == 0} };
private _isCooler = { params ["_c"]; _c find "ACME_BloodCooler_" == 0 };
private _snap     = {
    params ["_h"];
    if (_h isKindOf "CAManBase") then { (uniformItems _h) + (vestItems _h) + (backpackItems _h) }
    else {
        (getItemCargo _h) params [["_c", []], ["_n", []]];
        private _o = []; { private _cc = _x; for "_i" from 1 to (_n param [_forEachIndex, 0]) do { _o pushBack _cc; }; } forEach _c; _o
    }
};

// prune the expired floating ages.
{ private _c = _x; private _a = (_bagFloat get _c) select {(_now - (_x select 1)) < _ttl}; if (_a isEqualTo []) then { _bagFloat deleteAt _c; } else { _bagFloat set [_c, _a]; }; } forEach (keys _bagFloat);
{ private _c = _x; private _a = (_cooFloat get _c) select {(_now - (_x select 1)) < _ttl}; if (_a isEqualTo []) then { _cooFloat deleteAt _c; } else { _cooFloat set [_c, _a]; }; } forEach (keys _cooFloat);

// Corpses keep aging. Deployed cooler cargo has exactly one dedicated owner.
private _holders = (allUnits + allDeadMen + vehicles) select {
    !(_x isKindOf "ACME_BloodCoolerBox_CSWB1U")
        && {!(_x isKindOf "ACME_BloodCoolerBox_CSWB2U")}
        && {!(_x isKindOf "ACME_BloodCoolerBox_CSWB4U")}
};
_holders = _holders arrayIntersect _holders;

// gather the current counts and the existing ledgers per holder.
private _data = [];
{
    private _h = _x; private _nid = netId _h;
    private _rec = _store getOrDefault [_nid, [[], []]];
    private _inv = [_h] call _snap;
    private _cb = createHashMap; private _cc = createHashMap;
    { private _it = _x; if ([_it] call _isBag) then { _cb set [_it, (_cb getOrDefault [_it, 0]) + 1]; } else { if ([_it] call _isCooler) then { _cc set [_it, (_cc getOrDefault [_it, 0]) + 1]; }; }; } forEach _inv;
    private _hasState = (count _cb > 0) || {count _cc > 0} || {!((_rec select 0) isEqualTo [])} || {!((_rec select 1) isEqualTo [])};
    if (_hasState) then {
        _data pushBack [_h, _nid, _cb, _cc, _rec select 0, _rec select 1];
    };
} forEach _holders;

// blood: release the surplus to the float.
{
    _x params ["_h","_nid","_cb","_cc","_bagLedger"];
    private _byClass = createHashMap;
    { _x params ["_bc","_bv","_bw",["_at",_now]]; private _a = _byClass getOrDefault [_bc, []]; _a pushBack [_bw,_at]; _byClass set [_bc, _a]; } forEach _bagLedger;
    private _kept = [];
    {
        private _c = _x; private _ages = _byClass get _c; _ages sort false;
        private _surplus = (count _ages) - (_cb getOrDefault [_c, 0]);
        if (_surplus > 0) then { for "_i" from 1 to _surplus do { private _e = _ages deleteAt ((count _ages) - 1); private _fa = _bagFloat getOrDefault [_c, []]; _fa pushBack [(_e # 0) + ((_now - (_e # 1)) max 0), _now]; _bagFloat set [_c, _fa]; }; };
        { _kept pushBack [_c, ([_c] call _volOf), _x # 0, _x # 1]; } forEach _ages;
    } forEach (keys _byClass);
    _x set [4, _kept];
} forEach _data;
// blood: fill the deficits from the float, inheriting the age, and otherwise at warm 0.
{
    _x params ["_h","_nid","_cb","_cc","_keptBag"];
    private _keptCnt = createHashMap;
    { _x params ["_bc"]; _keptCnt set [_bc, (_keptCnt getOrDefault [_bc, 0]) + 1]; } forEach _keptBag;
    private _final = +_keptBag;
    {
        private _c = _x; private _need = (_cb get _c) - (_keptCnt getOrDefault [_c, 0]);
        if (_need > 0) then {
            for "_i" from 1 to _need do {
                private _w = 0; private _fa = _bagFloat getOrDefault [_c, []];
                if (count _fa > 0) then {
                    private _ranked = _fa apply {[(_x # 0) + ((_now - (_x # 1)) max 0), _x]};
                    _ranked sort false;
                    _w = (_ranked deleteAt 0) # 0;
                    _bagFloat set [_c, _ranked apply {_x # 1}];
                };
                _final pushBack [_c, ([_c] call _volOf), _w, _now];
            };
        };
    } forEach (keys _cb);
    _x set [4, _final];
} forEach _data;

// coolers: release the surplus to the float.
{
    _x params ["_h","_nid","_cb","_cc","_keptBag","_coolLedger"];
    private _byClass = createHashMap;
    { _x params ["_kc","_at"]; private _a = _byClass getOrDefault [_kc, []]; _a pushBack _at; _byClass set [_kc, _a]; } forEach _coolLedger;
    private _kept = [];
    {
        private _c = _x; private _ages = _byClass get _c; _ages sort true;
        private _surplus = (count _ages) - (_cc getOrDefault [_c, 0]);
        if (_surplus > 0) then { for "_i" from 1 to _surplus do { private _w = _ages deleteAt ((count _ages) - 1); private _fa = _cooFloat getOrDefault [_c, []]; _fa pushBack [_w, _now]; _cooFloat set [_c, _fa]; }; };
        { _kept pushBack [_c, _x]; } forEach _ages;
    } forEach (keys _byClass);
    _x set [5, _kept];
} forEach _data;
// coolers: fill the deficits from the float, inheriting the coolant, and otherwise fresh now with an auto-fill of
// blood.
private _autofill = [];
{
    _x params ["_h","_nid","_cb","_cc","_keptBag","_keptCool"];
    private _keptCnt = createHashMap;
    { _x params ["_kc"]; _keptCnt set [_kc, (_keptCnt getOrDefault [_kc, 0]) + 1]; } forEach _keptCool;
    private _final = +_keptCool;
    {
        private _c = _x; private _need = (_cc get _c) - (_keptCnt getOrDefault [_c, 0]);
        if (_need > 0) then {
            for "_i" from 1 to _need do {
                private _fa = _cooFloat getOrDefault [_c, []]; private _start = _now; private _fresh = true;
                if (count _fa > 0) then { _fa sort true; private _e = _fa deleteAt 0; _start = _e select 0; _cooFloat set [_c, _fa]; _fresh = false; };
                _final pushBack [_c, _start];
                if (_fresh) then {
                    private _bags = floor ((getNumber (configFile >> "CfgWeapons" >> _c >> "ACME_coolerCapacityMl")) / 500);
                    if (_bags > 0 && {missionNamespace getVariable ["ACME_coolerAutoFill", false]}) then { _autofill pushBack [_h, format ["ACM_BloodBag_%1_500", _fillType], _bags]; };
                };
            };
        };
    } forEach (keys _cc);
    _x set [5, _final];
} forEach _data;
// apply the auto-fill. the new blood is picked up as warm-0 and cooler-covered on the next pass.
{
    _x params ["_h","_bc","_n"];
    if (_h isKindOf "CAManBase") then { private _add = []; for "_i" from 1 to _n do { _add pushBack _bc; }; [_h, [], _add] remoteExec ["ACME_fnc_ccApply", _h]; }
    else { _h addItemCargoGlobal [_bc, _n]; };
} forEach _autofill;

// coverage, age and spoil.
{
    _x params ["_h","_nid","_cb","_cc","_bagLedger","_coolLedger"];
    // Client inventory replication can lag its seed event. Keep the exact seed
    // until enough physical items are visible, then bind it to a distinct
    // youngest admission before any spoilage decision. No missing seed is
    // terminally acknowledged, and no existing older bag loses its exposure.
    private _pending = _h getVariable ["ACME_bloodExposurePending", []];
    if !(_pending isEqualTo []) then {
        private _waiting = [];
        private _claimed = [];
        private _tokens = _h getVariable ["ACME_bloodExposureSeedTokens", createHashMap];
        {
            _x params ["_request", "_class", "_warm", "_sampled", "_expected"];
            private _candidates = [];
            private _total = 0;
            {
                if ((_x # 0) == _class) then {
                    _total = _total + 1;
                    if !(_forEachIndex in _claimed) then {
                        _candidates pushBack [(_x # 2) + ((_now - (_x param [3, _now])) max 0), _forEachIndex];
                    };
                };
            } forEach _bagLedger;
            if (_total < _expected || {_candidates isEqualTo []}) then {_waiting pushBack +_x;}
            else {
                _candidates sort true;
                private _index = (_candidates # 0) # 1;
                private _entry = +(_bagLedger # _index);
                private _value = ((_candidates # 0) # 0) max (_warm + ((_now - _sampled) max 0));
                _entry set [2, _value];
                _entry set [3, _now];
                _bagLedger set [_index, _entry];
                _claimed pushBack _index;
                private _machineKey = format ["%1:%2", _nid, _request # 0];
                private _history = _tokens getOrDefault [_machineKey, [0, []]];
                private _floor = _history # 0;
                private _seen = +(_history # 1);
                _seen pushBack [_request # 1, _class, _value, _now];
                _seen sort true;
                while {count _seen > 128} do {_floor = (_seen deleteAt 0) # 0;};
                _tokens set [_machineKey, [_floor, _seen]];
                ["ACME_bloodExposureReply", [_h, _request, _class, _value, _now], _h] call CBA_fnc_targetEvent;
            };
        } forEach _pending;
        _h setVariable ["ACME_bloodExposurePending", _waiting];
        _h setVariable ["ACME_bloodExposureSeedTokens", _tokens];
    };
    private _coverMl = 0;
    { _x params ["_kc","_at"]; private _chain = getNumber (configFile >> "CfgWeapons" >> _kc >> "ACME_coolerColdChainTime"); if (_chain <= 0 || {(_now - _at) < _chain}) then { _coverMl = _coverMl + getNumber (configFile >> "CfgWeapons" >> _kc >> "ACME_coolerCapacityMl"); }; } forEach _coolLedger;
    // the true-container model: a cooler keeps cold only what is inside it, which is handled client-side, so loose
    // blood warms.
    if (!(missionNamespace getVariable ["ACME_coolerAutoCover", false])) then { _coverMl = 0; };
    private _byVol = _bagLedger apply { [_x select 1, _x] }; _byVol sort false;
    private _keptMl = 0; private _kept = []; private _spoil = [];
    {
        (_x select 1) params ["_bc","_bv","_bw",["_at",_now]];
        if (_keptMl + _bv <= _coverMl) then { _keptMl = _keptMl + _bv; _kept pushBack [_bc, _bv, _bw, _now]; }
        else { private _nw = _bw + ((_now - _at) max 0); if (_nw >= _loose && {missionNamespace getVariable ["ACME_bloodSpoilEnabled", true]}) then { _spoil pushBack _bc; } else { _kept pushBack [_bc, _bv, _nw, _now]; }; };
    } forEach _byVol;
    if !(_spoil isEqualTo []) then {
        if (_h isKindOf "CAManBase") then { private _add = []; { _add pushBack "ACME_SpoiledBlood"; } forEach _spoil; [_h, _spoil, _add] remoteExec ["ACME_fnc_ccApply", _h]; }
        else { { _h addItemCargoGlobal [_x, -1]; _h addItemCargoGlobal ["ACME_SpoiledBlood", 1]; } forEach _spoil; };
    };
    _store set [_nid, [_kept, _coolLedger]];
    private _snapshot = [_kept apply {[_x # 0, _x # 1, _x # 2]}, _now];
    if !((_h getVariable ["ACME_bloodExposure", []]) isEqualTo _snapshot) then {
        _h setVariable ["ACME_bloodExposure", _snapshot, true];
    };
} forEach _data;

// prune the holders that have left the world.
{ if (isNull (objectFromNetId _x)) then { _store deleteAt _x; }; } forEach (keys _store);

missionNamespace setVariable ["ACME_ccByHolder", _store];
missionNamespace setVariable ["ACME_ccBagFloat", _bagFloat];
missionNamespace setVariable ["ACME_ccCoolFloat", _cooFloat];
missionNamespace setVariable ["ACME_ccBrokerFrame", diag_frameNo];
