#include "..\script_component.hpp"
/* treatmentNative passes this same callback array to progress/success/failure. */
private _id = ["start",_this] call FUNC(shieldSource);
_this set [7,_id];
