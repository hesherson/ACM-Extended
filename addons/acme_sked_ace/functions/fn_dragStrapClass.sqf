/*
 * Is the strap of a dragged SKED taken up to the rescuer's hip (setting acme_drag_strapRope)? Returns "" when it
 * is left lying as it is modelled, flat on the ground. (A string, from when the strap was a rope and this named
 * the class of the rope's helper.)
 * Arguments: none. Returns: string.
 */
["", "hip"] select (missionNamespace getVariable ["acme_drag_strapRope", true])
