// pull a seated catheter out of the arm.
// call it from the tick as [_drag] call ACME_fnc_ivMinigamePullTick. the pull is begun by fn_ivminigameclick.
//
// on the resistance.
// a catheter does not slide out. the dressing holds it, the vessel grips the cannula, and the first movement
// takes real force. once it is moving it comes freely.
// the mouse cannot push back, so the resistance is shown three ways at once, and together they read as force.
// the catheter does not move at all until the pull passes a breakaway threshold. below that the panel shakes in
// proportion to how hard the medic is pulling, which is the tug of something that is holding. above it the
// catheter starts to move, and the grip falls away as it comes out, so the last part is quick.
// the pointer is pinned to the hub for the whole pull, exactly as it is for the push, so the drag is unbounded.
params [["_drag", false]];
if ((uiNamespace getVariable ["ACME_IV_PullIdx", -1]) < 0) exitWith {};
private _rect = uiNamespace getVariable ["ACME_IV_BodyRect", []];
if (_rect isEqualTo []) exitWith {};
_rect params ["_bx", "_by", "_bw", "_bh"];

// let go and the catheter stays where it is. it does not slide back in.
if (!_drag) exitWith { [] call ACME_fnc_ivMinigamePullStop; };

private _pin = uiNamespace getVariable ["ACME_IV_PullPin", []];
if !(_pin isEqualType [] && {count _pin >= 2}) exitWith {
    uiNamespace setVariable ["ACME_IV_PullPin", getMousePosition];
};
_pin params ["_px", "_py"];
private _m = getMousePosition;
_m params ["_mx", "_my"];

private _dux = (_mx - _px) * safeZoneWAbs;
private _duy = (_my - _py) * safeZoneH;

// the axis of the catheter. a pull is the reverse of a push, so the sign is inverted.
private _suffix = uiNamespace getVariable ["ACME_IV_PullSuffix", ""];
private _geometry = [_suffix, uiNamespace getVariable ["ACME_IV_PullAngle", 0]] call ACME_fnc_ivCathGeometry;
(_geometry select 3) params ["_sx", "_sy"];
private _len = sqrt (_sx * _sx + _sy * _sy);
if (_len <= 0) exitWith {};
_sx = _sx / _len;
_sy = _sy / _len;
// Express both mouse axes in vertical-pixel UI units before taking the dot product.
private _aspect = pixelW / (pixelH max 1e-9);
_dux = _dux / _aspect;

// positive means the medic is pulling the catheter out.
private _proj = -(((_dux * _sx) + (_duy * _sy)));

// pin the pointer back on the hub.
setMousePosition [_px, _py];

private _prog = uiNamespace getVariable ["ACME_IV_PullProg", 0];

// the breakaway.
// it is a speed, in body heights per second, not a distance moved in one frame. measured per frame it would be
// easier on a machine running at 40 fps than on one running at 144, because each frame carries more travel.
// the grip falls away as the catheter comes out, because what holds it is the part that is still in.
private _dt = diag_deltaTime max 0.001;
private _speed = _proj / _dt;
private _breakSpeed = (missionNamespace getVariable ["ACME_iv_pullBreakaway", 0.10]) * _bh;
private _grip = 1 - _prog;
private _needed = _breakSpeed * _grip;

if (_proj <= 0) exitWith {};

if (_speed < _needed) exitWith {
    // it is holding. the catheter itself judders in proportion to the pull, so the resistance is felt on the
    // thing that is resisting rather than as a shake of the whole panel. the harder the pull, the more it moves
    // and the less it goes anywhere.
    private _f = (_speed / (_needed max 1e-6)) min 1;
    private _j = (missionNamespace getVariable ["ACME_iv_pullJudder", 0.0035]) * _f;
    private _ctrl0 = uiNamespace getVariable ["ACME_IV_PullCtrl", controlNull];
    if (!isNull _ctrl0) then {
        (uiNamespace getVariable ["ACME_IV_PullBase", [0, 0]]) params ["_jx", "_jy"];
        private _cs0 = uiNamespace getVariable ["ACME_IV_CathScale", 0.62];
        _ctrl0 ctrlSetPosition [_jx + (_j * (random 2 - 1)), _jy + (_j * (random 2 - 1)), _geometry select 0, _geometry select 1];
        _ctrl0 ctrlCommit 0;
    };
};

// it is moving. the travel needed for the whole catheter follows the sprite scale, as the push does.
private _cs = uiNamespace getVariable ["ACME_IV_CathScale", 0.62];
private _full = (missionNamespace getVariable ["ACME_iv_pullTravel", 0.25]) * _bh * _cs;
if (_full <= 0) exitWith {};
_prog = (_prog + (_proj / _full)) max 0 min 1;
uiNamespace setVariable ["ACME_IV_PullProg", _prog];

// the moment it breaks free, one short kick, so the release is felt as well as the hold.
if (!(uiNamespace getVariable ["ACME_IV_PullBroke", false])) then {
    uiNamespace setVariable ["ACME_IV_PullBroke", true];
    playSound "ACE_Sound_Click";
};

// Move only the selected component and its dependants, using stored geometry.
private _layers=uiNamespace getVariable ["ACME_IV_PullLayers",[]];
private _bases=uiNamespace getVariable ["ACME_IV_PullLayerBases",[]];
{
    if (!isNull _x && {_forEachIndex<count _bases}) then {
        private _base=+(_bases select _forEachIndex);
        _base set [0,(_base select 0)-_sx*_aspect*_full*_prog];
        _base set [1,(_base select 1)-_sy*_full*_prog];
        _x ctrlSetPosition _base;_x ctrlSetTextColor [1,1,1,(1-_prog*0.6) max 0.2];_x ctrlCommit 0;
    };
} forEach _layers;

if (_prog >= 1) then { [true] call ACME_fnc_ivMinigamePullStop; };
