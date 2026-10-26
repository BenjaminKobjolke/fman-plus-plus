; Call fman's scripting API from AutoHotkey v2.
;
; Hotkeys:
;   Ctrl+Alt+S  show fman's state (panes, cursor, selection)
;   Ctrl+Alt+D  move the cursor down in the active pane
;   Ctrl+Alt+W  open C:\Windows in the active pane
;   Ctrl+Alt+E  open the folder of the active Explorer window in fman
;
; Responses are shown as raw JSON; AutoHotkey has no built-in JSON parser.
#Requires AutoHotkey v2.0
#SingleInstance Force

API_URL := EnvGet("FMAN_API_URL") || "http://127.0.0.1:47447"
TOKEN_FILE := EnvGet("APPDATA") "\fman\Local\ScriptingApiToken.txt"

^!s:: MsgBox(FmanCall("GET", "/v1/state"), "fman state")
^!d:: FmanCommand("move_cursor_down")
^!w:: FmanOpen("C:\Windows")
^!e:: {
    hwnd := WinActive("ahk_class CabinetWClass")
    if !hwnd
        return
    for window in ComObject("Shell.Application").Windows {
        if window.HWND = hwnd {
            FmanOpen(window.Document.Folder.Self.Path)
            return
        }
    }
}

; Runs an fman command. ArgsJson is a JSON object string, e.g. '{"url": "file://C:/"}'.
FmanCommand(name, argsJson := "{}") {
    return FmanCall("POST", "/v1/command", '{"name": "' name '", "args": ' argsJson '}')
}

FmanOpen(folder) {
    ; fman URLs use forward slashes; escape quotes so the path stays valid JSON.
    url := "file://" StrReplace(StrReplace(folder, "\", "/"), '"', '\"')
    return FmanCommand("open_directory", '{"url": "' url '"}')
}

FmanCall(method, path, body := "") {
    global API_URL, TOKEN_FILE
    if !FileExist(TOKEN_FILE) {
        MsgBox("No token file at " TOKEN_FILE ".`nRun 'Toggle scripting API' in fman first.", "fman", "Icon!")
        return ""
    }
    token := Trim(FileRead(TOKEN_FILE, "UTF-8"), " `t`r`n")
    http := ComObject("WinHttp.WinHttpRequest.5.1")
    try {
        http.Open(method, API_URL path, false)
        http.SetRequestHeader("Authorization", "Bearer " token)
        if (body != "") {
            http.SetRequestHeader("Content-Type", "application/json; charset=utf-8")
            http.Send(body)
        } else {
            http.Send()
        }
    } catch as error {
        MsgBox("Cannot reach fman at " API_URL ".`n" error.Message, "fman", "Icon!")
        return ""
    }
    if (http.Status != 200) {
        MsgBox("HTTP " http.Status ": " http.ResponseText, "fman", "Icon!")
        return ""
    }
    return http.ResponseText
}
