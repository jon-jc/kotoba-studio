[Setup]
AppId={{62638D33-46D2-498E-A5D7-DC3434020298}
AppName=Kotoba Studio
AppVersion=0.3.0
AppPublisher=Kotoba Studio
AppPublisherURL=https://github.com/jon-jc/japan-ai-harness
DefaultDirName={localappdata}\Programs\Kotoba Studio
DefaultGroupName=Kotoba Studio
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename=Kotoba-Studio-0.3.0-Setup
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Kotoba.exe
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Files]
Source: "dist\Kotoba\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Icons]
Name: "{group}\Kotoba Studio"; Filename: "{app}\Kotoba.exe"
Name: "{autodesktop}\Kotoba Studio"; Filename: "{app}\Kotoba.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Kotoba.exe"; Description: "Launch Kotoba Studio"; Flags: nowait postinstall skipifsilent
