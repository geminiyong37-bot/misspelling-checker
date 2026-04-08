[Setup]
AppName=AI 문서 맞춤법 검사기
AppVersion=2.0.0
DefaultDirName={autopf}\AI_Word_Speller
DefaultGroupName=AI 문서 맞춤법 검사기
OutputBaseFilename=AI_Word_Speller_Setup
SetupIconFile=assets\app-icon.ico
UninstallDisplayIcon={app}\MisspellingChecker.exe
Compression=lzma
SolidCompression=yes

[Files]
Source: "Output\_staging\MisspellingChecker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\app-icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AI 문서 맞춤법 검사기"; Filename: "{app}\MisspellingChecker.exe"; IconFilename: "{app}\app-icon.ico"
Name: "{autodesktop}\AI 문서 맞춤법 검사기"; Filename: "{app}\MisspellingChecker.exe"; Tasks: desktopicon; IconFilename: "{app}\app-icon.ico"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Run]
Filename: "{app}\MisspellingChecker.exe"; Description: "{cm:LaunchProgram,AI 문서 맞춤법 검사기}"; Flags: nowait postinstall skipifsilent

[Code]
var
  APIKeyPage: TInputQueryWizardPage;

procedure OnAPIKeyChange(Sender: TObject);
begin
  WizardForm.NextButton.Enabled := Trim(APIKeyPage.Values[0]) <> '';
end;

procedure InitializeWizard;
begin
  APIKeyPage := CreateInputQueryPage(wpWelcome,
    'API 키 설정', 'Gemini, OpenAI 또는 Anthropic API 중 하나를 입력해 주세요.',
    'API 키를 입력해 주세요.');
  APIKeyPage.Add('API 키:', False);
  APIKeyPage.Edits[0].OnChange := @OnAPIKeyChange;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = APIKeyPage.ID then
    WizardForm.NextButton.Enabled := Trim(APIKeyPage.Values[0]) <> '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigPath: String;
  APIKey: String;
  Provider: String;
  JsonContent: String;
begin
  if CurStep = ssPostInstall then
  begin
    APIKey := Trim(APIKeyPage.Values[0]);
    if APIKey <> '' then
    begin
      // 공급자 감지 로직
      if Pos('sk-ant-', APIKey) = 1 then
        Provider := 'anthropic'
      else if Pos('sk-', APIKey) = 1 then
        Provider := 'openai'
      else
        Provider := 'gemini';

      ConfigPath := ExpandConstant('{%USERPROFILE}\.misspelling_checker_config.json');
      JsonContent := '{' + #13#10 +
                     '  "provider": "' + Provider + '",' + #13#10 +
                     '  "keys": {' + #13#10 +
                     '    "' + Provider + '": "' + APIKey + '"' + #13#10 +
                     '  }' + #13#10 +
                     '}';
      SaveStringToFile(ConfigPath, JsonContent, False);
    end;
  end;
end;
