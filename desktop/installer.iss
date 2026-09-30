[Setup]
AppName=pobieralnik.lol
AppVersion=1.0.0
DefaultDirName={autopf}\pobieralnik
DefaultGroupName=pobieralnik.lol
OutputDir=installer
OutputBaseFilename=pobieralnik-lol-Setup-1.0.0
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
PrivilegesRequired=lowest

[Files]
Source: "dist\pobieralnik\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\pobieralnik.lol"; Filename: "{app}\pobieralnik.exe"
Name: "{autodesktop}\pobieralnik.lol"; Filename: "{app}\pobieralnik.exe"

[Run]
Filename: "{app}\pobieralnik.exe"; Description: "Uruchom pobieralnik.lol"; Flags: postinstall nowait skipifsilent
