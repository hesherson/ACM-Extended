/* B117 aspect-safe Megacode lower-page builder. */
params ["_idd","_page"];
private _disp = uiNamespace getVariable ["ACME_Megacode_DLG",displayNull];
private _dummy = uiNamespace getVariable ["ACME_MC_target",objNull];
if (isNull _disp || {isNull _dummy}) exitWith {};
uiNamespace setVariable ["ACME_MC_page",toLowerANSI _page];

{if (!isNull _x) then {ctrlDelete _x;};} forEach (uiNamespace getVariable ["ACME_MC_contentCtrls",[]]);
private _acc = [];
private _geo = uiNamespace getVariable ["ACME_MC_geometry",[]];
if (count _geo < 16) exitWith {diag_log "[ACME][Megacode] Menu aborted: panel geometry missing";};
_geo params ["_pX","_pY","_pW","_pH","_rX","_rY","_rW","_rH"];

// Update page-button highlight without depending on the legacy config controls.
{
    if (!isNull _x) then {
        private _k = _x getVariable ["ACME_MC_pageKey",""];
        private _active = _k == toLowerANSI _page;
        private _base = switch _k do {case "scenario":{[0.20,0.12,0.28,1]}; case "log":{[0.10,0.20,0.16,1]}; case "reset":{[0.35,0.20,0.10,1]}; case "done":{[0.30,0.10,0.12,1]}; default {[0.10,0.13,0.18,1]};};
        _x ctrlSetBackgroundColor (if (_active) then {[0.18,0.45,0.62,1]} else {_base});
    };
} forEach (uiNamespace getVariable ["ACME_MC_navCtrls",[]]);

private _mkLabel = {
    params ["_x","_y","_w","_h","_txt",["_col",[0.85,0.88,0.94,1]],["_align",0]];
    private _c = _disp ctrlCreate ["RscText",-1];
    _c ctrlSetPosition [_x,_y,_w,_h]; _c ctrlSetText _txt; _c ctrlSetTextColor _col; _c ctrlSetBackgroundColor [0,0,0,0];
    _c ctrlSetFontHeight (_h*0.62); _c ctrlCommit 0; _acc pushBack _c; _c
};
private _mkBtn = {
    params ["_x","_y","_w","_h","_txt","_key","_eh",["_active",false]];
    private _b = _disp ctrlCreate ["ACME_ThemeButton",-1];
    _b ctrlSetPosition [_x,_y,_w,_h]; _b ctrlSetText _txt; _b ctrlSetTextColor [0.92,0.95,1,1];
    _b ctrlSetBackgroundColor (if (_active) then {[0.18,0.45,0.62,1]} else {[0.10,0.12,0.16,1]});
    _b ctrlSetFontHeight (_h*0.42); _b setVariable ["mc_key",_key]; _b ctrlAddEventHandler ["ButtonClick",_eh]; _b ctrlCommit 0;
    _acc pushBack _b; _b
};
private _mkSlider = {
    params ["_x","_y","_w","_h","_lbl","_key","_min","_max","_val"];
    [_x,_y,_w*0.36,_h*0.45,_lbl,[0.78,0.84,0.94,1]] call _mkLabel;
    private _vc = _disp ctrlCreate ["RscText",-1];
    _vc ctrlSetPosition [_x+(_w*0.36),_y,_w*0.14,_h*0.45]; _vc ctrlSetText str (round _val); _vc ctrlSetTextColor [1,1,1,1];
    _vc ctrlSetFontHeight (_h*0.34); _vc ctrlCommit 0; _acc pushBack _vc;
    private _s = _disp ctrlCreate ["RscXSliderH",-1];
    _s ctrlSetPosition [_x+(_w*0.36),_y+(_h*0.48),_w*0.62,_h*0.34]; _s sliderSetRange [_min,_max]; _s sliderSetPosition _val;
    _s setVariable ["mc_key",_key]; _s setVariable ["mc_valctrl",_vc];
    _s ctrlAddEventHandler ["SliderPosChanged",{params ["_c","_v"]; private _vc=_c getVariable ["mc_valctrl",controlNull]; if (!isNull _vc) then {_vc ctrlSetText str (round _v);}; [(_c getVariable ["mc_key",""]),_v] call ACME_fnc_megacodeSetVital;}];
    _s ctrlCommit 0; _acc pushBack _s; _s
};

