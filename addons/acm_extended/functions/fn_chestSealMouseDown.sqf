if ([_this,"down"] call ACME_fnc_minigameInputMouse) exitWith {true};
params ["_display", "_button"];
disableSerialization;

// the hands are on the mouse buttons now. holding lmb is the four-finger rake, which sweeps for occult wounds, and
// holding RMB is the single-finger feeler, which walks the ribs for the 5th ics. that removes the mode-toggle
// button entirely: the hand you are using is the button you are holding, which is one less thing to click
// mid-procedure.
// RMB no longer closes the dialog, because it is a hand now. use the close button or esc.
private _heldSealNow  = uiNamespace getVariable ["ACME_CS_Held", false];
private _heldSpearNow = uiNamespace getVariable ["ACME_CS_SpearHeld", false];

if (_button == 1) exitWith {
    // the right button is the feeler. it is only when bare-handed, and with a seal or a spear in hand it does
    // nothing, so a stray right-click can never fling the item somewhere or drop you out of the minigame.
    if (!_heldSealNow && {!_heldSpearNow}) then {
        uiNamespace setVariable ["ACME_CS_RMB", true];
        // The original right-button exit never enabled the common drag/render path.
        uiNamespace setVariable ["ACME_CS_Dragging", true];
        uiNamespace setVariable ["ACME_CS_DragPt", [[], false] call ACME_fnc_chestSealMouseCoords];
        uiNamespace setVariable ["ACME_CS_DragLast", -1];
    };
    false
};
if (_button != 0) exitWith {false};

// the left button, bare-handed, is the rake. with something in hand, lmb still places it, which is handled
// below.
if (!_heldSealNow && {!_heldSpearNow}) then {
    uiNamespace setVariable ["ACME_CS_LMB", true];
    uiNamespace setVariable ["ACME_CS_FingerMode", 4];
};

private _isFiniteNumber = {
    params ["_value"];
    ((typeName _value) isEqualTo "SCALAR") && {finite _value}
};

private _bodyRect = uiNamespace getVariable ["ACME_CS_BodyRect", [0,0,0,0]];
if !(_bodyRect isEqualType [] && {count _bodyRect >= 4}) exitWith {false};
_bodyRect params ["_bx", "_by", "_bw", "_bh"];
if !(([_bx] call _isFiniteNumber) && {[_by] call _isFiniteNumber} && {[_bw] call _isFiniteNumber} && {[_bh] call _isFiniteNumber} && {_bw > 0} && {_bh > 0}) exitWith {false};

private _mouse = [_bodyRect, true] call ACME_fnc_chestSealMouseCoords;
if !(_mouse isEqualType [] && {count _mouse >= 2}) exitWith {false};
_mouse params ["_mx", "_my"];
if !(([_mx] call _isFiniteNumber) && {[_my] call _isFiniteNumber}) exitWith {false};

private _insideRect = {
    params ["_pointX", "_pointY", "_rect"];
    if !(_rect isEqualType [] && {count _rect >= 4}) exitWith {false};
    _rect params ["_rx", "_ry", "_rw", "_rh"];
    if !(([_rx] call _isFiniteNumber) && {[_ry] call _isFiniteNumber} && {[_rw] call _isFiniteNumber} && {[_rh] call _isFiniteNumber} && {_rw > 0} && {_rh > 0}) exitWith {false};
    _pointX >= _rx && {_pointX <= _rx + _rw} && {_pointY >= _ry} && {_pointY <= _ry + _rh}
};

private _overSealSlot = [_mx, _my, uiNamespace getVariable ["ACME_CS_SlotRect", []]] call _insideRect;
private _overSpearSlot = [_mx, _my, uiNamespace getVariable ["ACME_CS_SpearSlotRect", []]] call _insideRect;
if (_overSealSlot || {_overSpearSlot}) exitWith {false};

private _side = uiNamespace getVariable ["ACME_CS_Side", "front"];
private _af = uiNamespace getVariable ["ACME_CS_AspectFix", 0.5625];
if !(([_af] call _isFiniteNumber) && {_af > 0.05} && {_af < 4}) then {_af = 0.5625;};
private _onBody = _mx >= _bx && {_mx <= _bx + _bw} && {_my >= _by} && {_my <= _by + _bh};

