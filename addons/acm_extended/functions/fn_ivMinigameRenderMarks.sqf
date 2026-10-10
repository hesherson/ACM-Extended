// render the persistent iv marks, meaning the placed hubs, removed sites and missed holes, stored on the patient
// that belong to the current limb and view. it deletes any previously-rendered mark sprites first. it is called
// on init and on flip, so the sites stay put when you re-open or flip the limb.
private _dlg = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (isNull _dlg) exitWith {};
if ((uiNamespace getVariable ["ACME_IV_PullIdx",-1])>=0) then {
    uiNamespace setVariable ["ACME_IV_PullIdx",-1];
    uiNamespace setVariable ["ACME_IV_PullLayers",[]];
    uiNamespace setVariable ["ACME_IV_PullLayerBases",[]];
    private _extra=uiNamespace getVariable ["ACME_IV_PullExtra",controlNull];
    if (!isNull _extra) then {ctrlDelete _extra;};
    uiNamespace setVariable ["ACME_IV_PullExtra",controlNull];
};
private _rect = uiNamespace getVariable ["ACME_IV_BodyRect", []];
if (_rect isEqualTo []) exitWith {};
_rect params ["_bx", "_by", "_bw", "_bh"];
private _af = uiNamespace getVariable ["ACME_IV_AspectFix", 0.5625];
private _patient = uiNamespace getVariable ["ACME_IV_Patient", objNull];
private _bp = uiNamespace getVariable ["ACME_IV_BodyPart", "leftarm"];
private _view = uiNamespace getVariable ["ACME_IV_View", ""];

{ if (!isNull _x) then { ctrlDelete _x; }; } forEach (uiNamespace getVariable ["ACME_IV_MarkCtrls", []]);
private _ctrls = [];

private _marks = if (isNull _patient) then { [] } else { _patient getVariable ["ACME_IV_Marks", []] };
private _anchors = uiNamespace getVariable ["ACME_IV_FrameAnchors", createHashMap];
private _fades = [];
private _hubCtrls = [];
private _finishCtrls = [];
private _trackKeys = createHashMap;
// First-seen timestamps survive repaint/rebuilds so a newly-created mark fades once instead of restarting every redraw.
private _visualFadeStarts = uiNamespace getVariable ["ACME_IV_VisualFadeStarts", createHashMap];
private _applyFirstSeenFade = {
    params ["_ctrl", "_key", "_seconds"];
    if (isNull _ctrl || {_seconds <= 0}) exitWith {};
    private _started = _visualFadeStarts getOrDefault [_key, -1];
    if (_started < 0) then {
        _started = CBA_missionTime;
        _visualFadeStarts set [_key, _started];
    };
    private _age = (CBA_missionTime - _started) max 0;
    if (_age < _seconds) then {
        private _left = (_seconds - _age) max 0.01;
        private _progress = (_age / _seconds) max 0 min 1;
        _ctrl ctrlSetFade (1 - _progress);
        _ctrl ctrlCommit 0;
        _ctrl ctrlSetFade 0;
        _ctrl ctrlCommit _left;
    } else {
        _ctrl ctrlSetFade 0;
        _ctrl ctrlCommit 0;
    };
};

