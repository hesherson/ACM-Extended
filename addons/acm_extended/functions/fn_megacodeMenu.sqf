#include "\x\acm\addons\main\ui_theme.hpp"
/*
 * Build one page of the Megacode instructor panel into the page area that ACME_fnc_megacodePanelLoad laid out.
 * [_idd, _page]; _page is vitals, rhythm, airway, wounds, neuro, scenario or log.
 * Every page is grouped under muted section labels; the current state is shown as a selected (light) button, and
 * what destroys or stops something is drawn in the danger colour. Sizes are shares of the panel height.
 */
params ["_idd","_page"];
private _disp = uiNamespace getVariable ["ACME_Megacode_DLG",displayNull];
private _dummy = uiNamespace getVariable ["ACME_MC_target",objNull];
if (isNull _disp || {isNull _dummy}) exitWith {};
private _pageKey = toLowerANSI _page;
uiNamespace setVariable ["ACME_MC_page",_pageKey];

{if (!isNull _x) then {ctrlDelete _x;};} forEach (uiNamespace getVariable ["ACME_MC_contentCtrls",[]]);
private _acc = [];
private _geo = uiNamespace getVariable ["ACME_MC_geometry",[]];
if (count _geo < 16) exitWith {diag_log "[ACME][Megacode] Menu aborted: panel geometry missing";};
_geo params ["_pX","_pY","_pW","_pH","_rX","_rY","_rW","_rH"];
private _theme = uiNamespace getVariable ["ACME_MC_theme",createHashMap];
private _col = {params ["_k",["_fb",[1,1,1,1]]]; _theme getOrDefault [_k,_fb]};

// Remember what this page was drawn from, so the tick can redraw it when that changes elsewhere.
private _sigFn = uiNamespace getVariable ["ACME_MC_pageSigFn",{[]}];
uiNamespace setVariable ["ACME_MC_pageSig",[_pageKey,[_dummy,_pageKey] call _sigFn]];

// Tab highlight: the open page is the selected (light) tab; RESET keeps the danger colour.
{
    if (!isNull _x) then {
        private _k = _x getVariable ["ACME_MC_pageKey",""];
        private _active = _k == _pageKey;
        _x ctrlSetBackgroundColor (if (_active) then {["selected"] call _col} else {if (_k == "reset") then {["danger"] call _col} else {["active"] call _col}});
        _x ctrlSetTextColor (if (_active) then {["darkInk"] call _col} else {if (_k == "reset") then {["dangerInk"] call _col} else {["ink"] call _col}});
    };
} forEach (uiNamespace getVariable ["ACME_MC_navCtrls",[]]);

private _fs = _pH*0.026;        // button and label text
private _hdrH = _pH*0.034;      // section label row
private _gapX = _rW*0.008;
private _gapY = _pH*0.010;

