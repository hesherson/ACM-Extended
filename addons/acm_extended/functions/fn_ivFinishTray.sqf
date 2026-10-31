/* Finishing tools share the catheter tray typography and layout. Their labels
   and silhouettes read the same real inventory stock used at attachment. */
params ["_d","_left","_y","_w","_h","_labelH","_step"];
private _tools=[["extension","EXTENSION"],["flush","10 mL FLUSH"],["dressing","TEGADERM"],["line","IV TUBING"],["lock","SALINE LOCK"]];
private _ctrls=[];
{
    _x params ["_tool","_label"];
    private _top=_y+_step*_forEachIndex;
    private _bg=[_d,"RscText",-1,controlNull,"panel"] call ACME_fnc_uiGlassControl;_bg ctrlSetBackgroundColor [0.10,0.13,0.17,0.92];
    _bg ctrlSetPosition [_left,_top,_w,_h];_bg ctrlCommit 0;_bg ctrlEnable false;
    private _pic=_d ctrlCreate ["RscPictureKeepAspect",-1];
    _pic ctrlSetText (if (_tool=="lock") then {"\acm_extended\ui\iv\field\icon_lock_ca.paa"} else {if (_tool=="flush") then {"\acm_extended\ui\items\salineFlush_ca.paa"} else {format ["\acm_extended\ui\iv\finish\icon_%1_ca.paa",_tool]}});
    _pic ctrlSetPosition [(_left)+_w*0.08,_top+_h*0.08,_w*0.84,_h*0.84];_pic ctrlCommit 0;_pic ctrlEnable false;
    private _text=_d ctrlCreate ["ACME_IV_ToolLabel",-1];_text ctrlSetText _label;
    _text ctrlSetPosition [_left,_top+_h,_w,_labelH];_text ctrlCommit 0;_text ctrlEnable false;
    private _click=_d ctrlCreate ["ACME_IV_ToolButton",-1];_click ctrlSetText "";
    _click ctrlSetPosition [_left,_top,_w,_h];_click ctrlSetBackgroundColor [0,0,0,0];_click ctrlCommit 0;
    _click ctrlSetTooltip (switch (_tool) do {
        case "lock": {"Attach to the catheter hub, secure with Tegaderm, then insert another 14g/16g catheter through its port."};
        case "extension": {"Connect the extension to a seated catheter hub."};
        case "flush": {"Connect, aspirate and flush. A missed line gives no blood return."};
        case "dressing": {"Secure the primary saline lock before field insertion; cover the completed setup after checking the line."};
        default {"Connect IV tubing to a catheter, extension or saline-lock port. Attach a bag in Transfusions."};
    });
    _click setVariable ["ACME_IV_Tool",_tool];
    _click ctrlAddEventHandler ["ButtonClick",{[(_this select 0) getVariable ["ACME_IV_Tool",""]] call ACME_fnc_ivFinishGrab;}];
    _ctrls pushBack [_tool,_pic,_text,_click];
} forEach _tools;
_d setVariable ["ACME_IV_FinishTray",_ctrls];
