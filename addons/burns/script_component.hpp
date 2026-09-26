#define COMPONENT burns
#define COMPONENT_BEAUTIFIED Burns
#include "\x\ACM\addons\main\script_mod.hpp"

// #define DEBUG_MODE_FULL
// #define DISABLE_COMPILE_CACHE

#ifdef DEBUG_ENABLED_BURNS
    #define DEBUG_MODE_FULL
#endif

#ifdef DEBUG_SETTINGS_BURNS
    #define DEBUG_SETTINGS DEBUG_SETTINGS_BURNS
#endif

#include "\x\ACM\addons\main\script_macros.hpp"

// Additional pain when a 2nd/3rd-degree burn is bandaged with a non-silver-nylon dressing.
#define BURN_WRONG_DRESSING_PAIN 0.25
