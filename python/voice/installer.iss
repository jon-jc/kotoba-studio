[Setup]
AppId={{62638D33-46D2-498E-A5D7-DC3434020298}
AppName=Kotoba Studio
AppVersion=0.12.5
AppPublisher=Kotoba Studio
AppPublisherURL=https://github.com/jon-jc/kotoba-studio
DefaultDirName={localappdata}\Programs\Kotoba Studio
DefaultGroupName=Kotoba Studio
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename=Kotoba-Studio-0.12.5-Setup
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\kotoba.ico
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
Name: "{group}\Kotoba Studio"; Filename: "{app}\Kotoba.exe"; IconFilename: "{app}\_internal\assets\kotoba.ico"; AppUserModelID: "KotobaStudio.Desktop"
Name: "{autodesktop}\Kotoba Studio"; Filename: "{app}\Kotoba.exe"; IconFilename: "{app}\_internal\assets\kotoba.ico"; AppUserModelID: "KotobaStudio.Desktop"; Tasks: desktopicon

[Run]
Filename: "{app}\Kotoba.exe"; Description: "Launch Kotoba Studio"; Flags: nowait postinstall skipifsilent
