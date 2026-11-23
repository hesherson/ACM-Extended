// this spawns a Megacode Kelly training dummy: a bare, gearless casualty that lies in ACM_LyingState and can never
// stand, crouch or go prone, used as a fully controllable manikin through the megacode control panel.
// it is script-callable as _dummy = [_pos, _dir] call ACME_fnc_megacodeSpawn.
// _this is [_pos, an atl or an object, and _dir].
params [["_pos", [0,0,0]], ["_dir", 0]];
if (_pos isEqualType objNull) then { _dir = getDir _pos; _pos = getPosATL _pos; };

if (!isServer) exitWith { objNull };  // the manikin, its keeper and its cable live on the server.
private _grp = createGroup [civilian, true];
private _u = _grp createUnit ["C_man_1", _pos, [], 0, "CAN_COLLIDE"];
if (isNull _u) exitWith { deleteGroup _grp; objNull };
_u setPosATL _pos;
_u setDir _dir;

// completely bare: no uniform, no gear and an empty inventory.
removeAllWeapons _u;
removeAllItems _u;
removeAllAssignedItems _u;
removeBackpack _u;
removeVest _u;
removeUniform _u;
removeHeadgear _u;
removeGoggles _u;
{ _u unlinkItem _x } forEach (assignedItems _u);
removeAllContainers _u;
_u unassignItem "NVGoggles";

// manikin behavior: inert ai, never a threat, and fully damageable so wounds can be applied.
_u setVariable ["ACME_isMegacode", true, true];
if (isNil "ACME_megacode_units") then {ACME_megacode_units = [];};
ACME_megacode_units pushBackUnique _u;
_u setName "Megacode Kelly";
_u disableAI "ALL";
// Keep the skeleton enabled for clinical poses and seizure gestures; autonomous movement stays disabled.
_u enableAI "ANIM";
_u setBehaviour "CARELESS";
_u setCaptive true;
_u allowDamage true;
[_u, [["allowUnconParam", true, true]]] call ACM_core_fnc_setAceMedicalState;
// plot armor: this manikin can never actually die. a per-unit ai-unconsciousness plus instant-death immunity
// blocks every dead transition in ACM's state machine, and the keeper pfh below pins the arrest timer and blood
// and runs the fatal clock that instead triggers the announce, mimic-death and auto-reset sequence.
[_u, [["aiUnconsciousness", true, true]]] call ACM_core_fnc_setAceMedicalState;
[_u, [["instantDeathImmune", true, true]]] call ACM_core_fnc_setAceMedicalState;
[_u, [["deathBlocked", true, true]]] call ACM_core_fnc_setAceMedicalState;
_u setVariable ["ACME_MC_operatorClient", objNull, true];  // set when an operator opens the panel.

// the baseline: no injuries, full blood, sinus and lying.
[_u, true, true] call ACM_core_fnc_setLyingState;
// seed the panel vitals, both live and the ramp targets, so the monitor reads normal and the first slider press
// eases in.
{
    _x params ["_k", "_v"];
    _u setVariable [_k, _v, true];
} forEach [
    ["ACME_MC_HR", 78], ["ACME_MC_HRTgt", 78], ["ACME_MC_SpO2", 98], ["ACME_MC_SpO2Tgt", 98],
    ["ACME_MC_SBP", 122], ["ACME_MC_SBPTgt", 122], ["ACME_MC_DBP", 78], ["ACME_MC_DBPTgt", 78],
    ["ACME_MC_RR", 14], ["ACME_MC_RRTgt", 14], ["ACME_MC_EtCO2", 38], ["ACME_MC_EtCO2Tgt", 38],
    ["ACME_MC_Temp", 37.0]
];
[_u, 0, true, false] call ACME_fnc_rhythmActiveCommit;
[_u, 0] call ACME_fnc_rhythmSet;

// settle into the lying pose and start the keeper that forbids standing, crouching and going prone.
[_u] call ACME_fnc_megacodeStanceLock;

// the instructor station: an olive laptop about 3 m away, joined to the manikin by a thin cable that runs into a
// plug on the laptop's back face (ACME_fnc_megacodeCableBuild).
private _lpPos = _u getPos [3, _dir];
private _laptop = "Land_Laptop_03_olive_F" createVehicle _lpPos;
_laptop setPosATL [(_lpPos select 0), (_lpPos select 1), ((getPosATL _laptop) select 2)];
private _lapDir = _dir + 180;  // the laptop is turned 180 degrees, so the screen faces the operator standing on the far side.
_laptop setDir _lapDir;
_laptop setVariable ["ACME_MC_laptopBaseDir", _lapDir, true];  // the reference heading for the cable tuner frame.
_laptop setVariable ["ACME_MC_laptopBasePos", getPosATL _laptop, true];  // the reference position for the laptop move.
// re-apply the tuned laptop position. the x, y and z persist across spawns.
private _lpOff = +(missionNamespace getVariable ["ACME_megacode_laptopPosOffset", [0,0,0]]);
[_laptop, _lpOff select 0, _lpOff select 1, _lpOff select 2] call ACME_fnc_megacodeLaptopMove;
_laptop setVariable ["ACME_isMegacodeLaptop", true, true];
_laptop setVariable ["ACME_megacodeDummy", _u, true];
_u setVariable ["ACME_MC_laptop", _laptop, true];
_u setVariable ["ACME_MC_spawnDir", _dir, false];  // the respawn re-uses the placement direction, not a corpse's heading.

// the cable: plug on the laptop, hidden rope helpers and the rope, all made on this machine (the server).
[_u] call ACME_fnc_megacodeCableBuild;

// a manikin deleted from outside (zeus, a script) takes its laptop and cable with it instead of leaving them behind.
_u addEventHandler ["Deleted", {
    params ["_unit"];
    private _rope = _unit getVariable ["ACME_MC_rope", objNull];
    if (!isNull _rope) then {ropeDestroy _rope;};
    {if (!isNull _x) then {deleteVehicle _x;};} forEach (_unit getVariable ["ACME_MC_helpers", []]);
    private _lap = _unit getVariable ["ACME_MC_laptop", objNull];
    if (!isNull _lap) then {deleteVehicle _lap;};
}];

// the spawn confirmation popup is removed. placing the manikin is a deliberate act by whoever placed it, and the
// laptop is visibly right there, so the message told the person who did it something they already knew.

// the server-side keeper. it enforces the plot armor and runs the fatal clock, from death into mimic and
// auto-reset.
[{ _this call ACME_fnc_megacodeWatch }, 1.0, [_u]] call CBA_fnc_addPerFrameHandler;

_u
