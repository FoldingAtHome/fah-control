## v7.4.15
 - Removed crashing themes: Evil-Mac & Outcrop.
 - Ignore invalid UTF-8 characters in log file.

## v7.4.13
 - Attempt to fix install on Ubuntu 16.04.

## v7.4.1
 - Removed trigger-save command, no longer necessary.

## v7.3.12
 - Reordered toolbar.
 - Move Viewer button to right of power bar.  #304
 - Changed FAHControl title bar to say Advanced Control.  #982
 - Right clicking on slot brings up correct slot menu.  Mentioned in #1060
 - Removed Configure->Advanced->Optimizations.  #1069

## v7.3.11
 - Split power slider to power + fold/pause/finish.
 - Added "on idle" & "always on" to slot menu.
 - Removed Percent CPU usage, not currently support by any cores.  #1056

## v7.3.7
 - Restored ctrl-a and ctrl-c functionality in log view. #1002

## v7.3.6
 - UI layout adjustments.

## v7.3.5
 - Put Viewer button back on toolbar.
 - Added additional tooltips.

## v7.3.4
 - Trigger save on folding power change.
 - Fix folding power reset problem on options save.

## v7.3.3
 - Fixed OK/Cancel buttons off bottom of screen at some resolutions. #904
 - Don't show selected client status in add client dialog.
 - Added folding power slider.
 - Removed client Fold/Pause/Finish/View buttons, use slot popup menu.
 - The links for project, WS & CS can extend to the edge of the window. #977
 - Changed Quit to Exit.
 - Added --exit command line option.

## v7.3.2
 - Center About box text.

## v7.3.0
 - Updated copyright dates.
 - Restored 'Work Unit' pane to 'Status' tab.
 - Fixed Missing, hidden, and vanishing text in Ubuntu 12.04.  #898
 - Remote system remains "Updating".  #906

## v7.2.14
 - Removed local client startup functionality.
 - Flipped 'Folding Slots' / 'Queue' orientation.  #951
 - Always list local client first. #655

## v7.2.13
 - Merged SMP and Uni slot types to CPU.
 - Removed novice/advanced/expert modes. #852
 - Removed project descriptions.
 - Enforce min GPU and CPU usage of 10%.
 - Removed all systray functionality. #217, #565, #487, #321
 - Disable search on tree views. #953
 - OSX: Don't quit app when window is closed. #606

## v7.2.12
 - Autostart client by default, if it's not already running.

## v7.2.11
 - Hide 'Folding Slot Status' column in expert/advanced.
 - Show status colors even when row is selected.

## v7.2.10
 - Fixed OSX: Copy/Paste not working.  #588
 - Fixed OSX: Copy the log clears the log window.  #601
 - Removed show project pane in advanced preference.
 - Moved WU info to a separate popup dialog.
 - Display Work Queue to right of Folding Slots in advanced/expert.
 - Changed 'Stats' and 'PPD' to 'Points Per Day'.
 - Hide PCRG Work Queue column in novice mode.
 - Don't show RCG in 'About Project' line.
 - Display slot status with reason in Work Queue. #743
 - Check if client is configured and popup dialog if not.

## v7.2.9
 - Fixed OSX: gtk 2 is broken on 10.7.  #793

## v7.2.8
 - Pass remote passwords to viewer.

## v7.2.7
 - Updated view modes.

## v7.2.0
 - Fix " escaping for options sent to client.
 - Only allow alpha numeric and puntuation in user name.
 - Updates for OSX 10.7 (calxalot)

## v7.1.52
 - Select 'Identity' tab by default.  #851

## v7.1.50
 - Z in the Zulu time display was still partially cut off.  #839

## v7.1.49
 - Z in the Zulu time display was partially cut off.  #839
 - Build Linux version on Debian testing for python 2.7 support.  #763

## v7.1.48
 - Added some tooltips.
 - Fixed windows default theme.

## v7.1.47
 - Added UTC time to status bar.  #647
 - Fixed missing system info.  #834
 - Fixed false 'Inactive' systray message.  #526
 - Display total PPD for all clients and all slots.  #408
 - Removed Unit ID from Work Unit status.

## v7.1.46
 - Default local client autostart to false.
 - Integrated caxalot's OSX install script changes.
 - Fixed themes for Linux.  #819
 - Hide theme prefernece in OSX, causes crashes in current gtk.
 - Really fix, Increment number of CPUs by 1 instead of 2.  #804

## v7.1.45
 - Fixed OSX icons file.  (calxalot)
 - Increment number of CPUs by 1 instead of 2.  #804

## v7.1.44
 - Fixed floating buttons on log tab.  #789
 - Changed 'Queue ID' -> 'Work Queue ID'.  #790
 - Changed '1' -> '01' in folding slot id. #790

## v7.1.43
 - Don't flash 'Offline' status while trying to connect.
 - Cleaned up some Windows related connection issues.
 - Don't timeout connection because FAHControl is busy.
 - Updated copyright dates.
 - Restore 'Follow' log check box.  #758
 - Don't refilter log unless filters have actually changed.

## v7.1.41
 - Changed copyright line in about box. #771
 - Added disconnect error messages.
 - Improved loading of large log files.
 - Swapped 'Severity' combo for 'Errors & Warnings' check box.

## v7.1.40
 - Fixed missing system info. #759
 - Fixed debian package problem.

## v7.1.39
 - Fixed deb install location problems. #718
 - Fixed shebang line. #719
 - Fixed client status message updating when paused/unpaused. #526
 - Fixed 'fah' module location problems.  #669
 - Reduced tool bar font size so it fits the default window size.