private _mkLabel = {
    params ["_x","_y","_w","_h","_txt",["_color",["secondary"] call _col],["_size",_fs],["_font",ACM_UI_FONT]];
    private _c = _disp ctrlCreate ["RscText",-1];
    _c ctrlSetPosition [_x,_y,_w,_h]; _c ctrlSetText _txt; _c ctrlSetTextColor _color; _c ctrlSetBackgroundColor [0,0,0,0];
    _c ctrlSetFont _font; _c ctrlSetFontHeight _size; _c ctrlCommit 0; _acc pushBack _c; _c
};
// a muted, upper-case section label with a hairline under it.
private _mkHeader = {
    params ["_x","_y","_w","_txt"];
    [_x,_y,_w,_hdrH,toUpper _txt,["muted"] call _col,_pH*0.021,"RobotoCondensedBold"] call _mkLabel;
    private _l = _disp ctrlCreate ["RscText",-1];
    _l ctrlSetPosition [_x,_y+_hdrH-(_pH*0.0035),_w,_pH*0.0015]; _l ctrlSetBackgroundColor (["rule"] call _col); _l ctrlCommit 0; _acc pushBack _l;
    _y + _hdrH + (_pH*0.006)
};
// _state: "normal", "selected" (the current setting), "danger" (destroys or stops something) or "off" (disabled).
private _mkBtn = {
    params ["_x","_y","_w","_h","_txt","_key","_eh",["_state","normal"],["_tip",""]];
    private _b = _disp ctrlCreate ["ACME_ThemeButton",-1];
    _b ctrlSetPosition [_x,_y,_w,_h]; _b ctrlSetText _txt;
    _b ctrlSetFont ACM_UI_FONT; _b ctrlSetFontHeight _fs;
    switch (_state) do {
        case "selected": {_b ctrlSetBackgroundColor (["selected"] call _col); _b ctrlSetTextColor (["darkInk"] call _col);};
        case "danger": {_b ctrlSetBackgroundColor (["danger"] call _col); _b ctrlSetTextColor (["dangerInk"] call _col);};
        default {_b ctrlSetBackgroundColor (["active"] call _col); _b ctrlSetTextColor (["ink"] call _col);};
    };
    if (_tip != "") then {_b ctrlSetTooltip _tip;};
    _b setVariable ["mc_key",_key]; _b ctrlAddEventHandler ["ButtonClick",_eh];
    if (_state == "off") then {_b ctrlEnable false;};
    _b ctrlCommit 0; _acc pushBack _b; _b
};
// one row: label | slider | value. _div 10 shows the value divided by ten with one decimal (temperature).
private _fmtValue = {
    params ["_v","_unit","_div"];
    private _n = if (_div == 10) then {((round _v)/10) toFixed 1} else {str (round _v)};
    format ["<t align='right' font='RobotoCondensedBold'>%1</t><t align='right' color='#a8a8a8'> %2</t>",_n,_unit]
};
private _mkSlider = {
    params ["_x","_y","_w","_h","_lbl","_key","_min","_max","_val",["_unit",""],["_div",1],["_eh",{}]];
    [_x,_y,_w*0.34,_h,_lbl] call _mkLabel;
    private _vc = _disp ctrlCreate ["RscStructuredText",-1];
    _vc ctrlSetPosition [_x+(_w*0.80),_y+((_h-(_fs*1.25))/2),_w*0.20,_fs*1.25];
    _vc ctrlSetBackgroundColor [0,0,0,0]; _vc ctrlSetFontHeight _fs;
    _vc ctrlSetStructuredText parseText ([_val,_unit,_div] call _fmtValue);
    _vc ctrlCommit 0; _acc pushBack _vc;
    private _s = _disp ctrlCreate ["RscXSliderH",-1];
    _s ctrlSetPosition [_x+(_w*0.34),_y+(_h*0.22),_w*0.45,_h*0.56]; _s sliderSetRange [_min,_max]; _s sliderSetPosition _val;
    _s setVariable ["mc_key",_key]; _s setVariable ["mc_valctrl",_vc]; _s setVariable ["mc_fmt",[_unit,_div,_fmtValue]];
    _s ctrlAddEventHandler ["SliderPosChanged",{
        params ["_c","_v"];
        private _vc=_c getVariable ["mc_valctrl",controlNull];
        (_c getVariable ["mc_fmt",["",1,{""}]]) params ["_unit","_div","_fmt"];
        if (!isNull _vc) then {_vc ctrlSetStructuredText parseText ([_v,_unit,_div] call _fmt);};
        [(_c getVariable ["mc_key",""]),_v] call ACME_fnc_megacodeSetVital;
    }];
    _s ctrlCommit 0; _acc pushBack _s; _s
};
// a row of equal buttons: [[label, key, state, tip], ...] across _w.
private _mkRow = {
    params ["_rowX","_rowY","_rowW","_h","_defs","_eh",["_cols",-1]];
    private _n = if (_cols > 0) then {_cols} else {count _defs};
    private _bw = (_rowW - (_gapX * (_n - 1))) / _n;
    {
        _x params ["_l","_k",["_st","normal"],["_tip",""]];
        private _c = _forEachIndex mod _n; private _r = floor (_forEachIndex / _n);
        [_rowX + (_c * (_bw + _gapX)), _rowY + (_r * (_h + _gapY)), _bw, _h, _l, _k, _eh, _st, _tip] call _mkBtn;
    } forEach _defs;
};

