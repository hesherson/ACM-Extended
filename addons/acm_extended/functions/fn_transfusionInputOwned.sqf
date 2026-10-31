/* A nested transfusion/clamp display owns mouse input, independently of display EH order.
 * Read this both when background cancellation is queued and when its deferred callback runs. */
!isNull (findDisplay 86000) || {!isNull (findDisplay 86200)}
