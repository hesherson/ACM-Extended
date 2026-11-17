private _acmeCanvas = call ACME_fnc_uiCanvas;
_acmeCanvas params ["_uiX", "_uiY", "_uiW", "_uiH"];
// the onload for the megacode cable tuner. it is a bottom-anchored panel, kept low so the laptop and cable stay
// visible while tuning, with a 4-column grid of live sliders.
// column 0 is where the wire plugs into the laptop, the anchor point: the plug x, y and z.
// column 1 is the laptop-side wire-end orientation: the wire pitch, yaw and roll.
// column 2 is the wire-end reach, meaning the steering anchor offset length: the wire reach.
// column 3 is the patient attach and the rope: the dummy y and z, the rope slack and the rope segments.
// each slider applies immediately.
params ["_display"];
uiNamespace setVariable ["ACME_MC_CableTunerDLG", _display];
private _laptop = uiNamespace getVariable ["ACME_MC_CableLaptop", objNull];

private _X = _uiX; private _Y = safeZoneY; private _W = _uiW; private _H = safeZoneH;
private _pX = _X + _W*0.05; private _pY = _Y + _H*0.685; private _pW = _W*0.90; private _pH = _H*0.300;
private _mX = _pX + 0.012; private _mW = _pW - 0.024;
private _top = _pY + _H*0.046;
private _colGap = 0.014;
private _cw  = (_mW - (_colGap * 3)) / 4;
private _rowH = _H*0.052;

private _lOff  = +(missionNamespace getVariable ["ACME_megacode_laptopHoseOffset", [0,-0.13,0.035]]);
private _dOff  = +(missionNamespace getVariable ["ACME_megacode_dummyHoseOffset", [0,0.32,0.12]]);
private _slack = missionNamespace getVariable ["ACME_megacode_ropeSlack", 0.2];
private _seg   = missionNamespace getVariable ["ACME_megacode_ropeSegments", 0];
private _pos   = +(missionNamespace getVariable ["ACME_megacode_laptopPosOffset", [0,0,0]]);
private _rPit  = missionNamespace getVariable ["ACME_megacode_ropeEndPitch", -35];
private _rYaw  = missionNamespace getVariable ["ACME_megacode_ropeEndYaw", 0];
private _rRol  = missionNamespace getVariable ["ACME_megacode_ropeEndRoll", 0];
private _stub  = missionNamespace getVariable ["ACME_megacode_ropeEndStub", 0.12];

private _ctrls = [];
private _mkSlider = {
    params ["_col","_row","_lbl","_key","_min","_max","_val","_dec"];
    private _x = _mX + (_col * (_cw + _colGap));
    private _y = _top + (_row * _rowH);
    private _fmt = if (_dec <= 0) then { str round _val } else { _val toFixed _dec };
    private _t = _display ctrlCreate ["RscText", -1];
    _t ctrlSetPosition [_x, _y, _cw*0.66, _rowH*0.46]; _t ctrlSetText _lbl; _t ctrlSetTextColor [0.8,0.85,0.95,1]; _t ctrlCommit 0;
    private _vc = _display ctrlCreate ["RscText", -1];
    _vc ctrlSetPosition [_x + _cw*0.66, _y, _cw*0.34, _rowH*0.46]; _vc ctrlSetText _fmt; _vc ctrlSetTextColor [1,1,1,1]; _vc ctrlCommit 0;
    private _s = _display ctrlCreate ["RscXSliderH", -1];
    _s ctrlSetPosition [_x, _y + _rowH*0.48, _cw, _rowH*0.40];
    _s sliderSetRange [_min, _max]; _s sliderSetPosition _val;
    _s setVariable ["ct_key", _key]; _s setVariable ["ct_vc", _vc]; _s setVariable ["ct_dec", _dec];
    _s ctrlAddEventHandler ["SliderPosChanged", {
        params ["_c","_v"];
        private _vc = _c getVariable ["ct_vc", controlNull];
        private _dec = _c getVariable ["ct_dec", 3];
        if (!isNull _vc) then { _vc ctrlSetText (if (_dec <= 0) then { str round _v } else { _v toFixed _dec }); };
        [(_c getVariable ["ct_key",""]), _v] call ACME_fnc_megacodeCableApply;
    }];
    _s ctrlCommit 0;
    _ctrls append [_t, _vc, _s];
};

// the args are col, row, label, key, min, max, value and decimals.
// column 0: where the wire plugs into the laptop, the anchor point on the laptop body.
[0, 0, "Plug X (lap)",     "lx",    -0.5,  0.5, (_lOff select 0), 3] call _mkSlider;
[0, 1, "Plug Y (lap)",     "ly",    -0.6,  0.6, (_lOff select 1), 3] call _mkSlider;
[0, 2, "Plug Z (lap)",     "lz",    -0.3,  0.3, (_lOff select 2), 3] call _mkSlider;
// column 1: the laptop-side wire-end orientation. it steers where the wire meets the laptop, replacing the laptop
// x, y and z. the pitch tips the wire down into the laptop instead of letting it stick straight up, and the yaw
// swings it sideways. roll is rotationally a no-op for a single wire anchor and is exposed for completeness.
[1, 0, "Wire Pitch (lap)", "rpitch", -90,   90, _rPit,            0] call _mkSlider;
[1, 1, "Wire Yaw (lap)",   "ryaw",  -180,  180, _rYaw,            0] call _mkSlider;
[1, 2, "Wire Roll (lap)",  "rroll",  -90,   90, _rRol,            0] call _mkSlider;
// column 2: the wire-end reach, meaning how far the steering anchor sits out from the plug. larger gives more
// leverage.
[2, 0, "Wire reach (lap)", "stub",   0.02, 0.45, _stub,           3] call _mkSlider;
// column 3: the patient attach and the rope.
[3, 0, "Dummy Y (chest)",  "dy",    -0.5,  0.6, (_dOff select 1), 3] call _mkSlider;
[3, 1, "Dummy Z (height)", "dz",    -0.3,  0.5, (_dOff select 2), 3] call _mkSlider;
[3, 2, "Rope slack",       "slack",    0,  1.5, _slack,           3] call _mkSlider;
[3, 3, "Rope segments",    "seg",      0,   63, _seg,             0] call _mkSlider;

private _btn = _display ctrlCreate ["ACME_ThemeButton", -1];
_btn ctrlSetPosition [_mX + (_cw*2) + (_colGap*2), _top + (_rowH * 3) + 0.004, _cw, _rowH*0.46];
_btn ctrlSetText "DONE";
_btn ctrlSetBackgroundColor (["selected", 1] call ACME_fnc_a11yColor);
_btn ctrlSetTextColor [0.92,0.95,1,1];
_btn ctrlAddEventHandler ["ButtonClick", { closeDialog 0; }];
_btn ctrlCommit 0;
_ctrls pushBack _btn;

uiNamespace setVariable ["ACME_MC_CableTunerCtrls", _ctrls];
