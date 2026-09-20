# ACM Extended 1.2.2: chest seal burping without a timer

## Changes

- Removed the six-second cooldown from traumatic and thoracostomy chest seal burping, including the shared wait between providers. This supersedes the cooldown described in the earlier repeat burping patch.
- Every completed five-notch peel can burp the seal immediately. Continuing to scroll starts another peel without moving the cursor away. Partial peels and lowering the corner do not repeat treatment or log entries.
- Stored cooldown values from an earlier version no longer block burping. Patient ownership checks and dead patient handling remain in place.

Version remains 1.2.2.

## Validation

Both branches passed 25 focused checks, including SQF execution, strict HEMTT diagnostics and addon config compilation.

The SQF execution checks cover repeated peels without advancing time, both wheel directions and seal types, partial peels, lowering and immediate reuse, multiple providers, ownership, old cooldown records and dead patients. Engine display, animation, network and physiology effects are simulated; actual multiplayer playback still needs verification.
