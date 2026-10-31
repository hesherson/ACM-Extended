#include "..\script_component.hpp"
/* GUI-owned replacement of ACE's unqualified renderer by a generation-bound
 * procedure renderer. Never remove the protected live handler if the handles
 * coincide. The caller must validate its display/generation before calling.
 * Returns the former ACE handle for diagnostic logging, including malformed
 * legacy values; the global handle is reset in every case, as before.
 */
params [["_protectedPFH", -1, [0]]];
private _acePFH = missionNamespace getVariable ["ace_medical_gui_menuPFH", -1];
if (_acePFH isEqualType 0 && {_acePFH >= 0} && {_acePFH != _protectedPFH}) then {
    [_acePFH] call CBA_fnc_removePerFrameHandler;
};
missionNamespace setVariable ["ace_medical_gui_menuPFH", -1];
_acePFH
