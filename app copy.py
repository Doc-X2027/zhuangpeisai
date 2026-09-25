"""PySide6 single-window competition application."""
from __future__ import annotations
import sys
import threading
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QFont, QPixmap, QTextCursor
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QProgressBar, QTabWidget, QTextEdit, QVBoxLayout, QWidget)
from competition_service import CompetitionService, IDENTIFY_IMAGE, WORKFLOW_IMAGE, format_duration
from server_multithread import CompetitionTCPServer

STYLE = """
QWidget { background:#0b1220; color:#dce7f7; font-family:'Microsoft YaHei UI'; font-size:14px; }
QFrame#card { background:#111c30; border:1px solid #253552; border-radius:16px; }
QLabel#title { font-size:25px; font-weight:700; color:#f7fbff; }
QLabel#muted { color:#8ea2bf; font-size:12px; }
QLabel#status { color:#64d8cb; font-weight:600; }
QPushButton { background:#1677ff; border:0; border-radius:10px; padding:11px 13px; font-weight:700; text-align:left; }
QPushButton:hover { background:#338cff; } QPushButton:pressed { background:#0d61d5; }
QPushButton:disabled { background:#253149; color:#70809a; }
QTabWidget::pane { border:1px solid #253552; border-radius:10px; background:#0e1829; }
QTabBar::tab { background:#17243a; padding:10px 18px; margin-right:3px; border-radius:7px; }
QTabBar::tab:selected { background:#1677ff; }
QTextEdit { background:#0e1829; border:0; padding:10px; font-family:Consolas,'Microsoft YaHei UI'; }
QProgressBar { border:0; border-radius:4px; background:#253149; height:7px; }
QProgressBar::chunk { border-radius:4px; background:#36cfc9; }
"""

class DropImageLabel(QLabel):
    image_dropped = Signal(str)
    def __init__(self, text=""):
        super().__init__(text)
        self.setAcceptDrops(True)
    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile() and urls[0].toLocalFile().lower().endswith(".png"):
            event.acceptProposedAction()
        else:
            event.ignore()
    def dropEvent(self, event):
        path = event.mimeData().urls()[0].toLocalFile()
        self.image_dropped.emit(path)
        event.acceptProposedAction()