// Scatter ACE contusions across the visible limb.  The layout is cached for the patient/view so a repaint,
// another medic's mark update or a flip back to this side does not make the bruises jump around.
if (!isNull _patient && {_bp in ["leftarm", "rightarm", "leftleg", "rightleg"]}) then {
    private _trauma = [_patient, _bp] call ACME_fnc_visualBruiseState;
    _trauma params ["_bruiseScore", "", "_bruiseSeverity"];
    if (_bruiseScore > 0) then {
        private _countBruises = ((ceil (_bruiseScore / 4)) max 1) min 4;
        private _layouts = uiNamespace getVariable ["ACME_IV_TraumaLayouts", createHashMap];
        private _layoutKey = format ["%1|%2|%3", netId _patient, _bp, _view];
        private _sig = format ["%1:%2", round (_bruiseScore * 10), _countBruises];
        private _cached = _layouts getOrDefault [_layoutKey, []];
        private _points = if ((_cached param [0, ""]) == _sig) then {+(_cached param [1, []])} else {[]};
        if ((count _points) != _countBruises) then {
            _points = [];
            private _eligible = [];
            {
                private _sd = [_bp, _x] call ACME_fnc_ivSiteData;
                if !(_sd isEqualTo []) then {
                    _sd params ["_sdView", "", "", "", "_vu", "_vv", "", "", ["_el", -1], ["_er", -1]];
                    if (_sdView == _view) then {_eligible pushBack [_vu, _vv, _el, _er];};
                };
            } forEach ["lower", "middle", "upper"];
            if !(_eligible isEqualTo []) then {
                for "_i" from 0 to (_countBruises - 1) do {
                    private _a = _eligible select (_i mod (count _eligible));
                    _a params ["_vu", "_vv", "_el", "_er"];
                    private _u = _vu;
                    if (_el >= 0 && {_er > _el}) then {
                        private _innerL = _el + ((_er - _el) * 0.18);
                        private _innerR = _er - ((_er - _el) * 0.18);
                        _u = _innerL + random ((_innerR - _innerL) max 0.001);
                    } else {
                        _u = _vu + (random 0.06) - 0.03;
                    };
                    private _spreadV = if (_bp in ["leftleg", "rightleg"]) then {0.12} else {0.09};
                    private _v = (_vv + (random _spreadV) - (_spreadV * 0.5)) max 0.08 min 0.92;
                    private _sev = ((_bruiseSeverity + floor (random 3) - 1) max 1) min 10;
                    private _scale = (if (_bp in ["leftleg", "rightleg"]) then {0.18} else {0.16}) * (0.86 + random 0.28);
                    _points pushBack [_u, _v, _sev, _scale];
                };
            };
            _layouts set [_layoutKey, [_sig, _points]];
            uiNamespace setVariable ["ACME_IV_TraumaLayouts", _layouts];
        };
        {
            _x params ["_u", "_v", "_sev", "_scale"];
            private _tag = if (_sev < 10) then {format ["0%1", _sev]} else {"10"};
            private _c = _dlg ctrlCreate ["ACME_IV_Bruise", -1];
            private _family = if (_bp in ["leftleg", "rightleg"]) then {"leg"} else {"arm"};
            _c ctrlSetText format ["\acm_extended\ui\bruises\%1_bruises_sev%2_ca.paa", _family, _tag];
            private _w = _bw * _scale; private _h = _bh * _scale;
            _c ctrlSetPosition [_bx + (_bw * _u) - (_w * 0.5), _by + (_bh * _v) - (_h * 0.5), _w, _h];
            _c ctrlSetTextColor [1,1,1,0.68];
            _c ctrlCommit 0; _c ctrlShow true;
            [_c, format ["trauma|%1|%2|%3|%4|%5", netId _patient, _bp, _view, _sig, _forEachIndex], missionNamespace getVariable ["ACME_iv_newBruiseFadeInSec", 2.5]] call _applyFirstSeenFade;
            _ctrls pushBack _c;
        } forEach _points;
    };
};

