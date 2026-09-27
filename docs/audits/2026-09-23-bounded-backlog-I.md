# Bounded I: stored-syringe editor autofocus ownership

Parent: `29ed91cf1239b6bccb6c946d2b177b007cdd7318` (G-H).

## Runtime defect and narrow correction

The delayed tag-editor callback looked up whichever draw display was current when it fired. It could focus a reopened display, another provider's editor, or a different selected syringe; returning to a new editor on the same display also let the older callback act.

Open now captures the exact display, provider, stable syringe ID and a display-local editor generation. The callback requires that same display/provider/body page/editor generation and selected record. Done invalidates its pending focus before committing the tag. No new PFH, network traffic or timer is added. The existing 0.14-second delay, native-size editor, None/color initial-focus choice, 0.12-second presentation transitions, normal tag commits and record contents remain unchanged.

H259 is reconciled separately: its obsolete source assumptions required the old rectangle variable and focus variable. It now checks the stored syringe's own native rectangle and color-aware focus contract; its function identity is unchanged. The original index moves 124 to 123.

## Evidence boundaries

Twenty-three cases execute actual Open/Done and identity functions, or mutation-check the native-editor contract. On unchanged G-H runtime, eight cases fail and fifteen pass. All 23 pass with the correction. Cases cover close/reopen, changed provider or page, selection change/removal/reordering, Done/reentry, repeated opens, empty stores, normal tagged/untagged focus and saved-tag contents. Object/control primitives are explicit namespace/ID fixtures. These tests do not render UI, test real scheduling/IME, certify general modal ownership, or change medication administration. Manual focus changes within an otherwise still-current 0.14-second session are outside this correction. No live Arma or stable-release approval.
