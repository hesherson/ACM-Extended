/* What is seen on and under the casualties near the camera: an airway adjunct on the face, the HPMK laid out under
 * one who is prepped for it (fn_casualtyVisualTick.sqf). On this machine for itself; once. (Moved out of
 * fn_postInit.sqf in B394: postInit only calls registration functions.) */
if (!hasInterface || {!isNil "ACME_casualtyVisualPFH"}) exitWith {};
ACME_casualtyVisuals = createHashMap;
ACME_casualtyVisualPFH = [{call ACME_fnc_casualtyVisualTick}, 0.5, []] call CBA_fnc_addPerFrameHandler;
