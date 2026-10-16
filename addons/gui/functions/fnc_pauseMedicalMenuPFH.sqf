#include "..\script_component.hpp"
/* B263: modal handoff retires BOTH native ACE menuPFH and ACME's generation-
 * bound medical renderer before closing the source menu. Either handler can
 * call ACE menuPFH, whose stale-display path calls closeDialog 0 and can
 * destroy a newly opened chest/thora dialog on the following frame.
 * Only PFHs owned by this medical menu are retired; never touch unrelated UI.
 */
private _renderer = uiNamespace getVariable ["ACME_medicalMenuRendererPFH", -1];
private _native = missionNamespace getVariable ["ace_medical_gui_menuPFH", -1];
private _retired = false;
if (_renderer isEqualType 0 && {_renderer >= 0}) then {
    [_renderer] call CBA_fnc_removePerFrameHandler;
    uiNamespace setVariable ["ACME_medicalMenuRendererPFH", -1];
    _retired = true;
};
if (_native isEqualType 0 && {_native >= 0}) then {
    if (_native != _renderer) then {[_native] call CBA_fnc_removePerFrameHandler;};
    missionNamespace setVariable ["ace_medical_gui_menuPFH", -1];
    _retired = true;
};
_retired
