if ([_this,"down"] call ACME_fnc_minigameInputMouse) exitWith {true};
// Shared display/control click router for the IV minigame.
// Left click holds for palpation, wiping and insertion.
// Right click on the applied band removes it; elsewhere it retracts the needle.
// With an empty hand, clicking a placed hub starts a pull.
// Slot buttons separately grab or return their tool on a single click.
// holding the band on the limb applies it at the snapped site.
// A needle click starts the stick; holding advances it and release ends the hold.
params ["_display", "_button", ["_evtX", -1], ["_evtY", -1]];
if (_display isEqualType controlNull) then {_display = ctrlParent _display;};
if !([] call ACME_fnc_ivUiValid) exitWith {false};
if (isNull _display || {_display != (uiNamespace getVariable ["ACME_IV_DLG", displayNull])}) exitWith {false};

if (_display getVariable ["ACME_IV_FinishBusy",false]) exitWith {
    if (_display getVariable ["ACME_IV_FieldInserting",false]) exitWith {
        if (_button==0) then {uiNamespace setVariable ["ACME_IV_Dragging",true];};
        if (_button in [1,2]) then {[] call ACME_fnc_ivMinigameRetract;};
        true
    };
    if (_button in [1,2]) then {[] call ACME_fnc_ivFinishAbort;};
    if (_button==0) then {
        private _a=_display getVariable ["ACME_IV_FinishActive",[]];
        private _cursor=[] call ACME_fnc_ivMinigameCursor;
        if (count _a>=3 && {(((_a select 0) param [16,[]]) param [2,""])=="flush"}
            && {[_a select 0,_cursor] call ACME_fnc_ivFinishSyringeHit}) then {
            uiNamespace setVariable ["ACME_IV_Dragging",true];
            _display setVariable ["ACME_IV_FlushPullPin",_cursor];
        };
    };
    true
};
if (_button in [1, 2]) exitWith {
    // Controls, their display and the CBA middle-button fallback can see the same
    // press. Consume it once so a band removal cannot also retract the needle.
    private _press = [diag_frameNo, _button];
    if ((_display getVariable ["ACME_IV_SecondaryPress", []]) isEqualTo _press) exitWith {true};
    _display setVariable ["ACME_IV_SecondaryPress", _press];

    private _hitBand = false;
    if (_button == 1 && {uiNamespace getVariable ["ACME_IV_BandOn", false]}
        && {!(uiNamespace getVariable ["ACME_IV_EJMode", false])}) then {
        private _body = uiNamespace getVariable ["ACME_IV_BodyRect", []];
        private _cursor = call ACME_fnc_ivMinigameCursor;
        private _band = uiNamespace getVariable ["ACME_IV_BandUV", []];
        if (count _body >= 4 && {count _cursor == 2} && {count _band >= 2}) then {
            _body params ["_x", "_y", "_w", "_h"];
            private _aspect = uiNamespace getVariable ["ACME_IV_AspectFix", 0.5625];
            if (_w > 0 && {_h > 0} && {_aspect > 0}) then {
                private _du = (((_cursor select 0) - _x) / _w) - (_band select 0);
                private _dv = ((((_cursor select 1) - _y) / _h) - (_band select 1)) / _aspect;
                _hitBand = sqrt ((_du * _du) + (_dv * _dv)) <= 0.05;
            };
        };
    };
    if (_hitBand) exitWith {
        [] call ACME_fnc_ivMinigameRemoveBand;
        true
    };
    // The established right/middle needle safety inputs remain available away
    // from the band. Space is still the keyboard equivalent.
    [] call ACME_fnc_ivMinigameRetract;
    true
};
if (_button != 0) exitWith { false };
uiNamespace setVariable ["ACME_IV_Dragging", true];

// an insertion is already under way. the catheter is in the arm, so this click is the medic taking hold of it
// again to push further, and it must not start a second stick.
private _insStage = uiNamespace getVariable ["ACME_IV_InsStage", ""];
if (_insStage in ["advance", "thread", "retract"]) exitWith { false };

private _finite = { params ["_v"]; (_v isEqualType 0) && {finite _v} };
private _rect = uiNamespace getVariable ["ACME_IV_BodyRect", []];
if (_rect isEqualTo []) exitWith { false };
_rect params ["_bx", "_by", "_bw", "_bh"];
private _af = uiNamespace getVariable ["ACME_IV_AspectFix", 0.5625];

private _ui = call ACME_fnc_ivMinigameCursor;
if (_ui isEqualTo []) exitWith { false };
_ui params ["_ux", "_uy"];
if !(([_ux] call _finite) && {[_uy] call _finite}) exitWith { false };

