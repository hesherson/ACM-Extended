/*
 * Phase 25 subsystem ownership: Blood-fridge/cooler storage, cold-chain, clot-pop and loadout-change runtime.
 *
 * Extracted intact from ACME_fnc_postInit and invoked at the original point so startup
 * sequencing and CBA registration order are preserved.
 */

// blood fridge.
// the server tick drives the auto open and close of every fridge, from the viewer pings, and the daily
// restock.
if (isServer) then {
    [{ call ACME_fnc_bloodFridgeTick }, 0.25, []] call CBA_fnc_addPerFrameHandler;
};

// owner-side viewer bookkeeping. a client pings the fridge through targetevent while its ACE menu is on it,
// and the tick treats the fridge as in use while any ping is fresh. it is keyed by netid, so a player counts at
// most once.
["ACME_bfViewPing", {
    params ["_anchor", "_player"];
    if (!isServer || {isNull _anchor} || {isNull _player} || {!alive _player}
        || {_player distance _anchor > 4.5} || {!(_anchor getVariable ["ACME_bloodFridge", false])}) exitWith {};
    private _v = _anchor getVariable ["ACME_bf_viewers", createHashMap];
    _v set [netId _player, diag_tickTime];
    _anchor setVariable ["ACME_bf_viewers", _v];
}] call CBA_fnc_addEventHandler;
["ACME_bfViewStop", {
    params ["_anchor", "_player"];
    if (!isServer || {isNull _anchor} || {isNull _player}) exitWith {};
    private _v = _anchor getVariable ["ACME_bf_viewers", createHashMap];
    _v deleteAt (netId _player);
    _anchor setVariable ["ACME_bf_viewers", _v];
}] call CBA_fnc_addEventHandler;

// Stock authority stays on the server even if engine ownership of a furniture object changes.
["ACME_bfTake", {_this call ACME_fnc_bloodFridgeTakeOwner;}] call CBA_fnc_addEventHandler;
["ACME_bfGive", {_this call ACME_fnc_bloodFridgeReceive;}] call CBA_fnc_addEventHandler;
["ACME_bfTakeStop", {
    params ["_anchor", "_player", "_token"];
    if (!isServer || {isNull _anchor} || {isNull _player}) exitWith {};
    private _takers = _anchor getVariable ["ACME_bf_takers", createHashMap];
    private _key = netId _player;
    if !(((_takers getOrDefault [_key, []]) param [1, []]) isEqualTo _token) exitWith {};
    _takers deleteAt _key;
    // Only retire this taker's browse entry. Another viewer/taker keeps the door open.
    private _viewers = _anchor getVariable ["ACME_bf_viewers", createHashMap];
    _viewers deleteAt _key;
    call ACME_fnc_bloodFridgeTick;
}] call CBA_fnc_addEventHandler;

// client. while the world interaction menu is open, poll the selected target and ping any fridge it lands
// on.
["ace_interactMenuOpened", {
    params ["_menuType"];
    // ACE world interaction is 0; 1 is self-interaction and never selects the fridge.
    if (_menuType != 0) exitWith {};
    if (!isNil "ACME_bf_pollPFH") exitWith {};
    ACME_bf_pollPFH = [{ call ACME_fnc_bloodFridgeMenuPoll }, 0.2, []] call CBA_fnc_addPerFrameHandler;
}] call CBA_fnc_addEventHandler;
["ace_interactMenuClosed", {
    if (isNil "ACME_bf_pollPFH") exitWith {};
    [ACME_bf_pollPFH] call CBA_fnc_removePerFrameHandler;
    ACME_bf_pollPFH = nil;
    private _lf = ACE_player getVariable ["ACME_bf_lastFridge", objNull];
    if (!isNull _lf) then {
        ["ACME_bfViewStop", [_lf, ACE_player]] call CBA_fnc_serverEvent;
        ACE_player setVariable ["ACME_bf_lastFridge", objNull];
    };
}] call CBA_fnc_addEventHandler;

// blood cooler, a true container.
// a double-click on a cooler in the inventory manages its contents. a local pass ages and spoils what is inside
// once the coolant runs out.
if (hasInterface) then {
    ["CAManBase", "InventoryOpened", {_this call ACME_fnc_coolerInvHook}] call CBA_fnc_addClassEventHandler;
    // NA2: register after ACME_coolerContentsDt is initialized below.
};

// Clot pop. The server tick targets the casualty owner and may partially reopen ONE unsecured clot.
 // Applied dressings are never touched by this event.
["ACME_popClots", { _this call ACME_fnc_popClots }] call CBA_fnc_addEventHandler;

// blood cold chain. a cooler keeps blood transfusable and warm blood spoils. freshness is tracked from the
// moment blood enters a holder and survives a hand-off, through a server-authoritative ledger and a short
// floating pool. a cooler arrives pre-loaded with its rated o- blood. the times are compressed hard for
// operations of about 4 h, because a real chain runs 24 to 72 h.
ACME_bloodScanInterval   = 60;  // s between cold-chain passes (also the age step)
ACME_bloodLooseSpoilTime = 1800;  // 30 min in the warm before uncovered blood spoils
ACME_bloodRewarmTime     = 1200;  // 20 min for a hung cold, [cooled], unit to rewarm thermally toward ambient.
                                  // transfusion hypothermia fades to zero across this time; the cold-unit flow tier does not.