class StageWorker(QObject):
    chunk = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()
    def __init__(self, function):
        super().__init__(); self.function = function
    @Slot()
    def run(self):
        try: self.succeeded.emit(self.function(self.chunk.emit))
        except Exception as exc: self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally: self.finished.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.service = CompetitionService()
        self.active_thread = None
        self.server = CompetitionTCPServer()
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.start_time = datetime.now()
        self.dropped_image: Path | None = None
        self.setWindowTitle('智能装配任务控制台')
        self.resize(1280, 800); self.setMinimumSize(1050, 680)
        self._build_ui(); self._start_timer(); self.server_thread.start()

    def _card(self):
        frame = QFrame(); frame.setObjectName("card"); return frame

    def _build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(22,18,22,18); outer.setSpacing(14)
        header = self._card(); row = QHBoxLayout(header); row.setContentsMargins(22,14,22,14)
        title = QLabel('智能装配任务控制台'); title.setObjectName("title")
        self.server_label = QLabel('● 通信服务准备中'); self.server_label.setObjectName("status")
        self.time_label = QLabel(); self.time_label.setObjectName("muted")
        row.addWidget(title); row.addStretch(); row.addWidget(self.server_label); row.addSpacing(20); row.addWidget(self.time_label)
        outer.addWidget(header)

        body = QHBoxLayout(); body.setSpacing(14); outer.addLayout(body, 1)
        controls = self._card(); controls.setMinimumWidth(225); controls.setMaximumWidth(285)
        ctl = QVBoxLayout(controls); ctl.setContentsMargins(15,15,15,15); ctl.setSpacing(10)
        ctl.addWidget(QLabel('任务流程'))
        self.stage_label = QLabel('等待任务 · 0/3'); self.stage_label.setObjectName("status"); self.stage_label.setWordWrap(True); ctl.addWidget(self.stage_label)
        self.progress = QProgressBar(); self.progress.setRange(0,100); ctl.addWidget(self.progress)
        self.buttons=[]
        for i,label in enumerate(('01  分析任务图片','02  创建装配流程','03  输出日志与指令')):
            button=QPushButton(label); button.setMinimumHeight(48); button.setEnabled(i==0)
            ctl.addWidget(button); self.buttons.append(button)
        self.buttons[0].clicked.connect(lambda: self.run_stage(0)); self.buttons[1].clicked.connect(lambda: self.run_stage(1)); self.buttons[2].clicked.connect(lambda: self.run_stage(2))
        ctl.addStretch()
        self.image_path_label=QLabel('当前使用内置图片\n可将 PNG 拖到右侧'); self.image_path_label.setWordWrap(True); self.image_path_label.setObjectName("muted"); ctl.addWidget(self.image_path_label)
        self.path_label=QLabel('任务输出将显示在这里'); self.path_label.setWordWrap(True); self.path_label.setObjectName("muted"); ctl.addWidget(self.path_label)
        body.addWidget(controls, 0)

        right = QVBoxLayout(); right.setSpacing(14); body.addLayout(right, 1)
        image_card = self._card(); image_layout = QVBoxLayout(image_card); image_layout.setContentsMargins(16,13,16,16)
        hint=QLabel('图片工作区  ·  仅接受单个 PNG 文件'); hint.setObjectName("muted"); image_layout.addWidget(hint)
        self.image_label = DropImageLabel('正在读取图片…'); self.image_label.setAlignment(Qt.AlignCenter); self.image_label.setMinimumHeight(245)
        self.image_label.setStyleSheet("background:#09111e;border:1px dashed #365175;border-radius:12px;color:#70809a;")
        self.image_label.image_dropped.connect(self._load_dropped_image); image_layout.addWidget(self.image_label, 1)
        right.addWidget(image_card, 3)
        self.tabs=QTabWidget(); self.identify_text=QTextEdit(); self.workflow_text=QTextEdit(); self.log_text=QTextEdit()
        for widget in (self.identify_text,self.workflow_text,self.log_text): widget.setReadOnly(True)
        self.tabs.addTab(self.identify_text,'模型识别'); self.tabs.addTab(self.workflow_text,'流程 JSON'); self.tabs.addTab(self.log_text,'任务记录')
        right.addWidget(self.tabs, 4)
        self._show_image(IDENTIFY_IMAGE)

    def _start_timer(self):
        self.clock=QTimer(self); self.clock.timeout.connect(self._update_clock); self.clock.start(1000); self._update_clock()

    def _run_server(self):
        try: self.server.serve_forever()
        except Exception: pass

    def _update_clock(self):
        self.time_label.setText(f"启动 {self.start_time:%H:%M:%S}  ·  运行 {format_duration((datetime.now()-self.start_time).total_seconds())}")
        if self.server_thread.is_alive(): self.server_label.setText('● 通信服务正常 · 8888')

    def _load_dropped_image(self, path):
        candidate=Path(path)
        if candidate.suffix.lower() != ".png" or not candidate.is_file():
            self.append_log('未接受该文件：请拖入 PNG 图片'); return
        if self._show_image(candidate):
            self.dropped_image=candidate
            self.image_path_label.setText(f"已选择图片:\n{candidate}")
            self.append_log(f"图片已更新: {candidate}")

    def _show_image(self, path):
        pix=QPixmap(str(path))
        if pix.isNull(): self.image_label.setText(f"无法显示图片\n{path}"); return False
        self._source_pixmap=pix; self._update_image(); return True

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,"_source_pixmap"): self._update_image()
    def _update_image(self):
        self.image_label.setPixmap(self._source_pixmap.scaled(self.image_label.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
    def append_log(self,message):
        self.log_text.append(f"[{datetime.now():%H:%M:%S}] {message}"); self.log_text.ensureCursorVisible()

    def run_stage(self,index):
        if self.active_thread and self.active_thread.isRunning(): return
        identify_path=self.dropped_image or IDENTIFY_IMAGE
        workflow_path=self.dropped_image or WORKFLOW_IMAGE
        functions=[lambda callback:self.service.identify_stage(identify_path,callback), lambda callback:self.service.workflow_stage(workflow_path,callback), lambda _callback:self.service.log_stage()]
        if index==0: self.identify_text.clear(); self.tabs.setCurrentIndex(0)
        elif index==1: self.workflow_text.clear(); self.tabs.setCurrentIndex(1)
        self.buttons[index].setEnabled(False); self.progress.setRange(0,0)
        self.stage_label.setText(f"模型正在输出 · {index+1}/3"); self.append_log(f"开始执行: {self.buttons[index].text()}")
        thread=QThread(self); worker=StageWorker(functions[index]); worker.moveToThread(thread)
        thread.started.connect(worker.run); worker.chunk.connect(lambda text,i=index:self._append_stream(i,text))
        worker.succeeded.connect(lambda value,i=index:self._stage_success(i,value)); worker.failed.connect(lambda error,i=index:self._stage_error(i,error))
        worker.finished.connect(thread.quit); worker.finished.connect(worker.deleteLater); thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: setattr(self,"active_thread",None)); self.active_thread=thread; thread.start()

    def _append_stream(self,index,text):
        target=self.identify_text if index==0 else self.workflow_text
        target.moveCursor(QTextCursor.MoveOperation.End); target.insertPlainText(text); target.ensureCursorVisible()

    def _stage_success(self,index,value):
        self.progress.setRange(0,100); self.progress.setValue((index+1)*100//3)
        self.stage_label.setText(f"阶段完成 · {index+1}/3"); self.append_log(f"已完成: {self.buttons[index].text()}")
        if index==0:
            if not self.identify_text.toPlainText(): self.identify_text.setPlainText(value)
            self.buttons[1].setEnabled(True); self.tabs.setCurrentIndex(0)
        elif index==1:
            workflow,command,path=value
            # Replace streamed source with formatted JSON after completion.
            self.workflow_text.setPlainText(workflow); self.buttons[2].setEnabled(True)
            self.path_label.setText(f"流程文件: {path}\n执行指令: {command}"); self.tabs.setCurrentIndex(1)
        else:
            path,command=value; self.path_label.setText(self.path_label.text()+f"\n记录文件: {path}\n最终指令: {command}")
            self.log_text.append(f"\n最终执行指令: {command}\n已写入任务记录: {path}"); self.tabs.setCurrentIndex(2)

    def _stage_error(self,index,error):
        self.progress.setRange(0,100); self.stage_label.setText(f"阶段异常 · {index+1}/3 可重试")
        self.buttons[index].setEnabled(True); self.append_log(f"错误信息: {error}"); self.tabs.setCurrentIndex(2)

    def closeEvent(self,event):
        self.server.shutdown()
        if self.active_thread and self.active_thread.isRunning(): self.active_thread.quit(); self.active_thread.wait(1500)
        event.accept()

def main():
    app=QApplication(sys.argv); app.setStyle("Fusion"); app.setStyleSheet(STYLE); app.setFont(QFont("Microsoft YaHei UI",10))
    window=MainWindow(); window.show(); return app.exec()
if __name__=="__main__": raise SystemExit(main())