private _held = uiNamespace getVariable ["ACME_IV_Held", "none"];
private _fieldTarget=if (_held=="needle") then {[_ux,_uy,"field"] call ACME_fnc_ivFinishTarget} else {[]};
if (_fieldTarget isNotEqualTo []) exitWith {
    private _close=[_ux,_uy,"field",false,true] call ACME_fnc_ivFinishTarget;
    if (_close isEqualTo []) exitWith {
        ["Move the needle closer to the saline-lock port.",2,uiNamespace getVariable ["ACME_IV_Medic",objNull]] call ace_common_fnc_displayTextStructured;
        true
    };
    _fieldTarget=_close;
    private _g=uiNamespace getVariable ["ACME_IV_Gauge",16];
    if (_g in [14,16]) then {
        [0,0,format ["field%1",_g],(_fieldTarget select 0) param [14,""]] call ACME_fnc_ivFinishStart;
    } else {["Use a 14g or 16g catheter for the saline lock.",2,uiNamespace getVariable ["ACME_IV_Medic",objNull]] call ace_common_fnc_displayTextStructured;};
    true
};

// for a held needle, trust the last rendered hover position, because that is what the player is actually seeing.
// the MouseButtonDown coords and getMousePosition can disagree by a frame or a control space, which caused the
// base, inserted and hub images to split apart after the click.
private _lastNeedle = uiNamespace getVariable ["ACME_IV_LastNeedleState", []];
if (_held == "needle" && {_lastNeedle isEqualType []} && {count _lastNeedle >= 7}) then {
    _lastNeedle params ["_lu", "_lv", "_lFrame", "_lX", "_lY", "_lW", "_lH", ["_lt", 0]];
    if ((diag_tickTime - _lt) < 0.20) then {
        _ux = _bx + (_bw * _lu);
        _uy = _by + (_bh * _lv);
        uiNamespace setVariable ["ACME_IV_NeedleFrame", _lFrame];
        uiNamespace setVariable ["ACME_IV_StickTopLeft", [_lX, _lY]];
    };
};

private _fx = (_ux - _bx) / _bw;
private _fy = (_uy - _by) / _bh;

private _onFinishTray=false;
{
    private _r=ctrlPosition (_x select 3);
    if (_ux>=(_r select 0) && {_ux<=(_r select 0)+(_r select 2)}
        && {_uy>=(_r select 1)} && {_uy<=(_r select 1)+(_r select 3)}) exitWith {_onFinishTray=true;};
} forEach (_display getVariable ["ACME_IV_FinishTray",[]]);
// Let the native button receive its click; do not also treat its coordinates as a hub.
if (_onFinishTray) exitWith {false};
if (_held in ["extension","flush","dressing","line","lock"]) exitWith {
    uiNamespace setVariable ["ACME_IV_Dragging",false];
    [_fx,_fy] call ACME_fnc_ivFinishStart;
    true
};
private _inRect = {
    params ["_px", "_py", "_r"];
    if !(_r isEqualType [] && {count _r >= 4}) exitWith { false };
    _r params ["_rx", "_ry", "_rw", "_rh"];
    (_px >= _rx) && {_px <= _rx + _rw} && {_py >= _ry} && {_py <= _ry + _rh}
};