private _heldSpear = uiNamespace getVariable ["ACME_CS_SpearHeld", false];
if (_heldSpear) exitWith {
    if (_side != "front") exitWith {
        ["NCD placement is anterior. Flip the patient to the front.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
        false
    };
    if (!_onBody) exitWith {false};

    private _patientSide = if (_mx >= (_bx + _bw / 2)) then {"left"} else {"right"};
    private _target = if (_patientSide == "left") then {
        uiNamespace getVariable ["ACME_CS_NCDTargetLeft", [0.57421875, 0.29296875]]
    } else {
        uiNamespace getVariable ["ACME_CS_NCDTargetRight", [0.4140625, 0.29296875]]
    };
    _target params ["_tx", "_ty"];
    private _targetX = _bx + (_bw * _tx);
    private _targetY = _by + (_bh * _ty);
    private _dx = (_mx - _targetX) / _af;
    private _dy = _my - _targetY;
    private _dist = 1e9;
    if (([_dx] call _isFiniteNumber) && {[_dy] call _isFiniteNumber}) then {
        private _distSq = (_dx * _dx + _dy * _dy) max 0;
        if ([_distSq] call _isFiniteNumber) then {_dist = sqrt _distSq;};
    };
    private _placeR = uiNamespace getVariable ["ACME_CS_NCDPlaceR", _bh * 0.018];
    if !(([_placeR] call _isFiniteNumber) && {_placeR > 0}) then {_placeR = _bh * 0.018;};
    // a valid placement is inside the 5th-ics ellipse zone of this side, at a normalized distance of 1 or less, so the
    // NAR SPEAR lands anywhere along the acceptable intercostal space rather than at just one point. _dist, to the
    // authored point, is still used below for the iatrogenic-miss band.
    private _ell = if (_patientSide == "left")
        then { uiNamespace getVariable ["ACME_CS_NCDEllipseLeft",  [0.555, 0.293, 0.050, 0.015]] }
        else { uiNamespace getVariable ["ACME_CS_NCDEllipseRight", [0.445, 0.293, 0.050, 0.015]] };
    _ell params ["_ecu", "_ecv", "_eru", "_erv"];
    private _u = (_mx - _bx) / _bw;
    private _v = (_my - _by) / _bh;
    private _nd = 1e9;
    if (_eru > 0 && {_erv > 0} && {[_u] call _isFiniteNumber} && {[_v] call _isFiniteNumber}) then {
        private _ndu = (_u - _ecu) / _eru;
        private _ndv = (_v - _ecv) / _erv;
        private _ndsq = ((_ndu * _ndu) + (_ndv * _ndv)) max 0;
        if ([_ndsq] call _isFiniteNumber) then { _nd = sqrt _ndsq; };
    };
    if !(([_nd] call _isFiniteNumber) && {_nd <= 1}) exitWith {
        private _missR = _bh * 0.13;  // the plausible-insertion band around the 5th ics.
        if (([_dist] call _isFiniteNumber) && {_dist <= _missR}) then {
            // a missed insertion inside the chest: the needle entered off the intercostal space. waste the spear, open a small
            // iatrogenic chest wound, reusing the hole system, and seed a developing pneumothorax. the medic can seal the
            // wound, try the other side, or, if it tensions, cut.
            private _medic = uiNamespace getVariable ["ACME_CS_Medic", objNull];
            private _patient = uiNamespace getVariable ["ACME_CS_Patient", objNull];


            private _queued = false;
            private _hx = (_mx - _bx) / _bw;
            private _hy = (_my - _by) / _bh;
            if (([_hx] call _isFiniteNumber) && {[_hy] call _isFiniteNumber} && {!isNull _patient}) then {
                (missionNamespace getVariable ["ACME_CS_holeField", [0.5, 0.285, 0.07, 0.05]]) params ["_fieldX", "_fieldY", "_fieldRX", "_fieldRY"];
                if (_fieldRX > 0 && {_fieldRY > 0}) then {
                    private _nx = (_hx - _fieldX) / _fieldRX;
                    private _ny = (_hy - _fieldY) / _fieldRY;
                    private _distance = sqrt (((_nx * _nx) + (_ny * _ny)) max 0);
                    if (_distance > 0.96) then {
                        private _scale = 0.96 / _distance;
                        _hx = _fieldX + ((_hx - _fieldX) * _scale);
                        _hy = _fieldY + ((_hy - _fieldY) * _scale);
                    };
                };
                _queued = ["miss", ["front", _hx, _hy], "ACME_NARSPEAR"] call ACME_fnc_chestSealRequest;
            };

            if (!_queued) exitWith {false};
            uiNamespace setVariable ["ACME_CS_SpearHeld", false];
            if (!isNull _medic) then {
                uiNamespace setVariable ["ACME_CS_SpearsLeft", [_medic, uiNamespace getVariable ["ACME_CS_Patient", objNull], "ACME_NARSPEAR"] call ACME_fnc_treatmentSupplyCount];
            };
            playSound "ACME_CS_HoleReveal";
            [] call ACME_fnc_chestSealRefreshSpearSlot;
            [] call ACME_fnc_chestSealRender;
            [] call ACME_fnc_chestSealPrompt;
            // there is no miss message. the revealed hole and the reveal sound are the feedback.
        } else {
            ["Locate the 5th intercostal space.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
        };
        false
    };

    [_patientSide] call ACME_fnc_chestSealApplyNCD;
    false
};

private _heldSeal = uiNamespace getVariable ["ACME_CS_Held", false];
if (_heldSeal) exitWith {
    if (!_onBody) exitWith {false};
    private _applyR = uiNamespace getVariable ["ACME_CS_ApplyR", (_bh * 0.062)];
    if !(([_applyR] call _isFiniteNumber) && {_applyR > 0}) then {_applyR = _bh * 0.062;};
    private _holes = uiNamespace getVariable ["ACME_CS_Holes", []];

    // Placement is keyed to the wound, not to the rendered seal footprint. Search open discovered holes FIRST.
    // Two wounds can be millimetres apart on screen and each remains independently sealable even if the seal
    // sprites overlap. Existing seals are manipulated only when no new seal is being held.
    private _best = -1;
    private _bestD = _applyR;
    {
        if (_x isEqualType [] && {count _x >= 5}) then {
            _x params ["_hSide", "_hx", "_hy", "_found", "_sealed"];
            if (_found && {!_sealed} && {_hSide == _side} && {[_hx] call _isFiniteNumber} && {[_hy] call _isFiniteNumber}) then {
                private _ddx = (_mx - (_bx + _bw * _hx)) / (_af max 0.05);
                private _ddy = _my - (_by + _bh * _hy);
                private _distSq = (_ddx * _ddx + _ddy * _ddy) max 0;
                if ([_distSq] call _isFiniteNumber) then {
                    private _d = sqrt _distSq;
                    if (([_d] call _isFiniteNumber) && {_d < _bestD}) then {_best = _forEachIndex; _bestD = _d;};
                };
            };
        };
    } forEach _holes;

    if (_best >= 0) then {
        [_best] call ACME_fnc_chestSealApply;
    } else {
        private _patient = uiNamespace getVariable ["ACME_CS_Patient", objNull];
        private _medic = uiNamespace getVariable ["ACME_CS_Medic", objNull];
        private _queued = false;
        private _wx = (_mx - _bx) / _bw;
        private _wy = (_my - _by) / _bh;
        if (([_wx] call _isFiniteNumber) && {[_wy] call _isFiniteNumber}) then {
            _queued = ["waste", [_side, _wx, _wy], "ACM_ChestSeal"] call ACME_fnc_chestSealRequest;
        };
        if (!_queued) exitWith {false};
        uiNamespace setVariable ["ACME_CS_Held", false];
        uiNamespace setVariable ["ACME_CS_SealsLeft", if (isNull _medic) then {0} else {[_medic, uiNamespace getVariable ["ACME_CS_Patient", objNull], "ACM_ChestSeal"] call ACME_fnc_treatmentSupplyCount}];
        ["Seal misplaced. center it directly over the found hole.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
        [] call ACME_fnc_chestSealRefreshSlot;
        [] call ACME_fnc_chestSealRender;
        [] call ACME_fnc_chestSealPrompt;
    };
    false
};

uiNamespace setVariable ["ACME_CS_Dragging", true];
uiNamespace setVariable ["ACME_CS_DragPt", [_mx, _my]];
uiNamespace setVariable ["ACME_CS_DragLast", -1];
false