ACME_bloodFloatTTL       = 180;  // s that the clock of a handed-off or dropped bag persists in the float pool before a reset.
ACME_coolerFillType      = "ON";  // the blood type a cooler auto-loads with. o-, on, is the universal donor. the options are o, on, a, an, b, bn, ab and abn.
// true-container model, where a double-click on a cooler manages it. blood is kept cold only while it is
// inside a cooler. loose blood therefore always warms, with autocover off, and a cooler no longer dumps loose
// o- into the inventory, with autofill off. a new cooler instead pre-fills its own container with rated o-.
// flip either back to true for the old behavior.
ACME_coolerAutoCover     = false;
ACME_coolerAutoFill      = false;
ACME_coolerContentsDt    = 5;  // s between local cooler-contents aging passes
if (hasInterface) then {
    [{ call ACME_fnc_coolerContentsTick }, ACME_coolerContentsDt, []] call CBA_fnc_addPerFrameHandler;
};
ACME_coolerThawRateInside = 0.2;  // once the coolant is gone, blood inside the box thaws at this fraction of real time.
ACME_coolerBoxScale      = 0.65;  // visual and geometry scale applied to a deployed cooler box. 1 is the vanilla box size.
// fluid-overload clot pop. crystalloid into a hemodynamically unstable, hypovolemic, patient tears clots
// loose.
ACME_clotPop_enabled     = true;
ACME_clotPop_bvThreshold = 5.1;  // blood volume in l below which the patient is unstable. normal is 6, so this is about a 15 percent loss.
ACME_clotPop_chance      = 0.001; // B180: 0.1% base risk per one-minute pass, only while an unsecured clot exists.
ACME_clotPop_fraction    = 0.15;  // at most 0.15 of ONE clotted wound reopens per successful event.
ACME_clotPop_dt          = 60;    // one risk evaluation per minute.
ACME_clotPop_maxChance   = 0.003; // hard 0.3% ceiling per minute after all severity scaling.
ACME_clotPop_nativeChance = 0.0015; // rare instability of a newly formed native clot.
ACME_clotPop_nativeMaxChance = 0.003; // hard cap for native clot-instability scheduling.
ACME_ca_mapEasePerSec    = 0.2;  // mmhg/s that the calcium MAP suppression is walked off. 18 mmhg across about 90 s,
                                  // rather than vanishing on the tick after the syringe goes in.
ACME_clotPop_fluidTypes  = ["Saline", "PlasmaLyte"];  // dilutional fluids that pop clots. add "HTS" or "Plasma" to include them.
ACME_clotPop_cooldown    = 600; // ten-minute shared cooldown after any scheduled/successful clot-pop event.
if (isServer) then {
    [{ [] call ACME_fnc_bloodColdChainTick }, ACME_bloodScanInterval, []] call CBA_fnc_addPerFrameHandler;
    [{ [] call ACME_fnc_clotPopTick }, ACME_clotPop_dt, []] call CBA_fnc_addPerFrameHandler;
    // a deployed cooler box ages its real blood cargo here. it is the box equivalent of the per-player contents
    // tick.
    [{ [] call ACME_fnc_coolerBoxColdChainTick }, ACME_coolerContentsDt, []] call CBA_fnc_addPerFrameHandler;
};
// react the instant the kit of a player changes, on an arsenal close, a pickup or a hand-off. this nudges a
// no-age server pass, so a new cooler fills and new blood is stamped promptly. it needs remoteexec of ACME
// functions to be permitted.
// when a wholesale loadout is applied, an arsenal load or a setUnitLoadout on the same unit rather than a
// single item pickup, a cooler in that loadout is a fresh unit. so this clears the per-player coolant clock and
// virtual store and lets the contents tick re-stock it with full coolant. respawn already makes a fresh unit
// with no clock, so that path is fine on its own. it tells a full load from looting by counting how many
// top-level loadout slots change at once. a single pickup touches one and a full load touches several.
["loadout", {
    // Loadout can fire several times during one arsenal/loadout transaction. Coalesce the client->server cold-chain
    // nudge before it enters the network; the server already performs its own second-stage coalescing.
    private _nudgeNow = diag_tickTime;
    private _nudgeLast = uiNamespace getVariable ["ACME_ccNudgeSentAt", -1];
    if (_nudgeLast < 0 || {_nudgeNow - _nudgeLast >= 0.5}) then {
        uiNamespace setVariable ["ACME_ccNudgeSentAt", _nudgeNow];
        remoteExecCall ["ACME_fnc_bloodColdChainNudge", 2];
    };
    [] call ACME_fnc_coolerAutoStore;
    private _p = ACE_player;
    if (!isNull _p) then {
        private _new = getUnitLoadout _p;
        private _old = _p getVariable ["ACME_lastLoadoutSig", []];
        _p setVariable ["ACME_lastLoadoutSig", _new];
        if (_old isNotEqualTo []) then {
            private _diffs = 0;
            { if !((_new param [_x, []]) isEqualTo (_old param [_x, []])) then { _diffs = _diffs + 1; }; } forEach [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
            if (_diffs >= 3) then {
                [_p, "coolant", createHashMap, true] call ACME_fnc_coolerStateCommit;
                [_p, "store", createHashMap, true] call ACME_fnc_coolerStateCommit;
            };
        };
        // ventilator boot re-arm. if the ventilator was reloaded, transferred or moved, and any loadout change is
        // signal enough that the device left and re-entered the kit, this re-arms the startup sequence so the next open
        // plays boot again. a preset self-open would otherwise skip boot, and this is what makes it replay.
        _p setVariable ["ACME_vent_booted", false];
    };
}] call CBA_fnc_addPlayerEventHandler;