{
    _x params ["_mbp", "_mview", "_mu", "_mv", "_mkind", ["_mtex", ""], ["_mframe", ""], ["_mgauge", 0], ["_mmiss", -1], ["_mscale", 1]];
    if (_mbp == _bp && {_mview == _view}) then {
        // A persistent venous track mark sits below the current hub/bruise/hole.  Repeated attempts at the
        // same tier intensify it, while the authored +/-15-degree families follow the catheter approach.
        if (_bp in ["leftarm", "rightarm", "leftleg", "rightleg"] && {_mgauge > 0} && {_mkind in ["removed", "miss"]}) then {
            private _mSite = toLower (_x param [10, ""]);
            private _trackKey = format ["%1:%2:%3", _mSite, round (_mu * 1000), round (_mv * 1000)];
            if !(_trackKey in _trackKeys) then {
                _trackKeys set [_trackKey, true];
                private _sameTier = {_x param [0, ""] == _bp && {_x param [1, ""] == _view} && {toLower (_x param [10, ""]) == _mSite}} count _marks;
                private _gaugeBonus = switch (_mgauge) do {case 14: {2}; case 16: {1}; default {0};};
                private _sev = (2 + ((_sameTier - 1) max 0) * 2 + _gaugeBonus) max 1 min 10;
                private _ori = "0deg_vertical";
                private _hubAngle = _x param [13, 0];
                if (_mframe find "_15_left" >= 0 || {_hubAngle > 3}) then {_ori = "pos15deg_offset";};
                if (_mframe find "_15_right" >= 0 || {_hubAngle < -3}) then {_ori = "neg15deg_offset";};
                if (_mframe == "" && {abs _hubAngle <= 3}) then {
                    private _bucket = floor ((((_x param [11, 0]) max 0) mod 360) / 120);
                    _ori = ["neg15deg_offset", "0deg_vertical", "pos15deg_offset"] param [_bucket, "0deg_vertical"];
                };
                private _tag = if (_sev < 10) then {format ["0%1", _sev]} else {"10"};
                private _tc = _dlg ctrlCreate ["ACME_IV_Bruise", -1];
                _tc ctrlSetText format ["\acm_extended\ui\bruises\iv_venous_track_marks_%1_sev%2_ca.paa", _ori, _tag];
                private _ts = if (_bp in ["leftleg", "rightleg"]) then {0.20} else {0.17};
                private _tw = _bw * _ts; private _th = _bh * _ts;
                _tc ctrlSetPosition [_bx + (_bw * _mu) - (_tw * 0.5), _by + (_bh * _mv) - (_th * 0.5), _tw, _th];
                _tc ctrlSetTextColor [1,1,1,0.72];
                _tc ctrlCommit 0; _tc ctrlShow true;
                [_tc, format ["track|%1|%2|%3|%4|%5", netId _patient, _bp, _view, _trackKey, _sev], missionNamespace getVariable ["ACME_iv_newBruiseFadeInSec", 2.5]] call _applyFirstSeenFade;
                _ctrls pushBack _tc;
            };
        };
        if (_mkind == "hub") then {
            private _uid=_x param [14,""];
            private _lock=controlNull;private _accessory=controlNull;
            if (_uid!="") then {
                _lock=_dlg ctrlCreate ["ACME_IV_HubMark",-1];
                _accessory=_dlg ctrlCreate ["ACME_IV_HubMark",-1];
                {_x ctrlEnable false;_x ctrlShow false;} forEach [_lock,_accessory];
                _ctrls append [_lock,_accessory];
            };
            private _c = _dlg ctrlCreate ["ACME_IV_HubMark", -1];
            // every iv, the ej included, builds its hub path from the frame now. the _mtex branch only fires for any legacy
            // iv_ej marker still stored on a patient from an older build, whose anchor sits higher.
            // the seated hub is frame 14 of the supercath set, being the catheter with the needle gone. a mark saved by
            // an older build has gauge 0, so it draws in 16g.
            private _mg = if (_mgauge in [14, 16, 18, 20]) then { _mgauge } else { 16 };
            if (_mtex != "") then { _c ctrlSetText _mtex; } else { _c ctrlSetText ([_mg, _mframe, 14] call ACME_fnc_ivCathTex); };
            // the hub frame shares the insertion plane with every other frame, so it uses the one anchor.
            private _anc = _anchors getOrDefault [_mframe, [0.49166, 0.44434]];
            if (_mtex find "iv_ej_left" >= 0) then { _anc = [0.516, 0.176]; };
            if (_mtex find "iv_ej_right" >= 0) then { _anc = [0.484, 0.176]; };
            _anc params ["_tipFx", "_tipFy"];
            // the hub and the line draw at the same scale as the catheter that placed them, or the seated art would not
            // match the one the medic just pushed in. a legacy body-diagram marker keeps its own full size.
            private _hs = uiNamespace getVariable ["ACME_IV_CathScale", 0.62];
            if (_mtex find "iv_ej_left" >= 0 || {_mtex find "iv_ej_right" >= 0}) then { _hs = 1; };
            // keep the hub on the exact same frame anchor as the base and inserted catheter art. the texture set is authored to
            // transition in place, so do not apply additional per-stage offsets here.
            [_c, _bx + _bw * _mu, _by + _bh * _mv, _mframe, _x param [13,0], _hs, _anc] call ACME_fnc_ivCathPose;
            _c ctrlShow true;
            _ctrls pushBack _c;
            // a hub keeps its own index, paired with the mark it belongs to.
            // ACME_IV_MarkCtrls is a flat list with more than one control per mark and only for the marks on this
            // view, so indexing it by mark number gives the wrong control. the pull needs the exact sprite for the
            // hub it took hold of, which is what this pairing provides.
            _hubCtrls pushBack [_forEachIndex, _c];
            if (_uid!="") then {
                private _baseFilm=_dlg ctrlCreate ["ACME_IV_HubMark",-1];
                private _secondary=_dlg ctrlCreate ["ACME_IV_HubMark",-1];
                private _film=_dlg ctrlCreate ["ACME_IV_HubMark",-1];
                {_x ctrlEnable false;_x ctrlShow false;} forEach [_baseFilm,_secondary,_film];
                _ctrls append [_baseFilm,_secondary,_film];
                _finishCtrls pushBack [_uid,_accessory,_film,_lock,_secondary,_baseFilm];
            };
        } else {
            // the miss-site bruise first, under the hole, gauge-correlated, scaled to fit and faded in.
            if (_mkind == "miss" && {_mgauge > 0}) then {
                private _b = _dlg ctrlCreate ["ACME_IV_Bruise", -1];
                // THE BRUISE ART EXISTS FOR 14g, 16g AND 18g ONLY. there is no bruise_20g_ca.paa in the tree,
                // and a texture path to a file that is not packed reports Picture not found rather than falling
                // back to anything. a 20g therefore borrows the 18g bruise, which is the nearest bore. drop
                // ui/iv/bruise_20g_ca.paa in and delete the remap line.
                private _bruiseG = _mgauge;
                if (_bruiseG == 20) then { _bruiseG = 18; };
                _b ctrlSetText (if (_mbp == "ej") then {"\acm_extended\ui\iv\bruise_ej_ca.paa"} else {format ["\acm_extended\ui\iv\bruise_%1g_ca.paa", _bruiseG]});
                private _brW = _mscale * _bw; private _brH = _mscale * _bh;
                // MEASURED, not typed. the painted bruise sits in the middle of a mostly empty canvas, and this is
                // where its content actually is. decoded from the 128x128 uncompressed mipmap of each file and
                // read at texel accuracy, the center is 0.500 by 0.500 in every one of the five bruise textures.
                // it was 0.492 on the v axis, which put every bruise a little high of the needle. small, and it is
                // the same class of error as the hand-typed body map table.
                // note for anyone changing the art: the content is only about 6.5 percent of the canvas at alpha
                // above 8, so the control has to be roughly fifteen times the intended bruise size for the mark to
                // read correctly, and any anchor error is magnified by the same factor.
                private _aX = 0.500; private _aY = 0.500;
                _b ctrlSetPosition [_bx + (_bw * _mu) - (_brW * _aX), _by + (_bh * _mv) - (_brH * _aY), _brW, _brH];
                // a bruise never reaches full opacity. at alpha 1 the painted mark reads as a solid blob stuck on
                // the skin rather than something under it, and it buries the puncture hole drawn on top of it.
                private _cap = (missionNamespace getVariable ["ACME_iv_bruiseMaxAlpha", 0.90]);
                if (!(_cap isEqualType 0) || {!finite _cap}) then { _cap = 0.90 };
                _cap = (_cap max 0.05) min 1;
                // A BRUISE HAS A LIFE OF ABOUT TWENTY MINUTES.
                // it darkens over the configured fade-in as blood tracks into the tissue, holds at the cap, then fades
                // out over the last stretch as it resolves. a puncture HOLE has no life and stays for the body.
                // Bruise creation uses shared serverTime, so every observer sees the same age regardless of client uptime.
                private _al = _cap;
                if (_mmiss >= 0) then {
                    private _e = serverTime - _mmiss;
                    private _life = missionNamespace getVariable ["ACME_iv_bruiseLifeSec", 1200];
                    private _out  = missionNamespace getVariable ["ACME_iv_bruiseFadeOutSec", 300];
                    private _fadeIn = (missionNamespace getVariable ["ACME_iv_bruiseFadeInSec", 5.0]) max 0.1;
                    _al = switch (true) do {
                        case (_e < 0):                { 0 };     // shared-clock skew: fresh means not visible yet, never full opacity.
                        case (_e < _fadeIn):          { (_e / _fadeIn) * _cap };
                        case (_e < (_life - _out)):   { _cap };
                        case (_e < _life):            { _cap * (((_life - _e) / (_out max 1)) max 0) };
                        default                       { 0 };
                    };
                };
                _b ctrlSetTextColor [1, 1, 1, _al];
                _b ctrlCommit 0;
                // the same both-ways test the per frame driver in fn_ivMinigameTick uses, and it has to be the
                // same or the two disagree the moment one of them runs.
                // it was a hide placed ABOVE an unconditional show, so it did nothing at all here and the resolved
                // bruise of a casualty who had been carrying one for twenty minutes reappeared on every rebuild.
                _b ctrlShow (_al > 0.004);
                _ctrls pushBack _b;
                _fades pushBack [_b, _mmiss];
            };
            // the puncture hole on top, but only where something actually came back out.
            // a seated hub leaves no hole, because the catheter is still sitting in it. the mark carries a hole
            // texture only for a pulled line. without this guard the control fell back to its config default,
            // hole1, and stamped a puncture beside every infiltration bruise.
            if (_mtex != "") then {
                private _c = _dlg ctrlCreate ["ACME_IV_Hole", -1];
                _c ctrlSetText _mtex;
                // the hole is the size of the bore that made it.
                // it used to be one size for every gauge, so a 14g and an 18g left an identical dot. they do not. the
                // outer diameters are 2.11 mm for 14g, 1.65 for 16g, 1.27 for 18g and 0.91 for 20g, so a 14g is a bit
                // over two and a half times the width of a 20g and it is plainly visible when it comes out.
                // the multiplier is the true diameter ratio against 18g, so the marks are in proportion to each other
                // rather than to a guess, and the base is a little larger than before because the old dot was too
                // small to read at all on the arm views.
                private _bore = switch (_mgauge) do {
                    case 14: { 1.66 };
                    case 16: { 1.30 };
                    case 18: { 1.00 };
                    case 20: { 0.72 };
                    default { 1.00 };
                };
                private _holeFrac = (if (_mbp in ["leftleg", "rightleg"]) then { 0.0090 } else { 0.0045 }) * _bore;
                private _r = _bh * _holeFrac;  // a very small puncture mark, at 2x on the legs.
                _c ctrlSetPosition [_bx + (_bw * _mu) - (_r / 2), _by + (_bh * _mv) - (_r / 2) / _af, _r, _r / _af];
                _c ctrlCommit 0;
                _c ctrlShow true;
                _ctrls pushBack _c;
            };
        };
    };
} forEach _marks;

