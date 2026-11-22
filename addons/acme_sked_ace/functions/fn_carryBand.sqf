/*
 * The rubber band between two rescuers who carry a litter. Run every frame where a rescuer is local, for him.
 * The two belong one litter and two reaches apart (the litter says how far: acme_carry_span). When they are
 * further apart or closer than that by more than 8 cm, the one who makes it worse by the way he walks is slowed
 * and the one who could make it better by keeping on is let walk faster: by up to 12 % each over the next
 * 20 cm, so two who both walk fall into step without noticing much. Beyond that the one who makes it worse is
 * held back hard, and at 55 cm he all but stands: one cannot pull away from a partner who stands, nor push into
 * him.
 * It works on the speed of his animations, which is his walking speed.
 * Arguments: 0: this rescuer, 1: the other, 2: the litter, 3: this one has the head end <BOOL>.
 * Returns: how much further apart than they belong they are (m; negative: closer).
 */
params ["_unit", "_other", "_litter", "_front"];
private _a = getPosASLVisual _unit;
private _b = getPosASLVisual _other;
private _stretch = (_a distance2D _b) - (_litter getVariable ["acme_carry_span", 3]);
// the way the litter goes: from its foot end to its head end
private _axis = if (_front) then {_a vectorDiff _b} else {_b vectorDiff _a};
_axis set [2, 0];
_axis = vectorNormalized _axis;
// Which way he goes along it: for the player of this machine what he presses (so he can be held to a crawl and
// it is still known that he pushes), for anybody else how he moves.
private _velocity = velocity _unit;
private _ahead = (_velocity select 0) * (_axis select 0) + (_velocity select 1) * (_axis select 1);
private _least = 0.08;
if (hasInterface && {_unit isEqualTo (call ace_common_fnc_player)}) then {
    private _forth = ((inputAction "MoveForward") + (inputAction "MoveFastForward") + (inputAction "MoveSlowForward") - (inputAction "MoveBack")) max -1 min 1;
    private _right = ((inputAction "TurnRight") - (inputAction "TurnLeft")) max -1 min 1;
    if (abs _forth > 0.1 || {abs _right > 0.1}) then {
        private _facing = vectorDirVisual _unit;
        _ahead = 1.4 * ((((_facing select 0) * _forth + (_facing select 1) * _right) * (_axis select 0))
            + (((_facing select 1) * _forth - (_facing select 0) * _right) * (_axis select 1)));
        _least = 0.03;
    };
};
private _over = (abs _stretch) - 0.08;
private _coef = 1;
if (_over > 0) then {
    // walking ahead makes it worse for the front one when they are stretched and for the rear one when they are
    // pressed together; walking back, the other way round
    private _worse = if (_front) then {
        (_stretch > 0 && {_ahead > 0.1}) || {_stretch < 0 && {_ahead < -0.1}}
    } else {
        (_stretch < 0 && {_ahead > 0.1}) || {_stretch > 0 && {_ahead < -0.1}}
    };
    // gently over the first 20 cm (both fall into step, and neither notices much), then hard
    private _gentle = (_over min 0.2) * 0.6;
    if (_worse) then {
        _coef = 1 - _gentle;
        if (_over > 0.2) then {_coef = (0.88 - ((_over - 0.2) / 0.27) * 0.88) max _least;};
    } else {
        if (abs _ahead > 0.1) then {_coef = 1 + _gentle;};
    };
};
private _now = _unit getVariable ["acme_carry_coef", 1];
_now = _now + (_coef - _now) * ((diag_deltaTime * 8) min 1);
_unit setVariable ["acme_carry_coef", _now];
_unit setVariable ["acme_carry_banded", true];
// (with the jog's share, and with ACE's fatigue kept off that speed: fn_paceApply.sqf)
[_unit] call acme_sked_fnc_paceApply;
_stretch
