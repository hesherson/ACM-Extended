# Bounded AQ: timed push owns dosing-relevant syringe contents

Parent is the retained cumulative AM-AP candidate on published AK-AL. A stable syringe ID prevented index drift, but an external same-ID row mutation could still replace medication, size, drug/diluent volume, component plan or recipe marker between confirmation and completion. The authored plunger would then describe the old row while completion handed off the changed row.

Confirmation now captures only dosing-relevant row fields and rechecks them at the existing settle and completion boundaries. Cosmetic label/tag text is deliberately excluded. A mismatch retires the old normal job without administering or rewriting the changed syringe. No per-frame store scan is added, so animation performance is unchanged. Existing stable-ID, patient/provider/workspace, timing, Hardcore and epinephrine-volume ownership remain.

Fourteen new execution cases: cumulative AM-AP runtime produces twelve intended failures and two passing cosmetic controls; candidate passes all fourteen. This does not prevent arbitrary memory corruption, mutation after the final check has entered the authoritative handoff, or changes outside the normal display-bound push path. No H entry closes in AQ.
