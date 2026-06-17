Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
appPath = fso.GetParentFolderName(WScript.ScriptFullName) & "\app.py"
' 用完整路径调用 pythonw，确保不依赖 PATH
' 窗口样式 1 = 正常激活显示（之前 0=隐藏 会导致 PySide6 窗口无法获取焦点）
shell.Run """E:\Python312\pythonw.exe"" """ & appPath & """", 1, False