// pull a placed iv out by taking hold of the hub.
// there is no remove button any more. take hold of the catheter and pull it, the same as you would on a body.
if (!(uiNamespace getVariable ["ACME_IV_EJMode", false]) || {true}) then {
    private _patient = uiNamespace getVariable ["ACME_IV_Patient", objNull];
    private _bp = uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"];
    private _view = uiNamespace getVariable ["ACME_IV_View", ""];
    private _held0 = uiNamespace getVariable ["ACME_IV_Held", "none"];
    if (!isNull _patient && {_held0 == "none"} && {(uiNamespace getVariable ["ACME_IV_InsStage", ""]) == ""}) then {
        private _marks = _patient getVariable ["ACME_IV_Marks", []];
        private _hit=[_ux,_uy,"",true] call ACME_fnc_ivFinishTarget;
        private _bestI=if (_hit isEqualTo []) then {-1} else {_marks findIf {(_x param [14,""])==((_hit select 0) param [14,""]) && {(_x param [4,""])=="hub"}}};
        private _bestD=if (_bestI<0) then {1e9} else {0};
        if (_bestI >= 0 && {_bestD <= (missionNamespace getVariable ["ACME_iv_pullGrabRadius", 0.05])}) exitWith {
            (_marks select _bestI) params ["", "", "", "", "", "", ["_pframe", ""]];
            uiNamespace setVariable ["ACME_IV_PullIdx", _bestI];
            private _row=_marks select _bestI;
            uiNamespace setVariable ["ACME_IV_PullUID",_row param [14,""]];
            uiNamespace setVariable ["ACME_IV_PullKind",_hit select 1];
            uiNamespace setVariable ["ACME_IV_PullSuffix", _pframe];
            uiNamespace setVariable ["ACME_IV_PullAngle", (_marks select _bestI) param [13,0]];
            uiNamespace setVariable ["ACME_IV_PullProg", 0];
            uiNamespace setVariable ["ACME_IV_PullBroke", false];
            uiNamespace setVariable ["ACME_IV_PullPin", getMousePosition];
            // the mark sprite for this hub becomes the thing being pulled, so the render leaves it alone.
            private _mc = controlNull;
            {
                if ((_x select 0) == _bestI) exitWith { _mc = _x select 1; };
            } forEach (uiNamespace getVariable ["ACME_IV_HubCtrls", []]);
            private _layers=[];private _bases=[];
            private _kind=_hit select 1;private _uid=_row param [14,""];
            {
                if ((_x select 0)==_uid) exitWith {
                    if (_kind=="removeDressing") then {_mc=_x select 2;_layers=[_mc];} else {
                        if (_kind in ["removeExtension","removeLine"]) then {_mc=_x select 1;};
                        _layers=if (_kind=="catheter") then {[_mc,_x select 1,_x select 2]} else {if (_kind=="removeExtension") then {[_x select 1,_x select 2]} else {[_mc]}};
                        // A line pull moves only its downstream tubing, not the extension baked into line_ca.
                        if (_kind=="removeLine") then {
                            (_x select 1) ctrlSetText "\acm_extended\ui\iv\finish\cursor_line_ca.paa";
                            private _base=_display ctrlCreate ["ACME_IV_HubMark",-1];
                            _base ctrlSetText "\acm_extended\ui\iv\finish\extension_ca.paa";
                            [_base,_row] call ACME_fnc_ivFinishPose;_base ctrlShow true;
                            uiNamespace setVariable ["ACME_IV_PullExtra",_base];
                        };
                    };
                };
            } forEach (_display getVariable ["ACME_IV_FinishCtrls",[]]);
            if ((_row param [15,[]]) param [4,false]) then {
                private _fieldPull=[_display,_row,_kind,_mc] call ACME_fnc_ivFieldPullLayers;
                _layers=_fieldPull select 0;_mc=_fieldPull select 1;
            };
            {_bases pushBack (ctrlPosition _x);} forEach _layers;
            uiNamespace setVariable ["ACME_IV_PullLayers",_layers];
            uiNamespace setVariable ["ACME_IV_PullLayerBases",_bases];
            uiNamespace setVariable ["ACME_IV_PullCtrl", _mc];
            if (!isNull _mc) then {
                (ctrlPosition _mc) params ["_p0x", "_p0y"];
                uiNamespace setVariable ["ACME_IV_PullBase", [_p0x, _p0y]];
            };
            false
        };
    };
};

// slot grabs are handled by the onButtonClick of each slot button, as a single click that toggles to return. we
// intentionally do not hit-test slots here, because doing so double-fired the grab, once down here and once on
// the click of the button on release, which is why an item only stuck if you dragged out of the box.

private _onBody = (_ux >= _bx) && {_ux <= _bx + _bw} && {_uy >= _by} && {_uy <= _by + _bh};

