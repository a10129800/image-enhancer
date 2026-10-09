Option Explicit
Dim WshShell, fso, currentDir, folder, f

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentDir

' 1. 自動整理目錄結構（無損重命名）
If fso.FolderExists(currentDir & "\bin") And Not fso.FolderExists(currentDir & "\core") Then
    fso.MoveFolder currentDir & "\bin", currentDir & "\core"
End If
If fso.FolderExists(currentDir & "\dist") And Not fso.FolderExists(currentDir & "\release") Then
    fso.MoveFolder currentDir & "\dist", currentDir & "\release"
End If
If fso.FolderExists(currentDir & "\samples") And Not fso.FolderExists(currentDir & "\assets\samples") Then
    fso.MoveFolder currentDir & "\samples", currentDir & "\assets\samples"
End If
If fso.FolderExists(currentDir & "\docs") And Not fso.FolderExists(currentDir & "\assets\docs") Then
    fso.MoveFolder currentDir & "\docs", currentDir & "\assets\docs"
End If

' 2. 清理根目錄舊啟動檔案
If fso.FileExists(currentDir & "\run_enhance.bat") Then
    fso.DeleteFile currentDir & "\run_enhance.bat", True
End If
If fso.FileExists(currentDir & "\git_push.bat") Then
    fso.DeleteFile currentDir & "\git_push.bat", True
End If

' 3. 動態清理根目錄 .exe，並對工作區與輔助設定設定隱藏屬性（避開中文字元編碼問題）
Set folder = fso.GetFolder(currentDir)
For Each f In folder.Files
    Dim ext, fname
    ext = LCase(fso.GetExtensionName(f.Name))
    fname = LCase(f.Name)
    
    If ext = "exe" Then
        fso.DeleteFile f.Path, True
    ElseIf ext = "code-workspace" Or fname = "agents.md" Or fname = "license" Or fname = "requirements.txt" Then
        f.Attributes = f.Attributes Or 2 ' 加上 Hidden 隱藏屬性
    End If
Next

' 4. 靜音啟動 Python GUI (0 代表完全隱藏黑框命令提示字元視窗)
WshShell.Run "pythonw """ & currentDir & "\src\gui.py""", 0, False
