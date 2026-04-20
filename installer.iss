[Setup]
AppName=AI 문서 맞춤법 검사기
AppVersion=2.0.0
DefaultDirName={autopf}\AI_Word_Speller
DefaultGroupName=AI 문서 맞춤법 검사기
OutputDir=Output
OutputBaseFilename=AI_Word_Speller_Setup
SetupIconFile=assets\app-icon.ico
UninstallDisplayIcon={app}\MisspellingChecker.exe
Compression=lzma
SolidCompression=yes

[Files]
Source: "Output\_staging\MisspellingChecker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "node_modules\typescript\*, node_modules\tsup\*, node_modules\tsx\*, *.map, *.md, demo.gif, LICENSE, NOTICE"
Source: "Output\_staging\verify_key.exe"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall
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
  ValidationLabel: TLabel;

procedure OnAPIKeyChange(Sender: TObject);
begin
  WizardForm.NextButton.Enabled := Trim(APIKeyPage.Values[0]) <> '';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  APIKey: String;
  ResultCode: Integer;
begin
  Result := True;
  if CurPageID = APIKeyPage.ID then
  begin
    APIKey := Trim(APIKeyPage.Values[0]);
    if APIKey <> '' then
    begin
      ExtractTemporaryFile('verify_key.exe');
      ValidationLabel.Visible := True;
      ValidationLabel.Caption := 'API 키 유효성 검사 중. 잠시만 기다려 주세요...';
      WizardForm.Refresh;
      Sleep(100); // 윈도우 이벤트 큐가 처리될 수 있도록 아주 잠깐 대기
      WizardForm.Refresh;
      
      // Run verify_key.exe <api_key>
      if Exec(ExpandConstant('{tmp}\verify_key.exe'), '"' + APIKey + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      begin
        case ResultCode of
          0: Result := True;
          2: begin
               MsgBox('유효하지 않은 API 키입니다. 다시 확인해 주세요.', mbError, MB_OK);
               Result := False;
             end;
          3: begin
               MsgBox('인터넷 연결 오류 또는 서버 응답 문제로 키를 확인할 수 없습니다.' + #13#10 + '인터넷 상태를 확인해 주세요.', mbError, MB_OK);
               Result := False;
             end;
          else
             begin
               MsgBox('검증 중 알 수 없는 오류가 발생했습니다. (에러 코드: ' + IntToStr(ResultCode) + ')', mbError, MB_OK);
               Result := False;
             end;
        end;
      end
      else
      begin
        MsgBox('검증 도구를 실행할 수 없습니다. 다시 시도해 주세요.', mbError, MB_OK);
        Result := False;
      end;
      
      ValidationLabel.Visible := False;
    end;
  end;
end;

procedure InitializeWizard;
begin
  APIKeyPage := CreateInputQueryPage(wpWelcome,
    'API 키 설정', 
    '',
    'API 키를 입력해 주세요.' + #13#10#13#10 +
    '- Gemini, OpenAI, Anthropic API 키 중 하나를 입력해 주세요.' + #13#10 +
    '- Next 버튼을 누르면 유효성 검증을 위해 인터넷 연결이 필요하며 수 초 정도 소요될 수 있습니다.' + #13#10#13#10);
  APIKeyPage.Add('API 키:', False);
  APIKeyPage.Edits[0].OnChange := @OnAPIKeyChange;

  ValidationLabel := TLabel.Create(WizardForm);
  ValidationLabel.Parent := APIKeyPage.Surface;
  ValidationLabel.Caption := '';
  ValidationLabel.Top := APIKeyPage.Edits[0].Top + APIKeyPage.Edits[0].Height + 15;
  ValidationLabel.Left := APIKeyPage.Edits[0].Left;
  ValidationLabel.Width := APIKeyPage.SurfaceWidth - (ValidationLabel.Left * 2);
  ValidationLabel.Font.Color := clBlue;
  ValidationLabel.Visible := False;
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