switch (_held) do {
    // apply the band at the snapped site.
    case "band": {
        if (!_onBody) exitWith {};
        private _snap = uiNamespace getVariable ["ACME_IV_SnapActive", []];
        if (_snap isEqualTo []) exitWith {};
        _snap params ["_sName", "_sbU", "_sbV", "_svU", "_svV", "_slbl", "_sBandTex"];
        uiNamespace setVariable ["ACME_IV_Site", _sName];
        uiNamespace setVariable ["ACME_IV_BandUV", [_sbU, _sbV]];
        uiNamespace setVariable ["ACME_IV_VeinUV", [_svU, _svV]];
// the candidate veins at this site. outside the antecubital fossa this is the single strip it always was.
uiNamespace setVariable ["ACME_IV_VeinSet",
    [(uiNamespace getVariable ["ACME_IV_Patient", objNull]),
     (uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"]),
     _sName, _svU, _svV] call ACME_fnc_ivVeinSet];
        uiNamespace setVariable ["ACME_IV_Label", _slbl];
        (_display displayCtrl 86504) ctrlSetText _slbl;
        uiNamespace setVariable ["ACME_IV_BandOn", true];
        uiNamespace setVariable ["ACME_IV_Held", "none"];
        uiNamespace setVariable ["ACME_IV_Cleaned", false];
        uiNamespace setVariable ["ACME_IV_BandTex", _sBandTex];
        private _bC = _display displayCtrl 86502;
        _bC ctrlSetText _sBandTex;
        _bC ctrlSetPosition [_bx, _by, _bw, _bh];
        _bC ctrlCommit 0;
        _bC ctrlShow true;
        (_display displayCtrl 86505) ctrlShow false;
        // seed the difficulty, at the default gauge, so the palpation feel reflects the patency.
        private _patient0  = uiNamespace getVariable ["ACME_IV_Patient", objNull];
        private _bodyPart0 = uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"];
        private _diff0 = [_patient0, _bodyPart0, 16, (uiNamespace getVariable ["ACME_IV_Site", 1])] call ACME_fnc_ivSiteDifficulty;
        _diff0 params ["_pat0", "_feel0", "_hit0", "_hot0"];
        uiNamespace setVariable ["ACME_IV_Patency", _pat0];
        uiNamespace setVariable ["ACME_IV_FeelRadius", _feel0];
        uiNamespace setVariable ["ACME_IV_HitRadius", _hit0];
        uiNamespace setVariable ["ACME_IV_MaxHot", _hot0];
        [] call ACME_fnc_ivMinigameRefreshBandSlot;
        [true] call ACME_fnc_ivMinigameBandFlag;  // a band on the limb stops a line running through it.
        [] call ACME_fnc_ivMinigameSaveState;
    };

    // holding a needle: the click is the stick. it only counts if it lands on the limb, and off the limb it does
    // nothing and the needle stays in hand. on the limb, a hit seats the catheter and a non-hit is a wasted miss.
    case "needle": {
        // Aim from the settled needle tip, not the pointer. The tip can lag/tremble far enough to cross the
        // silhouette edge, so artwork validity is tested AFTER this substitution.
        private _tipUV = uiNamespace getVariable ["ACME_IV_NeedleTipUV", []];
        if (_tipUV isEqualType [] && {count _tipUV >= 3} && {(diag_tickTime - (_tipUV select 2)) < 0.25}) then {
            _fx = _tipUV select 0;
            _fy = _tipUV select 1;
        };

        private _bpStick = uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"];
        private _viewStick = uiNamespace getVariable ["ACME_IV_View", ""];
        private _bounds = [_bpStick, _viewStick, _fy] call ACME_fnc_ivLimbBounds;
        private _onArt = count _bounds == 2
            && {_fx >= (_bounds select 0)}
            && {_fx <= (_bounds select 1)};
        // Transparent canvas is not patient skin. Clicking there consumes nothing, starts no catheter and leaves
        // no bruise. The needle simply stays in the provider's hand.
        if (!_onArt) exitWith {};

        private _isEJc = uiNamespace getVariable ["ACME_IV_EJMode", false];
        private _stickSite = "";
        if (!_isEJc) then {
            _stickSite = [_fx, _fy, _viewStick, uiNamespace getVariable ["ACME_IV_SiteList", []], _bpStick]
                call ACME_fnc_ivSiteAtPoint;
            if !(_stickSite in ["upper", "middle", "lower"]) exitWith {};

            // The puncture site, not the BOA site, supplies the veins and the pressure/band difficulty. This is
            // what lets a middle/AC band coexist with a real distal wrist stick on the same front artwork.
            private _sdStick = [_bpStick, _stickSite] call ACME_fnc_ivSiteData;
            if (count _sdStick < 6 || {(_sdStick select 0) != _viewStick}) exitWith {};
            private _sU = _sdStick select 4;
            private _sV = _sdStick select 5;
            uiNamespace setVariable ["ACME_IV_ProbeSite", _stickSite];
            uiNamespace setVariable ["ACME_IV_VeinUV", [_sU, _sV]];
            uiNamespace setVariable ["ACME_IV_VeinSet",
                [uiNamespace getVariable ["ACME_IV_Patient", objNull], _bpStick, _stickSite, _sU, _sV]
                    call ACME_fnc_ivVeinSet];
        } else {
            // Resolve the anatomical EJ side from the actual steel tip at the click, not from the previous frame's
            // cursor. Screen-right is patient-left.
            private _vL = uiNamespace getVariable ["ACME_IV_EJVeinL", [0.560, 0.505]];
            private _vR = uiNamespace getVariable ["ACME_IV_EJVeinR", [0.440, 0.505]];
            private _dL = (abs (_fx - (_vL select 0))) + (abs (_fy - (_vL select 1)));
            private _dR = (abs (_fx - (_vR select 0))) + (abs (_fy - (_vR select 1)));
            private _nearL = _dL <= _dR;
            uiNamespace setVariable ["ACME_IV_VeinUV", ([_vR, _vL] select _nearL)];
            uiNamespace setVariable ["ACME_IV_EJAnatomicalSide", (["right", "left"] select _nearL)];
            uiNamespace setVariable ["ACME_IV_EJSide", (["right", "left"] select _nearL)];
        };

        private _patientStick = uiNamespace getVariable ["ACME_IV_Patient", objNull];
        private _gaugeStick = uiNamespace getVariable ["ACME_IV_Gauge", 16];
        private _diffSite = if (_isEJc) then {uiNamespace getVariable ["ACME_IV_EJAnatomicalSide", "left"]} else {_stickSite};
        private _punctureDifficulty = [_patientStick, _bpStick, _gaugeStick, _diffSite] call ACME_fnc_ivSiteDifficulty;
        _punctureDifficulty params ["_patStick", "_feelStick", "_hit", "_hotStick"];
        uiNamespace setVariable ["ACME_IV_Patency", _patStick];
        uiNamespace setVariable ["ACME_IV_FeelRadius", _feelStick];
        uiNamespace setVariable ["ACME_IV_HitRadius", _hit];
        uiNamespace setVariable ["ACME_IV_MaxHot", _hotStick];

        private _distV = 1e9;
        if (_isEJc) then {
            _distV = [_fx, _fy] call ACME_fnc_ivVeinDist;
        } else {
            private _nearStick = [_fx, _fy] call ACME_fnc_ivVeinNearest;
            _nearStick params ["_nearDist", "_nearU", "_nearV", "_nearQ", "_nearName"];
            _distV = _nearDist;
            if (_nearDist < 1e8) then {
                uiNamespace setVariable ["ACME_IV_VeinUV", [_nearU, _nearV]];
                uiNamespace setVariable ["ACME_IV_NearVein", _nearName];
                uiNamespace setVariable ["ACME_IV_NearQuality", _nearQ];
            };
        };

        if (_distV > _hit) then {
            // A real skin puncture that misses the vessel still advances and can infiltrate. This is one of the
            // explicit situations allowed to create bruising.
            uiNamespace setVariable ["ACME_IV_StickAcc", 1];
            [_fx, _fy, false, _stickSite] call ACME_fnc_ivMinigameInsertStart;
        } else {
            uiNamespace setVariable ["ACME_IV_StickAcc", (if (_hit > 0) then {(_distV / _hit) min 1} else {0})];
            private _stickU = _fx;
            private _stickV = _fy;
            private _blocked = false;
            private _reason = "";
            if (!isNull _patientStick) then {
                {
                    _x params ["_mbp", "_mview", "_mu", "_mv", "_mkind", ["_mtex", ""], ["_mframe", ""], ["_mgauge", 0], ["_mmiss", -1], ["_mscale", 1], ["_msite", ""]];
                    if (_mbp == _bpStick && {_mview == _viewStick}) then {
                        private _du = _stickU - _mu;
                        private _dv = (_stickV - _mv) * (1 / _af);
                        if (sqrt ((_du * _du) + (_dv * _dv)) <= 0.03) then {_blocked = true; _reason = "used";};
                        private _sameDrainageTrack = (!_isEJc)
                            || {(toLowerANSI _msite) == (toLowerANSI (uiNamespace getVariable ["ACME_IV_EJAnatomicalSide", ""]))};
                        if (_sameDrainageTrack && {_mkind == "removed"} && {_stickV >= _mv - 0.012}) then {
                            _blocked = true;
                            _reason = "above";
                        };
                    };
                } forEach (_patientStick getVariable ["ACME_IV_Marks", []]);
            };
            if (_blocked) then {
                (_display displayCtrl 86503) ctrlSetText (if (_reason == "above") then {""} else {"That site is already used."});
            } else {
                // The exact U/V are retained by InsertStart -> StickSuccess -> AddMark. The coarse ACM access-site
                // index is only the physiological slot; the minigame hub always returns to this exact puncture.
                [_stickU, _stickV, true, _stickSite] call ACME_fnc_ivMinigameInsertStart;
            };
        };
    };

    // holding the tubing: click the seated hub to connect it.
    case "line": {
        if (!_onBody) exitWith {};
        [_fx, _fy] call ACME_fnc_ivMinigameLineConnect;
    };

    // Empty hand and pad holds continue into palpation/wiping in the tick.
    default {};
};
false
