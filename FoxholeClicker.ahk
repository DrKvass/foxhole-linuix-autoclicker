#Requires AutoHotkey v1.1.33+
#NoEnv
#NoTrayIcon
#SingleInstance Ignore
#Persistent
SetBatchLines, -1
SetControlDelay, -1
CoordMode, Mouse, Screen
SetWorkingDir, %A_ScriptDir%
; The Linux launcher supplies the current user's state path through Wine Z:.
; Never guess another user's home or depend on the installation directory.
if (!A_Args.Length() || A_Args[1] = "") {
    FileAppend, Missing shared-state path. Start with launch.sh in the package folder.`n, *
    ExitApp, 2
}
StateDir := A_Args[1]
FileCreateDir, %StateDir%
Config := A_ScriptDir "\config.ini"
Prefs := StateDir "\settings.ini"
StateFile := StateDir "\state"
StatusFile := StateDir "\worker-status"
IniRead, AllowedExe, %Config%, Target, ProcessName, War-Win64-Shipping.exe
IniRead, Interval, %Prefs%, Settings, Interval, 500
if (!RegExMatch(Interval, "^\d+$") || Interval < 1 || Interval > 60000)
    Interval := 500
IniRead, DisplayCPS, %Prefs%, Settings, DisplayCPS, 0
IniRead, RememberPoint, %Prefs%, Settings, Remember, 0
IniRead, ShiftClick, %Prefs%, Settings, ShiftClick, 0
IniRead, SavedX, %Prefs%, Point, X, -1
IniRead, SavedY, %Prefs%, Point, Y, -1
TargetHwnd := 0
Running := false
Selecting := false
ReusePoint := false
FileRead, LastCommand, %StateFile%
OnExit, Cleanup
; Bind to this game process, independently of selected target and click state.
; Holding a handle prevents a restarted game or recycled PID from keeping us alive.
Process, Exist, %AllowedExe%
GamePID := ErrorLevel
GameHandle := GamePID ? DllCall("OpenProcess", "UInt", 0x100000, "Int", 0, "UInt", GamePID, "Ptr") : 0
if (!GameHandle) {
    ExitReason := "Foxhole is not running. Start the game first."
    ExitApp
}
SetTimer, CheckGame, 500
SetStatus("Paused. Select a Foxhole target first.")
SetTimer, CheckCommand, 100
SetTimer, Heartbeat, 500
return

; Limit the built-in shortcut to the game. Native desktop shortcuts can send TOGGLE.
#If WinActive("ahk_exe " AllowedExe)
!Backspace::
ToggleAction()
; Avoid key-repeat toggling repeatedly while Backspace is held.
Critical, Off
KeyWait, Backspace
return
#If

SelectTarget:
BeginSelection()
return

PickTarget:
if (!Selecting)
    return
if (GetKeyState("Escape", "P") || A_TickCount - SelectionStarted > 15000) {
    CancelSelection()
    SetStatus("Selection cancelled. Previous target retained.")
    return
}
if (!GetKeyState("LButton", "P")) {
    Released := true
    return
}
if (!Released)
    return
MouseGetPos, mx, my, candidate
candidate := DllCall("GetAncestor", "Ptr", candidate, "UInt", 2, "Ptr")
WinGet, process, ProcessName, ahk_id %candidate%
if (process != AllowedExe) {
    Released := false
    SetStatus("That window is not " AllowedExe ". Click Foxhole or press Esc.")
    return
}
VarSetCapacity(point, 8, 0)
NumPut(mx, point, 0, "Int")
NumPut(my, point, 4, "Int")
if (!DllCall("ScreenToClient", "Ptr", candidate, "Ptr", &point))
    return
x := NumGet(point, 0, "Int"), y := NumGet(point, 4, "Int")
if (ReusePoint) {
    if (!RegExMatch(SavedX, "^\d+$") || !RegExMatch(SavedY, "^\d+$")) {
        CancelSelection()
        SetStatus("No saved point. Clear Use saved coordinates and select again.")
        return
    }
    x := SavedX, y := SavedY
}
if (!PointFits(candidate, x, y)) {
    CancelSelection()
    SetStatus("Point is outside the game client area. Select again.")
    return
}
TargetHwnd := candidate
WinGet, TargetPID, PID, ahk_id %TargetHwnd%
ClickX := x, ClickY := y
CancelSelection()
SaveSettings()
SetStatus("Ready at " ClickX ", " ClickY ". Press Alt+Backspace or Start.")
return

CheckCommand:
FileRead, command, %StateFile%
if (ErrorLevel || command = LastCommand)
    return
LastCommand := command
lines := StrSplit(command, "`n", "`r")
verb := Trim(lines[1])
; Native controller includes interval and point preferences; shell helpers need only a verb.
if (verb = "RUN" || verb = "SELECT" || verb = "CONFIG" || verb = "TOGGLE") {
    if (lines.Length() >= 5) {
        value := Trim(lines[3])
        if (!RegExMatch(value, "^\d+$") || value < 1 || value > 60000) {
            SetStatus("Interval must be an integer from 1 to 60000 ms.")
            return
        }
        Interval := value
        RememberPoint := (Trim(lines[4]) = "1")
        ReusePoint := (Trim(lines[5]) = "1")
        if (lines.Length() >= 6)
            ShiftClick := (Trim(lines[6]) = "1")
        if (lines.Length() >= 7)
            DisplayCPS := (Trim(lines[7]) = "1")
        SaveSettings()
        if (Running)
            StartClicking()
    }
}
if (verb = "TOGGLE")
    ToggleAction()
else if (verb = "RUN")
    StartClicking()
else if (verb = "SELECT") {
    Gosub, SelectTarget
} else if (verb = "STOP" || verb = "PAUSE") {
    CancelSelection()
    PauseClicking("Stopped. Target retained.")
} else if (verb = "EXIT") {
    ExitApp
}
return

ClickTick:
Critical
if (!GameAlive()) {
    ExitReason := "Foxhole closed. Clicker exited automatically."
    ExitApp
}
if (!Running)
    return
if (!TargetValid()) {
    TargetHwnd := 0
    PauseClicking("Target closed, changed or point out of bounds. Select again.")
    return
}
WinGet, minimized, MinMax, ahk_id %TargetHwnd%
if (minimized = -1) {
    PauseClicking("Foxhole is minimized. Restore it, then Start.")
    return
}
try {
    if (ShiftClick) {
        if (!ShiftLeftClick(TargetHwnd, ClickX, ClickY))
            PauseClicking("Shift + click could not be sent. Reselect the target.")
    } else {
        ControlClick, x%ClickX% y%ClickY%, ahk_id %TargetHwnd%,, Left, 1, NA Pos
        if (ErrorLevel)
            PauseClicking("ControlClick failed. Reselect the target.")
    }
} catch e {
    PauseClicking("ControlClick error. Reselect the target.")
}
return

CheckGame:
if (!GameAlive()) {
    ExitReason := "Foxhole closed. Clicker exited automatically."
    ExitApp
}
return

Heartbeat:
WriteStatus()
return

Cleanup:
Running := false
Selecting := false
SetTimer, ClickTick, Off
SetTimer, Heartbeat, Off
SetTimer, CheckGame, Off
if (GameHandle) {
    DllCall("CloseHandle", "Ptr", GameHandle)
    GameHandle := 0
}
WorkerExited := true
SaveSettings()
SetStatus(ExitReason ? ExitReason : "Worker exited.")
ExitApp

StartClicking() {
    global
    if (Selecting) {
        SetStatus("Finish target selection before starting.")
        return
    }
    if (!TargetValid()) {
        PauseClicking("No valid target. Use Set Target first.")
        return
    }
    Running := true
    SetTimer, ClickTick, %Interval%
    SetStatus((ShiftClick ? "Shift + left click" : "Left click") (DisplayCPS ? " at " Round(1000 / Interval, 3) " clicks/s" : " every " Interval " ms") " (" ClickX ", " ClickY ").")
}
PauseClicking(message) {
    global Running
    Running := false
    SetTimer, ClickTick, Off
    SetStatus(message)
}
CancelSelection() {
    global Selecting
    Selecting := false
    SetTimer, PickTarget, Off
}
TargetValid() {
    global
    if (!TargetHwnd || !DllCall("IsWindow", "Ptr", TargetHwnd))
        return false
    WinGet, pid, PID, ahk_id %TargetHwnd%
    WinGet, exe, ProcessName, ahk_id %TargetHwnd%
    return (pid = TargetPID && exe = AllowedExe && PointFits(TargetHwnd, ClickX, ClickY))
}
PointFits(hwnd, x, y) {
    VarSetCapacity(rect, 16, 0)
    if (!DllCall("GetClientRect", "Ptr", hwnd, "Ptr", &rect))
        return false
    return x >= 0 && y >= 0 && x < NumGet(rect, 8, "Int") && y < NumGet(rect, 12, "Int")
}
SetStatus(message) {
    global StatusMessage
    StatusMessage := message
    WriteStatus()
}
WriteStatus() {
    global
    Critical
    text := "exited=" (WorkerExited ? 1 : 0) "`nrunning=" (Running ? 1 : 0) "`nselecting=" (Selecting ? 1 : 0) "`nmessage=" StatusMessage "`n"
    tmp := StatusFile ".tmp"
    f := FileOpen(tmp, "w", "UTF-8-RAW")
    if (IsObject(f)) {
        f.Write(text)
        f.Close()
        FileMove, %tmp%, %StatusFile%, 1
    }
}
SaveSettings() {
    global
    IniWrite, %DisplayCPS%, %Prefs%, Settings, DisplayCPS
    IniWrite, %ShiftClick%, %Prefs%, Settings, ShiftClick
    IniWrite, %Interval%, %Prefs%, Settings, Interval
    IniWrite, %RememberPoint%, %Prefs%, Settings, Remember
    if (RememberPoint && TargetHwnd) {
        SavedX := ClickX, SavedY := ClickY
        IniWrite, %SavedX%, %Prefs%, Point, X
        IniWrite, %SavedY%, %Prefs%, Point, Y
    } else if (!RememberPoint) {
        IniDelete, %Prefs%, Point
        SavedX := -1, SavedY := -1
    }
}

; Send the complete modified click only to the selected HWND. No global Send
; or keyboard injection: native desktop typing is not given a synthetic Shift.
; Some games query hardware modifier state instead and may ignore this mode.
ShiftLeftClick(hwnd, x, y) {
    pos := (x & 0xFFFF) | ((y & 0xFFFF) << 16)
    if (!PostTarget(hwnd, 0x100, 0x10, 0x002A0001)) ; WM_KEYDOWN, VK_SHIFT
        return false
    downOK := false
    upOK := false
    shiftUpOK := false
    try {
        downOK := PostTarget(hwnd, 0x201, 0x0005, pos) ; LMB down + MK_SHIFT
    } finally {
        upOK := PostTarget(hwnd, 0x202, 0x0004, pos)   ; LMB up, Shift still held
        shiftUpOK := PostTarget(hwnd, 0x101, 0x10, 0xC02A0001)
    }
    return downOK && upOK && shiftUpOK
}
PostTarget(hwnd, message, wParam, lParam) {
    return DllCall("PostMessageW", "Ptr", hwnd, "UInt", message, "UPtr", wParam, "Ptr", lParam)
}

GameAlive() {
    global GameHandle
    ; WAIT_TIMEOUT (258) means this process is still alive. Exit on failure too.
    return GameHandle && DllCall("WaitForSingleObject", "Ptr", GameHandle, "UInt", 0, "UInt") = 258
}

ToggleAction() {
    global
    ; Each branch returns: selection never starts clicking as a side effect.
    if (Selecting)
        return
    if (!TargetValid()) {
        TargetHwnd := 0
        BeginSelection()
        return
    }
    if (!Running) {
        StartClicking()
        return
    }
    PauseClicking("Paused by Alt+Backspace. Target retained.")
}
BeginSelection() {
    global
    Selecting := true
    Released := false
    SelectionStarted := A_TickCount
    PauseClicking("Click a point in Foxhole (15 seconds). Esc cancels.")
    SetTimer, PickTarget, 20
}
