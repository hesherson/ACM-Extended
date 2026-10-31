# B300 — transfusion captions, original colors, icons and prepared propofol

Candidate 1.2.4.1 / B300, multiplayer protocol 2. Baseline B299 `2e463fd1457905fd1f6bb087bbc87991e08a36ae`. Existing PR #31 stays draft and unmerged.

## Requested corrections

The two empty captions were rendered by different systems. Native uses ACME_TransfusionCaption (RobotoCondensed, sizeEx 0.017 safeZoneH); React independently rendered “No fluids at this access” with a 0.020 viewport font. B300 removes the browser empty caption entirely. The existing native card pool owns all empty captions, including while React is ready. The empty browser remains hidden and disabled, and the same populated renderer is shown when a valid card appears. Empty-state changes do not reload a page, swap fonts or create a replacement text control. Occupied cards retain the existing font calibration, bounded snapshots, session fences, focus preservation and native fallback.

All 81 native transfusion chrome textures return byte-for-byte to their original pre-Dusk values. The baked window reflection and CSS backdrop capability are removed. React uses the corresponding original flat charcoal fills and borders, including the selected piggyback border. Rounded corners remain. There is no glass imitation, blur, decorative animation or camera/world effect.

The main bag icon is a physically square area, capped by 62% of row height or 0.052 safeZoneH, centered on the same occupied caption region. It is independent of the number of caption lines. Native and React use the same formula. This enlarges the actual bag silhouette, especially in inventory rows that previously squeezed it to one line of text. Titles, details, status and progress track retain one shared left edge; graduation and thermal right edges remain bounded by the card. Original medical art is not edited.

Stop Transfusion and Bag Actions share the existing top action row as equal-width controls with the established gap. Stop's authored width matches its runtime width to avoid a width jump on opening. Prime/Flush retains its lower row and existing handler. The remaining workflow and screen layout are retained.

## Prepared-infusion piggyback

The prepared-list filter explicitly excluded propofol bottles, and both provider and patient-owner gates rejected their carrier type. B300 admits a genuine prepared propofol bottle as a secondary on a saline primary. Ordinary prepared saline medication infusions remain supported. Blood/Y-set/FBTK and incompatible medication-primary restrictions remain; this does not make every drug compatible with every fluid.

The shared carrier validator runs in the prepared picker, before provider reservation, and again on the patient owner before physical carrier creation. A propofol secondary must retain its own dedicated ACME_Propofol carrier, 50 mL, 500 mg, original set ID, matching action/item, bottle marker and single unchanged component. It is not converted into saline, diluted, or mixed with another medication. Malformed legacy records that claim to be saline while carrying bottle markers/classes or propofol components remain excluded.

Existing request fingerprints, epochs, access identity, primary UID, inventory ledger certificate/escrow, replay detection, physical carrier proof, rollback and ACK settlement remain. Failed native creation returns the exact prepared records once. Duplicate requests/ACKs cannot create another bottle or duplicate inventory settlement. Existing secondary priority holds the primary; attachment does not rearm a stopped master line or open a clamp.

## Validation and limits

Focused SQF-VM tests execute the checked-out prepared picker, provider reservation, patient-owner transaction, native carrier factory, medication registration, inventory ACK, rollback, native caption renderer and browser tick. New cases cover genuine propofol, malformed identity/contents/volume, incompatible primaries, alternate native factory return values, repeated requests, duplicate ACKs, failed-carrier refunds, unchanged neighboring bags, preserved list indices and custody, native-only empty captions, top-row geometry, restored PAA bytes and retained IV/IO flags.

The root suite has 690 passing cases. The client suite has 43 passing cases. Strict HEMTT validates 2,140 SQFs, 15 stringtables and 22 configs; native-owner audit reports zero violations. Compiled browser checks cover four pane sizes, font readiness, 25 repeated volume updates per size, stable nodes/focus/font, geometry changes, native input routes, empty browser output and failure fallback. Scratch-only captures use the original ACE saline icon from the supplied source archive; these are browser captures, not Arma screenshots.

ACE menu/actions, original IV/IO art and the existing thin outlines, flags and site dots are unchanged. The only circulation UI source change is the authored Stop button width; its handler is unchanged. B300 does not change medical calculations, medication dosing or networking protocol. Experimental React remains OFF by default.

Arma cannot run in this container. Native font rasterization, input, rendering at actual UI scales, repeated empty/occupied transitions, live piggyback flow and dedicated-server acceptance still need in-game verification. Container builds omit Arma Tools model/animation binarization; the Windows helper runs native hemtt release. Close Arma before deployment and use the complete matching build/key on server, clients and HCs. Retain the persistence profile/adapter; avoid duplicate standalone DD1380.