private _pageKey = toLowerANSI _page;
switch _pageKey do {
    case "vitals": {
        private _colGap = _rW*0.04;
        private _cw = (_rW-_colGap)/2;
        private _rh = _rH*0.205;
        private _defs = [
            ["Heart Rate","HR",0,260,_dummy getVariable ["ACME_MC_HRTgt",78]],
            ["SpO2","SpO2",0,100,_dummy getVariable ["ACME_MC_SpO2Tgt",98]],
            ["Systolic BP","SBP",0,260,_dummy getVariable ["ACME_MC_SBPTgt",122]],
            ["Diastolic BP","DBP",0,160,_dummy getVariable ["ACME_MC_DBPTgt",78]],
            ["Resp Rate","RR",0,60,_dummy getVariable ["ACME_MC_RRTgt",14]],
            ["EtCO2","EtCO2",0,90,_dummy getVariable ["ACME_MC_EtCO2Tgt",38]],
            ["Temp x10 C","Temp",300,420,(_dummy getVariable ["ACME_MC_Temp",37])*10]
        ];
        {
            private _col = floor (_forEachIndex/4);
            private _row = _forEachIndex mod 4;
            _x params ["_l","_k","_mn","_mx","_v"];
            [_rX+(_col*(_cw+_colGap)),_rY+(_row*_rh),_cw,_rh*0.90,_l,_k,_mn,_mx,_v] call _mkSlider;
        } forEach _defs;

        // New shock-state instructor controls are kept on the VITALS page, where their hemodynamic effect is visible.
        private _sy = _rY+(_rh*3.18);
        [_rX+_cw+_colGap,_sy,_cw,_rh*0.22,"Shock phenotype",[1,0.80,0.48,1]] call _mkLabel;
        private _shock = [["AUTO/CLEAR","auto"],["HEM","hemorrhagic"],["DIST","distributive"],["CARD","cardiogenic"],["OBSTR","obstructive"],["NEURO","neurogenic"]];
        private _bw = (_cw-(_rW*0.004*5))/6;
        {
            _x params ["_l","_k"];
            [_rX+_cw+_colGap+(_forEachIndex*(_bw+_rW*0.004)),_sy+(_rh*0.26),_bw,_rh*0.40,_l,_k,{private _k=(_this select 0) getVariable ["mc_key","auto"]; private _d=uiNamespace getVariable ["ACME_MC_target",objNull]; if (!isNull _d && {!isNil "ACME_fnc_shockSetPhenotype"}) then {[_d,_k,if (_k=="auto") then {0} else {0.75}] call ACME_fnc_shockSetPhenotype;};},false] call _mkBtn;
        } forEach _shock;
    };
    case "rhythm": {
        private _defs = [["Sinus","sinus"],["Sinus Tach","stach"],["Sinus Brady","sbrady"],["A-Fib","afib"],["A-Fib RVR","afibrvr"],["Atrial Tach","atrialtach"],["SVT","svt"],["V-Tach","vt"],["Torsades","torsades"],["V-Fib","vfib"],["Asystole","asystole"],["PEA","pea"]];
        private _cols=4; private _gap=_rW*0.008; private _bw=(_rW-(_gap*3))/_cols; private _bh=(_rH-(_gap*2))/3;
        private _cur=toLowerANSI (_dummy getVariable ["ACME_MC_rhythmKey",_dummy getVariable ["ACME_MC_rhythm","sinus"]]);
        {
            _x params ["_l","_k"]; private _col=_forEachIndex mod _cols; private _row=floor(_forEachIndex/_cols);
            [_rX+(_col*(_bw+_gap)),_rY+(_row*(_bh+_gap)),_bw,_bh,_l,_k,{[(_this select 0) getVariable ["mc_key",""]] call ACME_fnc_megacodeSetRhythm;},_cur==_k] call _mkBtn;
        } forEach _defs;
    };
    case "airway": {
        private _defs=[["Patent","patent"],["Blood Obstruction","blood"],["Vomit Obstruction","vomit"],["Airway Collapse","collapse"],["Apnea","apnea"],["Pneumothorax","pneumo"],["Tension Pneumo","tpneumo"],["Hemothorax","hemothorax"],["Decompress / Clear","ncd"]];
        private _cols=3; private _gap=_rW*0.008; private _bw=(_rW-(_gap*2))/3; private _bh=(_rH-(_gap*2))/3; private _cur=toLowerANSI (_dummy getVariable ["ACME_MC_airway","patent"]);
        {_x params ["_l","_k"]; private _col=_forEachIndex mod 3; private _row=floor(_forEachIndex/3); [_rX+(_col*(_bw+_gap)),_rY+(_row*(_bh+_gap)),_bw,_bh,_l,_k,{[(_this select 0) getVariable ["mc_key",""]] call ACME_fnc_megacodeSetAirway;},_cur==_k] call _mkBtn;} forEach _defs;
    };
    case "wounds": {
        private _sel=uiNamespace getVariable ["ACME_MC_woundPart","Body"];
        [_rX,_rY,_rW,_rH*0.10,format ["Target region: %1",_sel],[1,0.9,0.5,1]] call _mkLabel;
        private _parts=[["Head","Head"],["Torso","Body"],["L Arm","LeftArm"],["R Arm","RightArm"],["L Leg","LeftLeg"],["R Leg","RightLeg"]];
        private _pg=_rW*0.006; private _pbw=(_rW-(_pg*5))/6; private _pbh=_rH*0.18; private _py=_rY+(_rH*0.11);
        {_x params ["_l","_k"]; [_rX+(_forEachIndex*(_pbw+_pg)),_py,_pbw,_pbh,_l,_k,{uiNamespace setVariable ["ACME_MC_woundPart",(_this select 0) getVariable ["mc_key","Body"]]; [87300,"wounds"] call ACME_fnc_megacodeMenu;},_sel==_k] call _mkBtn;} forEach _parts;
        private _wounds=[["Laceration","laceration"],["Gunshot","gunshot"],["Avulsion","avulsion"],["Amputation","amputation"],["Burn","burn"],["Crush","crush"],["Velocity/Frag","velocity"],["Spawn Axilla","axilla"],["Spawn Inguinal","inguinal"],["Clear All Wounds","clear"]];
        private _cols=5; private _gap=_rW*0.006; private _bw=(_rW-(_gap*4))/5; private _bh=_rH*0.27; private _wy=_py+_pbh+(_rH*0.05);
        {_x params ["_l","_k"]; private _col=_forEachIndex mod 5; private _row=floor(_forEachIndex/5); [_rX+(_col*(_bw+_gap)),_wy+(_row*(_bh+_gap)),_bw,_bh,_l,_k,{[(_this select 0) getVariable ["mc_key","laceration"]] call ACME_fnc_megacodeAddWound;},false] call _mkBtn;} forEach _wounds;
    };
    case "neuro": {
        private _gap=_rW*0.04; private _cw=(_rW-_gap)/2; private _rh=_rH*0.28;
        [_rX,_rY,_cw,_rh,"ICP (mmHg)","ICP",0,60,_dummy getVariable ["ACME_MC_ICP",10]] call _mkSlider;
        [_rX,_rY+_rh,_cw,_rh,"GCS","GCS",3,15,_dummy getVariable ["ACME_MC_GCS",15]] call _mkSlider;
        [_rX,_rY+(_rh*2),_cw,_rH*0.18,"ICP drives Cushing response. GCS <9 drives unconsciousness.",[0.72,0.78,0.88,1]] call _mkLabel;
        private _unc=_dummy getVariable ["ACE_isUnconscious",false]; private _bw=_cw; private _bh=_rH*0.28; private _x2=_rX+_cw+_gap;
        [_x2,_rY,_bw,_bh,"Herniation (Cushing + coma)","herniation",{[(_this select 0) getVariable ["mc_key",""]] call ACME_fnc_megacodeSetFeature;},false] call _mkBtn;
        [_x2,_rY+_bh+(_rH*0.04),_bw,_bh,if (_unc) then {"Wake Up"} else {"Make Unconscious"},"uncon",{[(_this select 0) getVariable ["mc_key",""]] call ACME_fnc_megacodeSetFeature;},false] call _mkBtn;
    };
    case "scenario": {
        private _act=_dummy getVariable ["ACME_MC_scenActive",false]; private _nm=_dummy getVariable ["ACME_MC_scenName",""];
        [_rX,_rY,_rW,_rH*0.11,if (_act) then {format ["Running: %1",_nm]} else {"Pick a scenario."},if (_act) then {[0.78,0.62,1,1]} else {[1,0.9,0.5,1]}] call _mkLabel;
        private _scn=[["ACS -> VF arrest","acs_vf"],["Tension pneumo -> PEA","tension_pea"],["Hemorrhage -> PEA","hemorrhage_pea"],["Hyperkalemia -> VF","hyperk_vf"],["Rising ICP -> herniation","icp_herniation"],["Hypoxia -> bradyasystole","hypoxia_asys"],["Septic shock -> PEA","sepsis_pea"]];
        private _cols=4; private _gap=_rW*0.008; private _bw=(_rW-(_gap*3))/4; private _bh=_rH*0.27; private _sy=_rY+(_rH*0.13);
        {_x params ["_l","_k"]; private _col=_forEachIndex mod 4; private _row=floor(_forEachIndex/4); [_rX+(_col*(_bw+_gap)),_sy+(_row*(_bh+_gap)),_bw,_bh,_l,_k,{[(_this select 0) getVariable ["mc_key",""]] call ACME_fnc_megacodeScenario;},false] call _mkBtn;} forEach _scn;
        private _stop=[_rX,_rY+(_rH*0.77),_rW*0.42,_rH*0.18,if (_act) then {"STOP SCENARIO"} else {"(no scenario running)"},"stop",{["stop"] call ACME_fnc_megacodeScenario;},_act] call _mkBtn;
        _stop ctrlEnable _act; if (_act) then {_stop ctrlSetBackgroundColor [0.48,0.10,0.10,1];};
    };
    case "log": {
        private _log=uiNamespace getVariable ["ACME_MC_log",[]];
        private _box=_disp ctrlCreate ["RscStructuredText",-1]; _box ctrlSetPosition [_rX,_rY,_rW,_rH]; _box ctrlSetBackgroundColor [0,0,0,0];
        private _txt=if (_log isEqualTo []) then {"<t align='left' size='1.0' color='#6b7785'>No actions applied yet.</t>"} else {private _s=""; {_x params [["_m",""],["_h","#cfe8ff"]]; _s=_s+format ["<t align='left' size='0.95' color='%1'>%2</t><br/>",_h,_m];} forEach _log; _s};
        _box ctrlSetStructuredText parseText _txt; _acc pushBack _box;
    };
    default {[_rX,_rY,_rW,_rH*0.2,"Unknown Megacode page",[1,0.4,0.4,1]] call _mkLabel;};
};
uiNamespace setVariable ["ACME_MC_contentCtrls",_acc];