switch _pageKey do {
    case "vitals": {
        private _colGap = _rW*0.05;
        private _cw = (_rW-_colGap)/2;
        private _shockH = _hdrH + (_pH*0.006) + (_rH*0.15);
        private _rowsTop = _rY + _hdrH + (_pH*0.006);
        private _rowH = ((_rY + _rH - _shockH - _gapY) - _rowsTop) / 4;  // (not _rh: SQF names ignore case, _rh is _rH)
        private _x1 = _rX + _cw + _colGap;
        [_rX,_rY,_cw,"Circulation (targets; the monitor eases to them)"] call _mkHeader;
        [_x1,_rY,_cw,"Respiration and temperature"] call _mkHeader;
        {
            _x params ["_c","_r","_l","_k","_mn","_mx","_v","_u",["_div",1]];
            [if (_c == 0) then {_rX} else {_x1},_rowsTop+(_r*_rowH),_cw,_rowH*0.92,_l,_k,_mn,_mx,_v,_u,_div] call _mkSlider;
        } forEach [
            [0,0,"Heart rate","HR",0,260,_dummy getVariable ["ACME_MC_HRTgt",78],"bpm"],
            [0,1,"Systolic BP","SBP",0,260,_dummy getVariable ["ACME_MC_SBPTgt",122],"mmHg"],
            [0,2,"Diastolic BP","DBP",0,160,_dummy getVariable ["ACME_MC_DBPTgt",78],"mmHg"],
            [0,3,"SpO2","SpO2",0,100,_dummy getVariable ["ACME_MC_SpO2Tgt",98],"%"],
            [1,0,"Respiratory rate","RR",0,60,_dummy getVariable ["ACME_MC_RRTgt",14],"/min"],
            [1,1,"EtCO2","EtCO2",0,90,_dummy getVariable ["ACME_MC_EtCO2Tgt",38],"mmHg"],
            [1,2,"Temperature","Temp",300,420,(_dummy getVariable ["ACME_MC_Temp",37])*10,"C",10]
        ];
        // shock-state instructor controls, kept here where their hemodynamic effect is visible.
        private _sy = _rY + _rH - _shockH;
        private _by = [_rX,_sy,_rW,"Forced shock phenotype"] call _mkHeader;
        private _forced = toLowerANSI ((_dummy getVariable ["ACME_shock_forced",[]]) param [0,"auto"]);
        if (_forced == "none") then {_forced = "auto";};
        [_rX,_by,_rW,_rH*0.15,[
            ["Auto / clear","auto"],["Hemorrhagic","hemorrhagic"],["Distributive","distributive"],
            ["Cardiogenic","cardiogenic"],["Obstructive","obstructive"],["Neurogenic","neurogenic"]
        ] apply {[_x select 0,_x select 1,if ((_x select 1) == _forced) then {"selected"} else {"normal"}]},{
            private _k=(_this select 0) getVariable ["mc_key","auto"];
            private _d=uiNamespace getVariable ["ACME_MC_target",objNull];
            if (!isNull _d && {!isNil "ACME_fnc_shockSetPhenotype"}) then {
                [_d,_k,if (_k=="auto") then {0} else {0.75}] call ACME_fnc_shockSetPhenotype;
                [[format ["Shock phenotype: %1",_k],"#ffd27a"]] call ACME_fnc_megacodeLog;
                [87300,"vitals"] call ACME_fnc_megacodeMenu;
            };
        }] call _mkRow;
    };
    case "rhythm": {
        private _cur=toLowerANSI (_dummy getVariable ["ACME_MC_rhythmKey",_dummy getVariable ["ACME_MC_rhythm","sinus"]]);
        private _bh = _rH*0.19;
        private _eh = {[(_this select 0) getVariable ["mc_key",""]] call ACME_fnc_megacodeSetRhythm;};
        private _sel = {params ["_l","_k"]; [_l,_k,if (_cur == _k) then {"selected"} else {"normal"}]};
        private _y = [_rX,_rY,_rW,"Perfusing rhythms"] call _mkHeader;
        [_rX,_y,_rW,_bh,[
            ["Sinus","sinus"],["Sinus tachycardia","stach"],["Sinus bradycardia","sbrady"],["A-fib","afib"],
            ["A-fib RVR","afibrvr"],["Atrial tachycardia","atrialtach"],["SVT","svt"],["V-tach with pulse","vt"]
        ] apply {_x call _sel},_eh,4] call _mkRow;
        _y = _y + (2*_bh) + _gapY + (_pH*0.016);
        _y = [_rX,_y,_rW,"Pulseless (cardiac arrest)"] call _mkHeader;
        [_rX,_y,_rW,_bh,[["Torsades","torsades"],["V-fib","vfib"],["Asystole","asystole"],["PEA","pea"]] apply {_x call _sel},_eh,4] call _mkRow;
    };
    case "airway": {
        private _cur=toLowerANSI (_dummy getVariable ["ACME_MC_airway","patent"]);
        private _bh = _rH*0.24;
        private _eh = {[(_this select 0) getVariable ["mc_key",""]] call ACME_fnc_megacodeSetAirway;};
        private _sel = {params ["_l","_k",["_tip",""]]; [_l,_k,if (_cur == _k) then {"selected"} else {"normal"},_tip]};
        private _y = [_rX,_rY,_rW,"Airway"] call _mkHeader;
        [_rX,_y,_rW,_bh,[
            ["Patent","patent","Clears every obstruction and brings breathing back after apnea"],
            ["Blood in airway","blood"],["Vomit in airway","vomit"],["Airway collapse","collapse"],["Apnea","apnea","Respiratory rate to zero"]
        ] apply {_x call _sel},_eh] call _mkRow;
        _y = _y + _bh + (_pH*0.026);
        _y = [_rX,_y,_rW,"Chest"] call _mkHeader;
        [_rX,_y,_rW,_bh,[
            ["Pneumothorax","pneumo"],["Tension pneumothorax","tpneumo"],["Hemothorax","hemothorax"],
            ["Decompress / clear chest","ncd","Needle decompression: clears the chest injuries"]
        ] apply {_x call _sel},_eh] call _mkRow;
    };
    case "wounds": {
        private _part=uiNamespace getVariable ["ACME_MC_woundPart","Body"];
        private _names=createHashMapFromArray [["Head","head"],["Body","torso"],["LeftArm","left arm"],["RightArm","right arm"],["LeftLeg","left leg"],["RightLeg","right leg"]];
        private _bh = _rH*0.165;
        private _y = [_rX,_rY,_rW,"Target region"] call _mkHeader;
        [_rX,_y,_rW,_bh,[["Head","Head"],["Torso","Body"],["Left arm","LeftArm"],["Right arm","RightArm"],["Left leg","LeftLeg"],["Right leg","RightLeg"]] apply {
            [_x select 0,_x select 1,if (_part == (_x select 1)) then {"selected"} else {"normal"}]
        },{uiNamespace setVariable ["ACME_MC_woundPart",(_this select 0) getVariable ["mc_key","Body"]]; [87300,"wounds"] call ACME_fnc_megacodeMenu;}] call _mkRow;
        _y = _y + _bh + (_pH*0.016);
        _y = [_rX,_y,_rW,format ["Add a wound to the %1",_names getOrDefault [_part,"torso"]]] call _mkHeader;
        private _addEh = {[(_this select 0) getVariable ["mc_key","laceration"]] call ACME_fnc_megacodeAddWound;};
        [_rX,_y,_rW,_bh,[["Laceration","laceration"],["Gunshot","gunshot"],["Avulsion","avulsion"],["Amputation","amputation"],["Burn","burn"],["Crush","crush"],["Fragmentation","velocity"]],_addEh] call _mkRow;
        _y = _y + _bh + (_pH*0.016);
        _y = [_rX,_y,_rW,"Junctional hemorrhage (two per region at most)"] call _mkHeader;
        private _w3 = (_rW - (2*_gapX)) / 3;
        [_rX,_y,_w3,_bh,"Axilla (arm)","axilla",_addEh,"normal","Junctional bleed at the armpit, next free arm"] call _mkBtn;
        [_rX+_w3+_gapX,_y,_w3,_bh,"Inguinal (leg)","inguinal",_addEh,"normal","Junctional bleed at the groin, next free leg"] call _mkBtn;
        [_rX+(2*(_w3+_gapX)),_y,_w3,_bh,"Clear all wounds","clear",_addEh,"danger","Removes every wound and bleed and refills the blood volume"] call _mkBtn;
    };
    case "neuro": {
        private _colGap=_rW*0.05; private _cw=(_rW-_colGap)/2; private _x2=_rX+_cw+_colGap;
        private _y = [_rX,_rY,_cw,"Intracranial"] call _mkHeader;
        private _rowH = _rH*0.20;
        [_rX,_y,_cw,_rowH,"ICP","ICP",0,60,_dummy getVariable ["ACME_MC_ICP",10],"mmHg"] call _mkSlider;
        [_rX,_y+_rowH,_cw,_rowH,"GCS","GCS",3,15,_dummy getVariable ["ACME_MC_GCS",15],""] call _mkSlider;
        private _help = _disp ctrlCreate ["RscStructuredText",-1];
        _help ctrlSetPosition [_rX,_y+(2*_rowH)+_gapY,_cw,(_rY+_rH)-(_y+(2*_rowH)+_gapY)];
        _help ctrlSetBackgroundColor [0,0,0,0]; _help ctrlSetFontHeight (_pH*0.023);
        _help ctrlSetStructuredText parseText "<t color='#a8a8a8'>ICP above 20 mmHg drives a Cushing response (bradycardia, hypertension). GCS below 9 makes the manikin unconscious.</t>";
        _help ctrlCommit 0; _acc pushBack _help;
        private _unc=_dummy getVariable ["ACE_isUnconscious",false];
        private _hern=_dummy getVariable ["ACME_MC_herniation",false];
        private _by = [_x2,_rY,_cw,"State"] call _mkHeader;
        private _bh=_rH*0.24;
        private _eh = {[(_this select 0) getVariable ["mc_key",""]] call ACME_fnc_megacodeSetFeature;};
        [_x2,_by,_cw,_bh,if (_hern) then {"Herniation: ON (click to end)"} else {"Herniation (Cushing + coma)"},"herniation",_eh,if (_hern) then {"selected"} else {"normal"}] call _mkBtn;
        [_x2,_by+_bh+_gapY,_cw,_bh,if (_unc) then {"Unconscious: wake up"} else {"Make unconscious"},"uncon",_eh,if (_unc) then {"selected"} else {"normal"}] call _mkBtn;
    };
    case "scenario": {
        private _act=_dummy getVariable ["ACME_MC_scenActive",false]; private _nm=_dummy getVariable ["ACME_MC_scenName",""];
        private _st = _disp ctrlCreate ["RscStructuredText",-1];
        _st ctrlSetPosition [_rX,_rY,_rW,_pH*0.040]; _st ctrlSetBackgroundColor [0,0,0,0]; _st ctrlSetFontHeight _fs;
        _st ctrlSetStructuredText parseText (if (_act) then {
            format ["<t font='RobotoCondensedBold' color='#f3f1ed'>Running: %1</t><t color='#a8a8a8'>   stages advance on their own; the arrest then waits for the trainee.</t>",_nm]
        } else {
            "<t color='#a8a8a8'>No scenario running. Pick one: the manikin deteriorates over a few minutes, most toward a cardiac arrest.</t>"
        });
        _st ctrlCommit 0; _acc pushBack _st;
        private _y = [_rX,_rY+(_pH*0.046),_rW,"Scenarios"] call _mkHeader;
        // [button label, key, the scenario's name in ACME_fnc_megacodeScenario, by which the running one is found].
        private _scn=[["ACS -> VF arrest","acs_vf","ACS -> VF arrest"],["Tension pneumo -> PEA","tension_pea","Tension pneumo -> PEA"],["Hemorrhage -> PEA","hemorrhage_pea","Hemorrhagic shock -> PEA"],["Hyperkalemia -> VF","hyperk_vf","Hyperkalemia -> VF"],["ICP -> herniation","icp_herniation","Rising ICP -> herniation -> arrest"],["Hypoxia -> asystole","hypoxia_asys","Hypoxia -> bradyasystole"],["Sepsis -> PEA","sepsis_pea","Septic shock -> PEA"]];
        private _bh = _rH*0.19;
        [_rX,_y,_rW,_bh,_scn apply {[_x select 0,_x select 1,if (_act && {_nm == (_x select 2)}) then {"selected"} else {"normal"},_x select 2]},{[(_this select 0) getVariable ["mc_key",""]] call ACME_fnc_megacodeScenario;},4] call _mkRow;
        private _sy = _y + (2*_bh) + _gapY + (_pH*0.018);
        [_rX,_sy,(_rW-(3*_gapX))/4,_bh,if (_act) then {"Stop scenario"} else {"No scenario running"},"stop",{["stop"] call ACME_fnc_megacodeScenario;},if (_act) then {"danger"} else {"off"}] call _mkBtn;
        [_rX+((_rW-(3*_gapX))/4)+_gapX,_sy,_rW*0.5,_bh,format ["Pace x%1 (ACME_megacode_scenarioPace; lower is faster)",(missionNamespace getVariable ["ACME_megacode_scenarioPace",1]) toFixed 1],["muted"] call _col,_pH*0.022] call _mkLabel;
    };
    case "log": {
        private _y = [_rX,_rY,_rW,"Activity log, newest first"] call _mkHeader;
        private _log=uiNamespace getVariable ["ACME_MC_log",[]];
        private _grpH = (_rY+_rH)-_y;
        // a scrolling group, so a long session can be read back in full.
        private _grp = _disp ctrlCreate ["RscControlsGroupNoHScrollbars",-1];
        _grp ctrlSetPosition [_rX,_y,_rW,_grpH]; _grp ctrlCommit 0; _acc pushBack _grp;
        private _box = _disp ctrlCreate ["RscStructuredText",-1,_grp];
        private _txt=if (_log isEqualTo []) then {"<t color='#a8a8a8'>Nothing applied yet. Every change made from this panel, and every scenario stage, is listed here.</t>"} else {
            (_log apply {_x params [["_m",""],["_h","#cfe8ff"]]; format ["<t color='%1'>%2</t>",_h,_m]}) joinString "<br/>"
        };
        _box ctrlSetBackgroundColor [0,0,0,0]; _box ctrlSetFontHeight (_pH*0.024);
        _box ctrlSetPosition [0,0,_rW-(_pW*0.016),_grpH]; _box ctrlCommit 0;
        _box ctrlSetStructuredText parseText _txt;
        _box ctrlSetPosition [0,0,_rW-(_pW*0.016),(ctrlTextHeight _box) max _grpH]; _box ctrlCommit 0;
    };
    default {[_rX,_rY,_rW,_hdrH,"Unknown Megacode page",[1,0.4,0.4,1]] call _mkLabel;};
};
uiNamespace setVariable ["ACME_MC_contentCtrls",_acc];
