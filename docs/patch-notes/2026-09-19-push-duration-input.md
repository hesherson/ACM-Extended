# ACM Extended 1.2.2: medication push duration input

## Changes

- Replaced the generic seconds control with a dedicated native edit control that explicitly permits modification and accepts up to three characters.
- Clicking the field gives it keyboard focus. Entering the field stops any held carousel movement. Both carousel key handlers yield to every text edit control, including the seconds field.
- Kept the gray recommended duration on a separate noninteractive label. Focusing or leaving the field no longer writes placeholder text into the value being edited.
- Preserved the typed value and caret during routine refreshes. Edit geometry, visibility and enable state are changed only when required.
- Continued Push validation while typing, so correcting 0 or an out of range value can enable Push without first leaving the field.
- Bounded carousel hover and click regions above the duration row, including the initial site selection. The recommendation is also hidden when leaving the Body Map.

Blank still means 3 seconds in normal and Hardcore medication modes. Explicit durations remain 1–300 seconds. IM administration is unchanged. Version remains 1.2.2 with build metadata 1.2.2.0.

## Validation

The release branch passed 25 focused checks. The development branch passed 36, including its existing drag handle checks. Both passed HEMTT strict diagnostics and complete addon config compilation.

SQF-VM executed the actual input filtering and both duration readers with only native control reads and writes substituted. Cases covered blank input, 1, 3, 30, 120 and 300, rejected values 0 and 301, backspace to blank, and removal of nondigit characters. Valid digits were retained without rewriting the input text. Source checks cover edit configuration, click focus, keyboard exclusions, recommendation separation and carousel bounds.

Two older Narc Box test expectations described the superseded mandatory duration and old plunger guard. Those assertions now check the existing blank default and the current normal push animation guard; no medication physiology or plunger timing changed in this patch.

The Windows package and Arma UI cannot be exercised here. In Arma, select IV/IO access, click Seconds to Push, type 30 using the number row and keypad, use backspace or select all to replace it with 120, then press Push. Confirm the selected duration in both medication modes. Check that blank uses 3 seconds and correcting 0 or 301 makes Push available. Repeat after changing the selected syringe and reopening the menu.

The fix is applied independently to main and dev. The experimental drag handle remains absent from main and present on dev.
