import os
import sys
import threading
import json

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QStandardPaths, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QProgressBar,
    QFileDialog, QMessageBox, QInputDialog, QSizePolicy, QCheckBox, QDialog
)

# Engine modules from misspelling checker
from hwp_parser import parse_with_kordoc
from doc_model import build_doc_from_parse_result
from ai_client import (
    run_ai_check, PROVIDER_GEMINI, PROVIDER_OPENAI, PROVIDER_ANTHROPIC
)
from excel_exporter import export_to_excel

SUPPORTED_EXT = ('.hwp', '.hwpx', '.pdf', '.docx', '.txt', '.doc')
_CONFIG_FILE = os.path.expanduser("~/.misspelling_checker_config.json")
APP_VERSION = "2.0.0"

def resource_path(relative):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative)
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative)

def _detect_provider(api_key: str) -> str:
    if api_key.startswith("sk-ant-"):
        return PROVIDER_ANTHROPIC
    if api_key.startswith("sk-"):
        return PROVIDER_OPENAI
    return PROVIDER_GEMINI

def _load_config() -> dict:
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"provider": PROVIDER_GEMINI, "keys": {}, "show_welcome": True}

def _save_config(config: dict):
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def _apply_config(config: dict):
    provider = config.get("provider", PROVIDER_GEMINI)
    os.environ["TYPO_PROVIDER"] = provider
    os.environ["TYPO_API_KEY"] = config.get("keys", {}).get(provider, "")

# ────────────────────────────────────────────
# Welcome Dialog
# ────────────────────────────────────────────

class WelcomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("안내 및 사용 방법")
        self.setFixedSize(500, 600)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QLabel("사용 방법 안내")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #5D4037;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        text = QLabel("""
            <div style='line-height: 160%; color: #5D4037; font-family: "맑은 고딕";'>
                <p><b>** 오타 찾기에 눈이 아픈 그대들을 위해서 만들었습니다.</b></p>
                
                <p><b>** 사용방법은 간단합니다.</b><br>
                - 파일을 상단 박스 안에 drag&drop 하시면 자동으로 시작합니다.<br>
                - 결과는 엑셀로 출력됩니다.<br>
                - 검사 결과로서 띄어쓰기 오류가 많이 나오는 편인데 피로도를 줄이기 위해서 중요한 오타라고 생각되는 부분을 색깔로 강조 표기하였습니다.</p>

                <p><b>** 보안을 위해서 유료 API를 사용하시기 바랍니다.</b><br>
                - 무료는 AI 학습에 활용되는 경우가 많습니다.<br>
                - OpenAI, Anthropic, Google API가 가능하며 가성비 좋은 모델을 default로 해 놓았기 때문에 토큰(비용) 소모는 크지 않습니다.<br>
                - 갑자기 계속해서 검사 오류가 발생한다면 API 할당량 소진 여부를 확인해 보시기 바랍니다.</p>

                <p><b>** AI는 실수를 합니다.</b><br>
                - 하지만 중요한 오타는 잘 잡아내는 편이니 가끔 나오는 실수는 귀엽게 봐주시면 감사하겠습니다.<br>
                - 사용 중 발견되는 AI의 실수나 오류를 알려주시면 업데이트하는 데 도움이 됩니다.</p>

                <p><b>** 이미지 기반 PDF는 읽기가 안 되기 때문에 오류가 납니다.</b><br>
                - 일시적인 오류가 아니므로 계속 시도해봤자 소용없습니다.<br>
                - 저에게 개인적으로 말씀해 주시면 이미지 PDF 오타 검사 도와드릴 수 있으니 참고 바랍니다.</p>

                <p><b>** AI의 실수나 오류 신고 또는 그 밖의 문의사항은 회계조사부 김성범(053-770-2627)에게 문의해 주시면 감사하겠습니다.</b></p>
            </div>
        """)
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        content_layout.addWidget(text)
        scroll.setWidget(content)

        self.dont_show_cb = QCheckBox("다시는 이 창을 열지 않음")
        self.dont_show_cb.setStyleSheet("color: #8D6E63; font-size: 11px;")

        btn_box = QHBoxLayout()
        confirm_btn = QPushButton("확인")
        confirm_btn.setObjectName("btnPrimary")
        confirm_btn.setFixedWidth(100)
        confirm_btn.clicked.connect(self.accept)
        btn_box.addStretch(1)
        btn_box.addWidget(confirm_btn)
        btn_box.addStretch(1)

        layout.addWidget(header)
        layout.addWidget(scroll)
        layout.addWidget(self.dont_show_cb)
        layout.addLayout(btn_box)
        
        self.setLayout(layout)
        
        # Apply theme colors
        self.setStyleSheet("""
            QDialog { background-color: #FDF9F0; }
            #btnPrimary { background: #C1A062; color: #5D4037; border: none; padding: 8px; border-radius: 8px; font-weight: bold; }
            #btnPrimary:hover { background: #B39250; }
        """)

# ────────────────────────────────────────────
# UI Widgets
# ────────────────────────────────────────────

class DropArea(QFrame):
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropArea")
        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_api_checked", False):
            self._api_checked = True
            
            # Show Welcome popup if needed
            config = _load_config()
            if config.get("show_welcome", True):
                dlg = WelcomeDialog(self.window())
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    if dlg.dont_show_cb.isChecked():
                        config["show_welcome"] = False
                        _save_config(config)
            
            QTimer.singleShot(0, self.window()._ensure_api_key)

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        icon = QLabel("⬇")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setObjectName("dropIcon")
        icon.setFixedWidth(56)
        icon.setFixedHeight(56)

        title = QLabel("여기에 파일을 드래그 & 드롭")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setObjectName("dropTitle")

        hint = QLabel("또는 아래 버튼을 눌러 선택")
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        hint.setObjectName("dropHint")

        formats = QLabel("지원 형식: HWP, HWPX, PDF, TXT, DOC, DOCX")
        formats.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        formats.setObjectName("dropFormats")

        self.btn_pick = QPushButton("파일 선택")
        self.btn_pick.setObjectName("btnPick")

        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(formats)
        layout.addWidget(self.btn_pick, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragging", True)
            self.style().unpolish(self)
            self.style().polish(self)
        else:
            event.ignore()

    def dragLeaveEvent(self, _event):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
        event.acceptProposedAction()
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                paths.append(path)
        if paths:
            self.files_dropped.emit(paths)

class FileItemWidget(QFrame):
    def __init__(self, filename="파일명.hwpx"):
        super().__init__()
        self.setObjectName("fileItem")
        self._build_ui(filename)

    def _build_ui(self, filename):
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(4)
        left.setContentsMargins(0, 0, 0, 0)

        self.full_name = filename
        self.name = QLabel(filename)
        self.name.setObjectName("fileName")
        self.name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.name.setMinimumWidth(80)

        self.status = QLabel("대기 중")
        self.status.setObjectName("fileStatus")

        self.bar = QProgressBar()
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setObjectName("progressBar")
        self.bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        left.addWidget(self.name)
        left.addWidget(self.status)
        left.addWidget(self.bar)

        layout.addLayout(left, stretch=1)
        self.setLayout(layout)
        self.name.setToolTip(self.full_name)
        QTimer.singleShot(0, self._update_elide)

    def _update_elide(self):
        metrics = self.name.fontMetrics()
        width = max(80, self.name.width())
        elided = metrics.elidedText(self.full_name, Qt.TextElideMode.ElideRight, width)
        if self.name.text() != elided:
            self.name.setText(elided)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elide()

    def set_progress(self, value: int):
        self.bar.setValue(value)

    def set_status(self, text: str):
        self.status.setText(text)

# ────────────────────────────────────────────
# Background Worker
# ────────────────────────────────────────────

class CheckWorker(QThread):
    file_progress = pyqtSignal(int, int)
    file_status = pyqtSignal(int, str)
    file_done = pyqtSignal(int, int)
    file_results = pyqtSignal(int, list)
    file_original_path = pyqtSignal(int, str)
    overall_status = pyqtSignal(str)
    finished_all = pyqtSignal()

    def __init__(self, items, parent_window):
        super().__init__()
        self.items = items
        self.parent_window = parent_window
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def run(self):
        total = len(self.items)
        for idx, item in enumerate(self.items, 1):
            if self.cancel_event.is_set():
                break
                
            item_id = item["id"]
            file_path = item["path"]

            self.file_status.emit(item_id, "문서 파싱 중... (kordoc)")
            self.file_progress.emit(item_id, 10)
            self.overall_status.emit(f"[{idx}/{total}] {item['name']} 분석 중...")

            try:
                # 1. 문서 파싱
                raw_result = parse_with_kordoc(file_path)
                if not raw_result:
                    self.file_status.emit(item_id, "❌ KORDOC 파싱 실패")
                    self.file_progress.emit(item_id, 0)
                    continue

                # 2. 문서 모델 생성
                self.file_status.emit(item_id, "문서 모델 생성 중...")
                self.file_progress.emit(item_id, 20)
                doc = build_doc_from_parse_result(raw_result, file_path)

                if not doc.get("sentences"):
                    self.file_status.emit(item_id, "완료 (검사할 문장이 없습니다)")
                    self.file_progress.emit(item_id, 100)
                    continue

            except Exception as e:
                self.file_status.emit(item_id, f"❌ 오류 발생: {e}")
                self.file_progress.emit(item_id, 0)
                continue

            # 3. AI 검사
            self.file_status.emit(item_id, "AI 오타 검사 시작...")
            
            def progress_cb(current_batch, total_batches):
                if self.cancel_event.is_set():
                    return
                # 20% ~ 90%
                p = 20 + int(70 * (current_batch / total_batches))
                self.file_progress.emit(item_id, p)
                self.file_status.emit(item_id, f"AI 검증 중... (배치 {current_batch}/{total_batches})")

            try:
                errors = run_ai_check(doc, progress_callback=progress_cb, stop_event=self.cancel_event)
            except InterruptedError:
                self.file_status.emit(item_id, "중단됨")
                self.cancel_event.set() # 다른 작업도 중단하도록 설정
                break
            except Exception as e:
                if self.cancel_event.is_set():
                    self.file_status.emit(item_id, "중단됨")
                    break
                self.file_status.emit(item_id, f"❌ 에러: {e}")
                self.file_progress.emit(item_id, 0)
                continue
                
            if self.cancel_event.is_set():
                self.file_status.emit(item_id, "중단됨")
                break

            # 4. 결과 정리
            item["results"] = errors
            self.file_original_path.emit(item_id, file_path)
            self.file_results.emit(item_id, errors)
            self.file_progress.emit(item_id, 100)
            self.file_done.emit(item_id, len(errors))

        self.finished_all.emit()

# ────────────────────────────────────────────
# Main Window
# ────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"문서 맞춤법 검사기 v{APP_VERSION}")
        icon_path = resource_path(os.path.join("assets", "app-icon.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setFixedSize(440, 720)
        self._apply_theme()
        self._build_ui()

        self.file_items = []
        self.is_processing = False
        self.all_results = []
        self._api_checked = False

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout()
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel("문서 맞춤법 검사기")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setObjectName("headerTitle")

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("divider")

        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self._on_drop)
        self.drop_area.btn_pick.clicked.connect(self._pick_files)

        list_container = QFrame()
        list_container.setObjectName("listContainer")
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(0, 4, 0, 0)
        list_layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setObjectName("listScroll")

        self.list_inner = QWidget()
        self.list_inner_layout = QVBoxLayout()
        self.list_inner_layout.setContentsMargins(0, 0, 0, 0)
        self.list_inner_layout.setSpacing(8)
        self.list_inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.list_inner.setLayout(self.list_inner_layout)
        self.scroll.setWidget(self.list_inner)

        list_layout.addWidget(self.scroll)
        list_container.setLayout(list_layout)

        self.status_lbl = QLabel("업로드된 문서가 없습니다.")
        self.status_lbl.setObjectName("statusLabel")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_row = QHBoxLayout()
        self.btn_clear = QPushButton("초기화")
        self.btn_clear.setObjectName("btnSecondary")
        self.btn_clear.setFont(QFont("맑은 고딕", 9, QFont.Weight.Bold))
        self.btn_stop = QPushButton("강제 중단")
        self.btn_stop.setObjectName("btnDanger")
        self.btn_stop.setFont(QFont("맑은 고딕", 9, QFont.Weight.Bold))
        self.btn_download = QPushButton("결과 다운로드")
        self.btn_download.setObjectName("btnPrimary")
        self.btn_download.setFont(QFont("맑은 고딕", 9, QFont.Weight.Bold))
        self.btn_clear.setFixedWidth(100)
        self.btn_stop.setFixedWidth(100)

        self.btn_clear.clicked.connect(self._clear_all)
        self.btn_stop.clicked.connect(self._stop_checking)
        self.btn_download.clicked.connect(self._save_results)

        btn_row.addWidget(self.btn_clear)
        btn_row.addWidget(self.btn_stop)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_download)

        root.addWidget(title)
        root.addWidget(divider)
        root.addWidget(self.drop_area)
        root.addWidget(self.status_lbl)
        root.addWidget(list_container, stretch=1)
        root.addLayout(btn_row)

        central.setLayout(root)
        self.setCentralWidget(central)

    def _apply_theme(self):
        app = QApplication.instance()
        if app is None: return

        font = QFont("맑은 고딕", 9)
        app.setFont(font)

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#FDF9F0"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#5D4037"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#F7F0E6"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#EDE0D4"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#5D4037"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#EDE0D4"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#5D4037"))
        app.setPalette(palette)

        app.setStyleSheet("""
            #headerTitle { font-size: 18px; font-weight: 700; color: #5D4037; }
            #divider { color: #E3D6C8; }
            #dropArea { background: #EDE0D4; border: 1px solid #D8C9B8; border-radius: 10px; }
            #dropArea[dragging="true"] { border: 1px solid #C1A062; background: #E7D7C6; }
            #dropIcon { 
                font-size: 42px; 
                color: #FFF3E0; 
                background: #D4A762; 
                border-radius: 12px; 
                padding-bottom: 4px; /* 이모티콘 수직 중앙 보정 */
            }
            #dropTitle { font-size: 12px; color: #5D4037; font-weight: 600; }
            #dropHint { font-size: 10px; color: #5D4037; }
            #dropFormats { font-size: 9px; color: #8D6E63; }
            #listContainer { background: transparent; }
            #listScroll { border: none; }
            #fileItem { background: #F3E9DC; border: 1px solid #DDCDBE; border-radius: 8px; }
            #fileName { font-weight: 600; color: #5D4037; }
            #fileStatus { font-size: 10px; color: #A1887F; }
            #progressBar { background: #E6D6C7; border: 1px solid #E6D6C7; height: 6px; border-radius: 3px; }
            #progressBar::chunk { background: #C1A062; border-radius: 3px; margin: 0px; }
            #statusLabel { color: #A1887F; }
            #btnPrimary { background: #C1A062; color: #5D4037; border: none; padding: 8px 24px; border-radius: 10px; font-weight: 700; }
            #btnPrimary:hover { background: #B39250; }
            #btnPrimary:pressed { background: #A88442; }
            #btnPick { background: #6D4C41; color: #FFF8E1; border: none; padding: 8px 24px; border-radius: 10px; font-weight: 700; }
            #btnPick:hover { background: #5B3F35; }
            #btnPick:pressed { background: #4D352E; }
            #btnSecondary { background: #9E9E9E; color: #5D4037; border: none; padding: 8px 24px; border-radius: 10px; font-weight: 700; }
            #btnSecondary:hover { background: #8C8C8C; }
            #btnSecondary:pressed { background: #7A7A7A; }
            #btnDanger { background: #BF360C; color: #FFF8E1; border: none; padding: 8px 24px; border-radius: 10px; font-weight: 700; }
            #btnDanger:hover { background: #A82E0B; }
            #btnDanger:pressed { background: #922608; }
        """)

    def _ensure_api_key(self):
        config = _load_config()
        provider = config.get("provider", PROVIDER_GEMINI)
        keys = config.get("keys", {})
        api_key = keys.get(provider, "")

        if api_key:
            _apply_config(config)
            return

        while True:
            key, ok = QInputDialog.getText(
                self,
                "API 키 입력",
                "API 키를 입력해 주세요.\n(OpenAI, Anthropic, Gemini 키 모두 지원합니다.)",
            )
            if not ok:
                QMessageBox.critical(self, "실행 취소", "API 키가 없어 검사를 진행할 수 없습니다.")
                QApplication.quit()
                return

            key = key.strip()
            if not key:
                continue

            # 바로 저장
            new_provider = _detect_provider(key)
            if "keys" not in config: config["keys"] = {}
            config["provider"] = new_provider
            config["keys"][new_provider] = key
            _save_config(config)
            _apply_config(config)
            QMessageBox.information(self, "설정 완료", f"API 키가 설정되었습니다.\n공급자: {new_provider}")
            break

    def _pick_files(self):
        if self.is_processing: return
        files, _ = QFileDialog.getOpenFileNames(
            self, "검사할 파일 선택", "", "지원 문서 (*.hwp *.hwpx *.pdf *.docx *.txt *.doc)"
        )
        if files:
            self._add_files(files)

    def _on_drop(self, paths):
        if self.is_processing: return
        self._add_files(paths)

    def _add_files(self, paths):
        added = 0
        for p in paths:
            if os.path.isdir(p):
                for fn in os.listdir(p):
                    fp = os.path.join(p, fn)
                    if fn.lower().endswith(SUPPORTED_EXT) and not fn.startswith('~'):
                        if self._add_file(fp): added += 1
            elif p.lower().endswith(SUPPORTED_EXT):
                if self._add_file(p): added += 1
        if added:
            self.status_lbl.setText(f"{added}개 파일 추가됨. 자동 검사를 시작합니다...")
            self._start_checking()

    def _add_file(self, path):
        for item in self.file_items:
            if item["path"] == path: return False
        widget = FileItemWidget(os.path.basename(path))
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.list_inner_layout.addWidget(widget)
        self.file_items.append({
            "id": len(self.file_items),
            "path": path,
            "name": os.path.basename(path),
            "widget": widget,
            "results": [],
            "progress": 0,
        })
        return True

    def _start_checking(self):
        if self.is_processing: return
        pending = [i for i in self.file_items if i["results"] == []]
        if not pending: return
        self.is_processing = True
        self.all_results = []

        self.worker = CheckWorker(pending, self) # self (MainWindow)를 parent_window로 전달
        self.worker.file_progress.connect(self._on_progress)
        self.worker.file_status.connect(self._on_status)
        self.worker.file_done.connect(self._on_done)
        self.worker.file_results.connect(self._on_results)
        self.worker.file_original_path.connect(self._on_file_original_path)
        self.worker.overall_status.connect(self._on_overall)
        self.worker.finished_all.connect(self._on_finished_all)
        self.worker.start()

    def _stop_checking(self):
        if not self.is_processing: return
        if hasattr(self, "worker"):
            self.worker.cancel()
        self.status_lbl.setText("강제 중단 중...")

    def _on_progress(self, item_id, progress):
        for item in self.file_items:
            if item["id"] == item_id:
                item["widget"].set_progress(progress)
                item["progress"] = progress
                break

    def _on_status(self, item_id, text):
        for item in self.file_items:
            if item["id"] == item_id:
                item["widget"].set_status(text)
                break

    def _on_done(self, item_id, error_count):
        for item in self.file_items:
            if item["id"] == item_id:
                item["progress"] = 100
                item["widget"].set_status(f"완료 ({error_count}건 발견)")
                break

    def _on_file_original_path(self, item_id, path):
         for item in self.file_items:
            if item["id"] == item_id:
                item["path"] = path
                break

    def _on_results(self, item_id, results):
        for item in self.file_items:
            if item["id"] == item_id:
                # Add file_path to error dicts so exporter can use it
                for r in results:
                     r["file"] = item["path"]
                item["results"] = results
                break
        if results:
            self.all_results.extend(results)

    def _on_overall(self, text):
        self.status_lbl.setText(text)

    def _on_finished_all(self):
        self.is_processing = False
        total_errors = 0
        for item in self.file_items:
            total_errors += len(item.get("results", []))
            
        # [IMPROVED] Check if any item was manually or unexpectedly stopped
        is_stopped = any(i["widget"].status.text() == "중단됨" for i in self.file_items)
        
        if is_stopped:
            self.status_lbl.setText(f"중단됨. 현재까지 {total_errors}건 발견.")
            QMessageBox.warning(
                self, "검사 중단", 
                f"사용자에 의해 검사가 중단되었습니다.\n"
                f"현재까지 {total_errors}건의 오류를 발견했습니다.\n"
                "결과 다운로드 버튼을 눌러 지금까지의 결과를 저장할 수 있습니다."
            )
        else:
            self.status_lbl.setText(f"검사 완료! 총 {total_errors}건 발견.")
            QMessageBox.information(
                self, "검사 완료", 
                f"검사가 완료되었습니다.\n총 {total_errors}건 발견.\n결과 다운로드 버튼을 눌러 저장하세요."
            )

    def _clear_all(self):
        if self.is_processing: return
        for item in list(self.file_items):
            item["widget"].setParent(None)
        self.file_items.clear()
        self.all_results.clear()
        self.status_lbl.setText("업로드된 문서가 없습니다.")

    def _save_results(self):
        if not self.file_items:
            QMessageBox.information(self, "알림", "저장할 검사 결과가 없습니다.")
            return
        
        all_results = []
        for item in self.file_items:
            all_results.extend(item.get("results", []))
            
        if not all_results:
            QMessageBox.information(self, "알림", "저장할 검사 결과가 없습니다.")
            return

        desktop_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        if not desktop_dir:
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = os.path.join(desktop_dir, f"맞춤법검사결과_{timestamp}.xlsx")
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "검사결과 저장", default_path, "Excel Files (*.xlsx)"
        )
        if not save_path:
            return
            
        try:
            # excel_exporter.py 의 export_to_excel 사용 (버그 수정)
            export_to_excel(all_results, save_path)
            QMessageBox.information(self, "저장 완료", f"저장되었습니다.\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", str(e))

def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()