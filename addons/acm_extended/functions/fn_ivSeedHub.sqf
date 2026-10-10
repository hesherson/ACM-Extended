// seed a hub mark for an IV that was placed by something other than the mini-game.
// it runs off ACM's own ACM_circulation_setIVLocal event, so it catches EVERY placement path rather than one.
// call it as [_medic, _patient, _bodyPart, _type, _iv, _accessSite] call ACME_fnc_ivSeedHub, which is exactly
// ACM's own argument order for that event.
//
// THE PROBLEM IT FIXES.
// the IV screen draws from ACME_IV_Marks, and fn_ivMinigamePullStop reads a mark to decide which access site to
// tear down. an IV placed by ACM's auto heal facility path, by a mission script, or by any ACM action we do not
// own, writes ACM_circulation_IV_Placement and nothing else. so the line existed, ran fluid and could not be
// seen or pulled, because there was no hub on the limb to grab.
// the Zeus module already seeded its own mark. that covered one path out of several.
//
// WHY AN EVENT AND NOT A POLL.
// ACM raises this event on every placement, ours included, so a handler here fires exactly when the state
// changes and costs nothing the rest of the time. a per frame or per second sweep over units would cost
// something forever to catch an event that happens a few times a mission.
//
// THE DEFERRED CHECK IS WHAT STOPS A DUPLICATE.
// the mini-game calls setIV and writes its own mark, and the order of the two is not guaranteed. so the seed
// waits a beat and then re-reads the marks. if the mini-game has written a hub for this limb and site by then,
// this does nothing. that also means a genuinely unmarked IV is seeded a beat after it appears, which nobody
// can perceive.
params [["_medic", objNull], ["_patient", objNull], ["_bodyPart", ""], ["_type", 0], ["_iv", true], ["_accessSite", -1]];
if (isNull _patient || {!local _patient}) exitWith {};
if (!_iv) exitWith {};  // an IO has no catheter hub on the limb art and no pull path.
if (_type <= 0) exitWith {};  // a type of 0 is a REMOVAL. it clears a site rather than filling one.
private _bp = toLower _bodyPart;
if !(_bp in ["leftarm", "rightarm", "leftleg", "rightleg"]) exitWith {};  // the ej and the torso have no limb view.
if (_accessSite < 0 || {_accessSite > 2}) exitWith {};

// the site name, from the index ACM was given. fn_ivSiteIndex is the one mapping in the addon and this is its
// inverse, kept next to it so the pair cannot drift apart.
private _siteName = ["upper", "middle", "lower"] param [_accessSite, "lower"];

[{
    params ["_patient", "_bp", "_siteName", "_type", "_epoch"];
    if (isNull _patient || {!local _patient}
        || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {};

    // still there? a placement that was undone inside the delay needs no mark.
    private _place = _patient getVariable ["ACM_circulation_IV_Placement", []];
    private _partIdx = ACME_infusion_bodyParts find _bp;
    if (_partIdx < 0) exitWith {};
    private _row = _place param [_partIdx, []];
    private _siteIdx = [_siteName] call ACME_fnc_ivSiteIndex;
    if ((_row param [_siteIdx, 0]) != _type) exitWith {};

    private _marks = _patient getVariable ["ACME_IV_Marks", []];
    if !(_marks isEqualType []) then { _marks = []; };

    // already marked, by the mini-game or by the Zeus module. a mark is [bodyPart, view, u, v, kind, holeTex,
    // frame, gauge, missTime, scale, site, rot, alpha], so element 0 is the limb, element 4 is the kind and
    // element 10 is the access site.
    private _have = _marks findIf {
        ((toLower (_x param [0, ""])) isEqualTo _bp)
        && {(_x param [4, ""]) isEqualTo "hub"}
        && {(toLower (_x param [10, ""])) isEqualTo _siteName}
    };
    if (_have >= 0) exitWith {};

    // the view texture and the vein point come from fn_ivSiteData, the same source the screen draws from, so the
    // hub lands on the vein rather than at a guessed point.
    private _sd = [_bp, _siteName] call ACME_fnc_ivSiteData;
    if (!(_sd isEqualType [])) exitWith {};
    if ((count _sd) < 6) exitWith {};
    _sd params ["_viewTex", "_bandTex", "_bandU", "_bandV", "_veinU", "_veinV"];

    // the gauge from the ACM catheter type, so the hub art matches the line that is running. this is the inverse
    // of the mapping fn_ivMinigameRegister:96 writes, and it is the only other place the pair appears.
    private _gauge = switch (_type) do {
        case 2: { 14 };
        case 1: { 16 };
        case 5: { 18 };
        case 6: { 20 };
        default { 16 };  // an unknown type from another addon draws as the base bore.
    };

    private _frame = if (_bp in ["leftarm", "leftleg"]) then {"_15_left"} else {"_15_right"};
    private _mark = [_bp, _viewTex, _veinU, _veinV, "hub", "", _frame, _gauge, -1, 1, _siteName, 0, 1, 0];
    // The common owner mutation assigns the same stable finishing UID as manual/Zeus placements.
    [_patient, "add", [_mark], _epoch] call ACME_fnc_ivMarkCommit;
}, [_patient, _bp, _siteName, _type, [_patient] call ACME_fnc_clinicalEpoch], (missionNamespace getVariable ["ACME_iv_seedHubDelay", 0.6])] call CBA_fnc_waitAndExecute;