// Site-specific infiltration/extravasation overlay.  Worsening severity crossfades over ten seconds; recovery
// can step down immediately so the picture always reflects the current injury state.
private _exFades = [];
private _exState = uiNamespace getVariable ["ACME_IV_ExtravasationVisualState", createHashMap];
{
    _x params ["_siteIdx", "_sev"];
    private _siteName = ["upper", "middle", "lower"] param [_siteIdx, "middle"];
    private _candidates = _marks select {
        (_x param [0, ""]) == _bp && {(_x param [1, ""]) == _view} && {toLower (_x param [10, ""]) == _siteName}
            && {(_x param [4, ""]) in ["hub", "miss", "removed"]}
    };
    if !(_candidates isEqualTo []) then {
        private _mark = _candidates select ((count _candidates) - 1);
        private _u = _mark param [2, 0.5]; private _v = _mark param [3, 0.5];
        private _key = format ["%1#%2#%3", netId _patient, _bp, _siteIdx];
        private _prior = _exState getOrDefault [_key, [0, -1, -1]];
        _prior params ["_current", "_old", "_started"];
        if (_sev != _current) then {
            if (_current <= 0) then {
                // First appearance: fade the broad injury in rather than stamping it at full opacity.
                _old = 0; _started = CBA_missionTime;
            } else {
                if (_sev > _current) then {
                    _old = _current; _started = CBA_missionTime;
                } else {
                    _old = -1; _started = -1;
                };
            };
            _current = _sev;
            _prior = [_current, _old, _started];
            _exState set [_key, _prior];
        };
        private _cap = 0.86;
        private _scale = if (_bp in ["leftleg", "rightleg"]) then {0.23} else {0.20};
        private _w = _bw * _scale; private _h = _bh * _scale;
        private _mkCtrl = {
            params ["_level", "_alpha"];
            private _tag = if (_level < 10) then {format ["0%1", _level]} else {"10"};
            private _ec = _dlg ctrlCreate ["ACME_IV_Bruise", -1];
            _ec ctrlSetText format ["\acm_extended\ui\bruises\iv_infiltration_extravasation_sev%1_ca.paa", _tag];
            _ec ctrlSetPosition [_bx + (_bw * _u) - (_w * 0.5), _by + (_bh * _v) - (_h * 0.5), _w, _h];
            _ec ctrlSetTextColor [1,1,1,_alpha];
            _ec ctrlCommit 0; _ec ctrlShow (_alpha > 0.003);
            _ctrls pushBack _ec;
            _ec
        };
        private _fadeInSec = (missionNamespace getVariable ["ACME_iv_extravasationFadeInSec", 4.0]) max 0.1;
        private _duration = if (_old == 0) then {_fadeInSec} else {10};
        private _age = if (_started >= 0) then {CBA_missionTime - _started} else {_duration};
        if (_old >= 0 && {_started >= 0} && {_age < _duration}) then {
            private _t = (_age / _duration) max 0 min 1;
            private _oc = controlNull;
            if (_old > 0) then {_oc = [_old, _cap * (1 - _t)] call _mkCtrl;};
            private _nc = [_current, _cap * _t] call _mkCtrl;
            _exFades pushBack [_oc, _nc, _started, _cap, _key, _current, _duration];
        } else {
            [_current, _cap] call _mkCtrl;
            if (_old >= 0) then {_exState set [_key, [_current, -1, -1]];};
        };
    };
} forEach ([_patient, _bp] call ACME_fnc_ivExtravasationState);
uiNamespace setVariable ["ACME_IV_ExtravasationVisualState", _exState];
uiNamespace setVariable ["ACME_IV_ExtravasationFades", _exFades];
uiNamespace setVariable ["ACME_IV_VisualFadeStarts", _visualFadeStarts];

{ [_x] call ACME_fnc_ivMinigameHookCtrl; } forEach _ctrls;
uiNamespace setVariable ["ACME_IV_MarkCtrls", _ctrls];
uiNamespace setVariable ["ACME_IV_HubCtrls", _hubCtrls];
uiNamespace setVariable ["ACME_IV_BruiseFades", _fades];

_dlg setVariable ["ACME_IV_FinishCtrls",_finishCtrls];
