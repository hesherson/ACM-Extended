# Bounded M: head-position collision completion ordering

Parent: `2fcd3e987eba4b7fd8a2ff5ba25d236983777431` (K-L).

The delayed completions in headElevSuspend and headElevateStop restored collision
before their existing ownership/state guard. An old suspension could restore mass
while a different placement owned the patient, and a previous true-lower completion
could restore collision while a new elevation was still lifting.

Only the position of the existing collision-restore call changes in each callback:
suspension checks its existing pose token and Suspended flag first; true lowering
checks that a new elevation is not active first. No timer, event handler, state key,
animation, timing, gear restoration, clinical rule or network operation is added.
The two changed source hashes are explicitly reviewed in the preservation module.

Twenty new execution cases run the complete actual SQF functions against recorded
engine-boundary fixtures. On unmodified K-L source: 6 fail and 14 pass. With the
correction: all 20 pass. Controls include current completion, owner/life changes,
nonvisible/vehicle lowering, dead-patient delegation, carrier restore-versus-park
handoffs and the actual new-lift callback restoring collision after the old callback
has been rejected. No H-index item is closed by this runtime correction alone.

The fixtures do not execute real PhysX, reproduce an actual player launch or prove
network ordering. Restore/park calls are recorded, not real engine loadout changes.
This narrow correction does not add ownership generations to initial roll retries,
solve ownership moving away and back, or solve lower/elevate/lower ABA sequences.
Those remain open lifecycle investigations. Live Arma and release approval remain
outstanding. Broad validation is recorded with bounded N and the evidence artifact.
