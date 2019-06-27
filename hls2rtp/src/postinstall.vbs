
if IsObject(Session) then
    targetdir=Session.Property("CustomActionData")
else
    targetdir="c:\hls2rtp\"
end if
Set fso = CreateObject("Scripting.FileSystemObject")
    fso.CopyFile targetdir+"patches\gstmpegtsdemux.dll", targetdir+"lib\gstreamer-1.0\", True
    fso.CopyFile targetdir+"patches\gstmpegtsdemux.pdb", targetdir+"lib\gstreamer-1.0\", True
    fso.CopyFile targetdir+"patches\gstrtp.dll", targetdir+"lib\gstreamer-1.0\", True
    fso.CopyFile targetdir+"patches\gstrtp.pdb", targetdir+"lib\gstreamer-1.0\", True
    fso.CopyFile targetdir+"patches\gstmpegts-1.0-0.dll", targetdir+"bin\", True
    fso.CopyFile targetdir+"patches\gstmpegts-1.0-0.dll", targetdir+"bin\", True
Set fso = Nothing

Set WshShell = CreateObject("WScript.Shell")
Set objEnv = WshShell.Environment("System")
oldSystemPath = objEnv("PATH")
If InStr(path,targetdir+"bin")=0 Then
    newSystemPath = oldSystemPath & ";" & targetdir+"bin"
    objEnv("PATH") = newSystemPath
end if
