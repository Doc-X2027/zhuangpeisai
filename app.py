"""Competition GUI. Source stays ASCII; UI copy uses Unicode escapes."""
from __future__ import annotations
import os, socket, sys, threading, time
import hikvision
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject,QThread,QTimer,Qt,Signal,Slot
from PySide6.QtGui import QColor,QFont,QIntValidator,QPixmap,QTextCursor
from PySide6.QtWidgets import (QApplication,QFrame,QHBoxLayout,QLabel,QLineEdit,QMainWindow,
    QPushButton,QProgressBar,QTextEdit,QVBoxLayout,QWidget)
from competition_service import CompetitionService,IDENTIFY_IMAGE,WORKFLOW_IMAGE,cache_image_for_model
from command_sender import send_task_command
from server_multithread import CompetitionTCPServer
from voice_client import RemoteSpeechClient

INPUT_IMAGE = Path(r"E:\photo\color.jpg")

def detect_local_ip():
    """Return the preferred LAN IPv4 address without sending network data."""
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as probe:
            probe.connect(("192.168.34.200",8765))
            address=probe.getsockname()[0]
            if address and not address.startswith("127."): return address
    except OSError:
        pass
    try:
        addresses=socket.gethostbyname_ex(socket.gethostname())[2]
        return next((address for address in addresses if not address.startswith("127.")),"未检测到")
    except OSError:
        return "未检测到"

STYLE="""
QWidget { background:#0b1220; color:#dce7f7; font-family:'Microsoft YaHei UI'; font-size:14px; }
QFrame#card { background:#111c30; border:1px solid #253552; border-radius:16px; }
QLabel#title { font-size:24px; font-weight:700; color:#f7fbff; }
QLabel#muted { color:#8ea2bf; font-size:12px; }
QLabel#status { color:#64d8cb; font-weight:600; }
QLineEdit { background:#0e1829; border:1px solid #365175; border-radius:6px; padding:5px; }
QFrame#timerBox { background:#0e1829; border:1px solid #365175; border-radius:8px; }
QPushButton { background:#1677ff; border:0; border-radius:10px; padding:10px 12px; font-weight:700; text-align:left; }
QPushButton:hover { background:#338cff; } QPushButton:pressed { background:#0d61d5; }
QPushButton:disabled { background:#253149; color:#70809a; }
QTabWidget::pane { border:1px solid #253552; border-radius:10px; background:#0e1829; }
QTabBar::tab { background:#17243a; padding:9px 17px; margin-right:3px; border-radius:7px; }
QTabBar::tab:selected { background:#1677ff; }
QTextEdit { background:#0e1829; border:0; padding:10px; font-family:Consolas,'Microsoft YaHei UI'; }
QProgressBar { border:0; border-radius:4px; background:#253149; height:7px; }
QProgressBar::chunk { border-radius:4px; background:#36cfc9; }
"""

TASK_NAMES=("01  \u8bc6\u522b\u4efb\u52a1\u56fe\u7247","02  \u751f\u6210\u88c5\u914d\u6d41\u7a0b","03  \u751f\u6210\u65e5\u5fd7\u4e0e\u6307\u4ee4")
TASK_COPY=(
    "\u8bfb\u53d6\u4efb\u52a1\u56fe\u7247\uff0c\u8c03\u7528\u89c6\u89c9\u5927\u6a21\u578b\u8bc6\u522b\u5143\u7d20\u548c\u6570\u91cf\u3002",
    "\u8bfb\u53d6\u88c5\u914d\u8981\u6c42\uff0c\u751f\u6210\u5de5\u4f5c\u6d41 JSON \u548c\u6267\u884c\u5e8f\u5217\u3002",
    "\u4fdd\u5b58\u5f53\u524d\u6bd4\u8d5b\u65e5\u5fd7\u5e76\u8f93\u51fa\u53ef\u7528\u7684\u6267\u884c\u6307\u4ee4\u3002")

class DropImageLabel(QLabel):
    image_dropped=Signal(str)
    def __init__(self,text=""):
        super().__init__(text); self.setAcceptDrops(True)
    def dragEnterEvent(self,event):
        urls=event.mimeData().urls()
        suffix=Path(urls[0].toLocalFile()).suffix.lower() if len(urls)==1 and urls[0].isLocalFile() else ""
        if suffix in ('.png','.jpg','.jpeg','.webp','.bmp','.tif','.tiff'): event.acceptProposedAction()
        else: event.ignore()
    def dropEvent(self,event):
        self.image_dropped.emit(event.mimeData().urls()[0].toLocalFile()); event.acceptProposedAction()

class ResultTextEdit(QTextEdit):
    enter_pressed=Signal()
    def __init__(self):
        super().__init__(); self.capture_enter=False
    def keyPressEvent(self,event):
        if self.capture_enter and event.key() in (Qt.Key_Return,Qt.Key_Enter):
            event.accept(); self.enter_pressed.emit()
        else:
            super().keyPressEvent(event)

class StageWorker(QObject):
    chunk=Signal(int,str); status=Signal(int,str); succeeded=Signal(int,object); failed=Signal(int,str); finished=Signal()
    def __init__(self,index,function): super().__init__(); self.index=index; self.function=function
    @Slot()
    def run(self):
        try: self.succeeded.emit(self.index,self.function(lambda text:self.chunk.emit(self.index,text),lambda text:self.status.emit(self.index,text)))
        except Exception as exc: self.failed.emit(self.index,f"{type(exc).__name__}: {exc}")
        finally: self.finished.emit()

class NetworkBridge(QObject):
    request=Signal(object)
    feedback=Signal(str)
    command_delivery=Signal(str,bool)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.service=CompetitionService(); self.active_thread=None; self.active_worker=None; self.selected_stage=0
        self.stage_ok=[False,False,False]; self.stage_values=[None,None,None]; self.network_request=None; self.network_queue=[]
        self.bridge=NetworkBridge(); self.bridge.request.connect(self._accept_network_request); self.bridge.feedback.connect(self._accept_feedback)
        self.bridge.command_delivery.connect(self._command_delivery_finished)
        self.listen_host,self.listen_port="0.0.0.0",8888; self.server_error=None; self.listener_status_error=False
        self.command_target_host=os.getenv("TASK_COMMAND_HOST","192.168.34.10")
        self.command_target_port=int(os.getenv("TASK_COMMAND_PORT","8888"))
        self.server=CompetitionTCPServer(self.listen_host,self.listen_port,self._network_command,self._network_feedback,self._robot_read_command)
        self.server_thread=threading.Thread(target=self._run_server,args=(self.server,),daemon=True)
        self.timer_started_at=None; self.countdown_seconds=300; self.timer_remaining=300; self.timer_running=False; self.timer_last_tick=None
        self.last_voice_text=""; self.last_voice_received_at=0.0
        self.awaiting_voice_command=False
        self.voice_triggered_stage=None
        self.pending_robot_command=None
        self.pending_robot_command_lock=threading.Lock()
        # Preview and model both use cached files; source documents stay read-only.
        self.stage_sources={0:INPUT_IMAGE,1:INPUT_IMAGE}; self.stage_images={}; self.image_cache_info={}
        self.input_image_signature=None
        for index,source in self.stage_sources.items():
            try:
                cached,source_size,cached_size=cache_image_for_model(source)
            except (FileNotFoundError,OSError) as exc:
                self.image_load_error=str(exc)
                continue
            self.stage_images[index]=cached; self.image_cache_info[index]=(source_size,cached_size)
        self.stage_documents=["", "", ""]; self.output_document=""
        self.displayed_stage=None; self.pending_auto_stage=None
        self.setWindowTitle("\u667a\u80fd\u88c5\u914d\u4efb\u52a1\u63a7\u5236\u53f0"); self.resize(1280,800)
        screen=QApplication.primaryScreen()
        if screen:
            area=screen.availableGeometry(); self.setMinimumSize(area.width()//3,area.height()//3)
        else: self.setMinimumSize(640,360)
        self._build_ui(); self._start_timers(); self.server_thread.start()
        self._start_voice_client()

    def _card(self):
        frame=QFrame(); frame.setObjectName('card'); return frame

    def _build_ui(self):
        root=QWidget(); self.setCentralWidget(root)
        outer=QVBoxLayout(root); outer.setContentsMargins(20,16,20,16); outer.setSpacing(12)
        header=self._card(); row=QHBoxLayout(header); row.setContentsMargins(18,11,18,11)
        title=QLabel("\u667a\u80fd\u88c5\u914d\u63a7\u5236\u53f0"); title.setObjectName('title'); row.addWidget(title); row.addStretch()
        self.listen_status=QLabel("\u25cf \u76d1\u542c"); self.listen_status.setObjectName('status'); row.addWidget(self.listen_status)
        self.ip_edits=[]
        for value in ('0','0','0','0'):
            edit=QLineEdit(value); edit.setMaxLength(3); edit.setFixedWidth(36); edit.setAlignment(Qt.AlignCenter); edit.setValidator(QIntValidator(0,255,self)); self.ip_edits.append(edit); row.addWidget(edit)
            if len(self.ip_edits)<4: row.addWidget(QLabel('.'))
        row.addWidget(QLabel(':')); self.port_edit=QLineEdit('8888'); self.port_edit.setMaxLength(5); self.port_edit.setFixedWidth(55); self.port_edit.setAlignment(Qt.AlignCenter); self.port_edit.setValidator(QIntValidator(1,65535,self)); row.addWidget(self.port_edit)
        self.listen_button=QPushButton("\u5e94\u7528"); self.listen_button.setFixedWidth(60); self.listen_button.clicked.connect(self._apply_listener); row.addWidget(self.listen_button); row.addSpacing(12)
        timer_box=QFrame(); timer_box.setObjectName('timerBox'); timer_box.setFixedWidth(178); timer_row=QHBoxLayout(timer_box); timer_row.setContentsMargins(5,2,5,2); timer_row.setSpacing(2)
        self.time_edit=QLineEdit("05:00"); self.time_edit.setAlignment(Qt.AlignCenter); self.time_edit.setStyleSheet("background:transparent;border:0;padding:2px;color:#f7fbff;font-size:22px;font-weight:700;"); self.time_edit.setFixedWidth(88); self.time_edit.setMaxLength(8); self.time_edit.editingFinished.connect(self._apply_timer_text); timer_row.addWidget(self.time_edit)
        self.timer_button=QPushButton("\u25b6"); self.timer_button.setToolTip("\u542f\u52a8 / \u6682\u505c"); self.timer_button.setFixedSize(36,34); self.timer_button.setStyleSheet("QPushButton{background:transparent;border:0;padding:0;text-align:center;font-size:18px;} QPushButton:hover{background:#253552;}"); self.timer_button.clicked.connect(self._toggle_timer); timer_row.addWidget(self.timer_button)
        self.timer_reset_button=QPushButton("\u21bb"); self.timer_reset_button.setToolTip("\u91cd\u7f6e"); self.timer_reset_button.setFixedSize(36,34); self.timer_reset_button.setStyleSheet("QPushButton{background:transparent;border:0;padding:0;text-align:center;font-size:20px;} QPushButton:hover{background:#253552;}"); self.timer_reset_button.clicked.connect(self._reset_timer); timer_row.addWidget(self.timer_reset_button)
        row.addWidget(timer_box)
        outer.addWidget(header)

        body=QHBoxLayout(); body.setSpacing(12); outer.addLayout(body,1)
        controls=self._card(); controls.setMinimumWidth(185); controls.setMaximumWidth(225); ctl=QVBoxLayout(controls); ctl.setContentsMargins(15,15,15,15); ctl.setSpacing(10)
        ctl.addWidget(QLabel("\u4efb\u52a1\u9009\u62e9")); self.buttons=[]
        for i,name in enumerate(TASK_NAMES):
            button=QPushButton(name); button.setMinimumHeight(46); button.clicked.connect(lambda _checked=False,n=i:self.select_stage(n)); ctl.addWidget(button); self.buttons.append(button)
        self.task_title=QLabel(); self.task_title.setObjectName('status'); ctl.addWidget(self.task_title)
        self.task_copy=QLabel(); self.task_copy.setObjectName('muted'); self.task_copy.setWordWrap(True); self.task_copy.setMinimumHeight(42); ctl.addWidget(self.task_copy)
        self.progress=QProgressBar(); self.progress.setRange(0,100); ctl.addWidget(self.progress); ctl.addStretch()
        network_title=QLabel("网络信息"); network_title.setObjectName('status'); ctl.addWidget(network_title)
        ctl.addWidget(QLabel("本机 IP（自动读取）"))
        self.local_ip_edit=QLineEdit(detect_local_ip()); self.local_ip_edit.setReadOnly(True); ctl.addWidget(self.local_ip_edit)
        ctl.addWidget(QLabel("机器人 IP（手动输入）"))
        self.robot_ip_edit=QLineEdit("192.168.34.300"); ctl.addWidget(self.robot_ip_edit)
        ctl.addWidget(QLabel("语音盒子 IP（手动输入）"))
        self.voice_box_ip_edit=QLineEdit("192.168.34.200"); ctl.addWidget(self.voice_box_ip_edit)
        self.image_path_label=QLabel("\u4f7f\u7528\u7f13\u5b58\u538b\u7f29\u56fe\u7247\uff0c\u53ef\u62d6\u5165\u56fe\u7247"); self.image_path_label.setObjectName('muted'); self.image_path_label.setWordWrap(True); ctl.addWidget(self.image_path_label)
        self.path_label=QLabel("\u4efb\u52a1\u8f93\u51fa\u5c06\u663e\u793a\u5728\u8fd9\u91cc"); self.path_label.setObjectName('muted'); self.path_label.setWordWrap(True); ctl.addWidget(self.path_label); body.addWidget(controls)

        right=QVBoxLayout(); right.setSpacing(12); body.addLayout(right,1)
        image_card=self._card(); image_layout=QVBoxLayout(image_card); image_layout.setContentsMargins(14,11,14,14)
        image_layout.addWidget(QLabel("\u56fe\u7247\u5de5\u4f5c\u533a  \u00b7  \u9884\u89c8\u4e0e\u4e0a\u4f20\u5747\u4f7f\u7528 1MB \u4ee5\u4e0b\u7684\u7f13\u5b58\u56fe\u7247"))
        self.image_label=DropImageLabel("\u6b63\u5728\u8bfb\u53d6\u56fe\u7247\u2026"); self.image_label.setAlignment(Qt.AlignCenter); self.image_label.setMinimumHeight(120); self.image_label.setStyleSheet('background:#09111e;border:1px dashed #365175;border-radius:12px;color:#70809a;'); self.image_label.image_dropped.connect(self._load_dropped_image); image_layout.addWidget(self.image_label,1); right.addWidget(image_card,3)
        result_card=self._card(); result_layout=QVBoxLayout(result_card); result_layout.setContentsMargins(14,11,14,14)
        result_header=QHBoxLayout(); self.result_title=QLabel(); self.result_title.setObjectName('status'); result_header.addWidget(self.result_title); result_header.addStretch()
        self.start_task_button=QPushButton("\u5f00\u59cb\u4efb\u52a1"); self.start_task_button.setFixedWidth(120); self.start_task_button.setMinimumHeight(42); self.start_task_button.clicked.connect(self.run_selected_stage); result_header.addWidget(self.start_task_button); result_layout.addLayout(result_header)
        self.result_text=ResultTextEdit(); self.result_text.setPlaceholderText("\u4efb\u52a1\u7ed3\u679c\u5c06\u663e\u793a\u5728\u8fd9\u91cc\uff0c\u53ef\u76f4\u63a5\u4fee\u6539"); self.result_text.enter_pressed.connect(self._resume_auto_stage); result_layout.addWidget(self.result_text,1); right.addWidget(result_card,4)
        self.select_stage(0)

    def _start_timers(self):
        self.clock=QTimer(self); self.clock.timeout.connect(self._update_clock); self.clock.start(1000)
        self.photo_timer=QTimer(self); self.photo_timer.timeout.connect(self._refresh_live_image); self.photo_timer.start(500)
        self.flow_timer=QTimer(self); self.flow_timer.setInterval(35); self.flow_timer.timeout.connect(self._animate_flow); self.flow_index=None; self.flow_phase=0

    def _start_voice_client(self):
        base_url=os.getenv("AUBO_ARM_SPEECH_BASE_URL","http://192.168.34.200:8765")
        self.voice_client=RemoteSpeechClient(base_url,self,auto_listen=True,events_enabled=False)
        self.voice_client.status_changed.connect(self._voice_status_changed)
        self.voice_client.recognition_received.connect(self._voice_recognition_received)
        self.voice_client.error_received.connect(lambda message:self.append_log(f"\u8bed\u97f3\uff1a{message}"))
        self.voice_client.start()

    @Slot(str,bool)
    def _voice_status_changed(self,text,connected):
        if text==getattr(self,'last_voice_status',None): return
        self.last_voice_status=text
        self.append_log(f"\u8bed\u97f3\u72b6\u6001\uff1a{text}")

    @Slot(str,object)
    def _voice_recognition_received(self,text,payload):
        now=time.monotonic()
        if text==self.last_voice_text and now-self.last_voice_received_at<1.0: return
        self.last_voice_text=text
        self.last_voice_received_at=now
        self.append_log(f"\u8bed\u97f3\u8bc6\u522b\u7ed3\u679c\uff1a{text}")
        if "小具同学" in text:
            self.awaiting_voice_command=True
            self.append_log("检测到唤醒词，正在播报就绪提示")
            self.voice_client.listen_for_command_after_tts("我已就绪，请下达指令")
            text=text.replace("小具同学","",1).strip(" ，,。！？!?")
            if not text:
                return
        command_stage=None
        if "\u4efb\u52a1\u4e00" in text: command_stage=0
        elif "\u4efb\u52a1\u4e8c" in text: command_stage=1
        if command_stage is None: return
        self.awaiting_voice_command=False
        if self.active_thread or self.network_request:
            self.append_log(f"\u8bed\u97f3\u6307\u4ee4\u5df2\u5ffd\u7565\uff1a\u5f53\u524d\u6709\u4efb\u52a1\u6b63\u5728\u6267\u884c\uff0c\u65e0\u6cd5\u542f\u52a8\u4efb\u52a1{command_stage+1}")
            return
        self.append_log(f"\u8bed\u97f3\u6307\u4ee4\u5df2\u63a5\u53d7\uff1a\u6267\u884c\u4efb\u52a1{command_stage+1}")
        self.voice_triggered_stage=command_stage
        self.select_stage(command_stage)
        self._execute_stage(command_stage)

    def _run_server(self,server):
        try: server.serve_forever()
        except Exception as exc:
            if server is self.server: self.server_error=str(exc)

    def _network_command(self,command,addr):
        request={'command':command,'addr':addr,'event':threading.Event(),'response':None,'received_at':time.perf_counter()}
        self.bridge.request.emit(request)
        if not request['event'].wait(600): return 'Process failure: GUI task timeout'
        return request['response'] or 'Process failure'

    def _network_feedback(self,text,addr):
        self.bridge.feedback.emit(text)

    def _robot_read_command(self,addr):
        with self.pending_robot_command_lock:
            command=self.pending_robot_command
            if command:
                self.pending_robot_command=None
        if not command:
            self.bridge.feedback.emit(f"机器人 {addr[0]}:{addr[1]} 请求 read，但当前没有待发送信息")
            return "Process failure: no pending task command"
        self.bridge.feedback.emit(f"机器人 {addr[0]}:{addr[1]} 请求 read，已返回待发送信息：{command}")
        return command

    def _start_robot_project(self):
        robot_ip=self.robot_ip_edit.text().strip()
        def start():
            try:
                from set_aubo_do06_high import set_do06_high
                set_do06_high(robot_ip,30004,"aubo","123456")
                self.bridge.command_delivery.emit(f"机械臂工程启动信号已发送：{robot_ip} 的 DO06 已置高，等待 read",True)
            except Exception as exc:
                self.bridge.command_delivery.emit(f"机械臂工程启动失败：{type(exc).__name__}: {exc}",False)
        threading.Thread(target=start,daemon=True).start()

    def _send_task_command(self,command):
        host,port=self.command_target_host,self.command_target_port
        def deliver():
            try:
                size=send_task_command(host,port,command)
                self.bridge.command_delivery.emit(f"\u4efb\u52a1\u6307\u4ee4\u5df2\u53d1\u9001\u5230 {host}:{port}\uff08{size} \u5b57\u8282\uff09",True)
            except Exception as exc:
                self.bridge.command_delivery.emit(f"\u4efb\u52a1\u6307\u4ee4\u53d1\u9001\u5931\u8d25 {host}:{port}\uff1a{type(exc).__name__}: {exc}",False)
        threading.Thread(target=deliver,daemon=True).start()

    @Slot(str,bool)
    def _command_delivery_finished(self,message,ok):
        self.append_log(message)

    @Slot(str)
    def _accept_feedback(self,text):
        line=self.service.record_robot_visual_log(text)
        self._append_output(line+"\n")

    @Slot(object)
    def _accept_network_request(self,request):
        if self.active_thread or self.network_request:
            request['response']='Process failure: task busy'; request['event'].set(); return
        mapping={'identify':[0],'planning':[1],'auto':[0,1,2]}
        addr=request['addr']; self.service.client_addr=addr
        self.append_log(f"\u5ba2\u6237\u7aef {addr[0]}:{addr[1]} \u5df2\u8fde\u63a5\uff0c\u63a5\u6536\u547d\u4ee4\uff1a{request['command']}")
        self.network_request=request; self.network_queue=list(mapping[request['command']]); self._run_next_network_stage()

    def _run_next_network_stage(self):
        if self.active_thread:
            QTimer.singleShot(80,self._run_next_network_stage); return
        if not self.network_queue:
            command=self.network_request['command']
            if command=='identify': response=self.stage_values[0] or self.service.result.identification
            elif command=='planning': response=self.stage_values[1][1] if self.stage_values[1] else self.service.result.command_result
            else: response=self.stage_values[1][1] if self.stage_values[1] else self.service.result.command_result
            self.network_request['response']=response; self.network_request['event'].set(); self.network_request=None; return
        stage=self.network_queue.pop(0); self.select_stage(stage); self._execute_stage(stage)

    def _apply_listener(self):
        parts=[edit.text().strip() for edit in self.ip_edits]; port_text=self.port_edit.text().strip()
        if any(not part for part in parts) or not port_text: self._set_listener_status("\u25cf \u5730\u5740\u4e0d\u5b8c\u6574",False); return
        values=[int(part) for part in parts]; port=int(port_text)
        if any(value>255 for value in values) or not 1<=port<=65535: self._set_listener_status("\u25cf \u5730\u5740\u65e0\u6548",False); return
        host='.'.join(str(value) for value in values)
        if host==self.listen_host and port==self.listen_port and self.server_thread.is_alive(): self._set_listener_status("\u25cf \u76d1\u542c",True); return
        self.server.shutdown(); self.server_thread.join(1.2); self.listen_host,self.listen_port=host,port; self.server_error=None
        self.server=CompetitionTCPServer(host,port,self._network_command,self._network_feedback,self._robot_read_command); self.server_thread=threading.Thread(target=self._run_server,args=(self.server,),daemon=True); self.server_thread.start(); self._set_listener_status("\u25cf \u76d1\u542c",True)

    def _set_listener_status(self,text,ok):
        self.listener_status_error=not ok
        self.listen_status.setText(text)
        self.listen_status.setStyleSheet(f"color:{'#64d8cb' if ok else '#ff4d4f'};font-weight:600;")

    def _begin_timer(self):
        if not self.timer_running and self.timer_started_at is None: self._toggle_timer()

    def _apply_timer_text(self):
        if self.timer_running: return
        try:
            parts=self.time_edit.text().strip().split(':')
            if len(parts)!=2: raise ValueError
            minutes,seconds=(int(part) for part in parts)
            if minutes<0 or not 0<=seconds<60: raise ValueError
            self.timer_remaining=minutes*60+seconds; self.countdown_seconds=self.timer_remaining
        except ValueError:
            pass
        self._show_timer()

    def _show_timer(self):
        remaining=max(0,int(self.timer_remaining+0.999)); minutes,seconds=divmod(remaining,60)
        self.time_edit.setText(f"{minutes:02d}:{seconds:02d}")
        color='#ff4d4f' if remaining==0 else '#f7fbff'
        self.time_edit.setStyleSheet(f"background:transparent;border:0;padding:2px;color:{color};font-size:22px;font-weight:700;")

    def _toggle_timer(self):
        if self.timer_running:
            self._consume_timer_time(); self.timer_running=False; self.timer_last_tick=None; self.timer_button.setText("\u25b6")
        else:
            self._apply_timer_text()
            if self.timer_remaining<=0: return
            now=datetime.now()
            if self.timer_started_at is None: self.timer_started_at=now; self.service.start_time=now
            self.timer_last_tick=now; self.timer_running=True; self.timer_button.setText("\u23f8")
        self.time_edit.setReadOnly(self.timer_running); self._show_timer()

    def _reset_timer(self):
        self.timer_running=False; self.timer_started_at=None; self.timer_last_tick=None; self.timer_remaining=self.countdown_seconds
        self.service.start_time=None; self.time_edit.setReadOnly(False); self.timer_button.setText("\u25b6"); self._show_timer()

    def _consume_timer_time(self):
        if not self.timer_running or self.timer_last_tick is None: return
        now=datetime.now(); self.timer_remaining=max(0,self.timer_remaining-(now-self.timer_last_tick).total_seconds()); self.timer_last_tick=now

    def _update_clock(self):
        if self.timer_running:
            self._consume_timer_time(); self._show_timer()
            if self.timer_remaining<=0:
                self.timer_running=False; self.timer_last_tick=None; self.time_edit.setReadOnly(False); self.timer_button.setText("\u25b6")
        if self.server_error: self._set_listener_status("\u25cf \u76d1\u542c\u5931\u8d25",False)
        elif self.listener_status_error: pass
        elif self.server_thread.is_alive(): self._set_listener_status("\u25cf \u76d1\u542c",True)

    def select_stage(self,index):
        self.selected_stage=index; self.displayed_stage=index
        self.task_title.setText(TASK_NAMES[index]); self.task_copy.setText(TASK_COPY[index])
        self.result_title.setText("\u8fd0\u884c\u65e5\u5fd7")
        self._apply_selection_styles()
        if index in self.stage_images:
            image_path=self.stage_images[index]
            self._show_image(image_path)
            source_size,cached_size=self.image_cache_info[index]
            self.image_path_label.setText(f"\u539f\u56fe\u53ea\u8bfb\uff1a{self.stage_sources[index]}\n\u7f13\u5b58\uff1a{image_path}\n{source_size/1024:.1f}KB \u2192 {cached_size/1024:.1f}KB")
            self.image_label.setEnabled(True)
        else:
            if index in self.stage_sources:
                self.image_path_label.setText(f"\u56fe\u7247\u8bfb\u53d6\u5931\u8d25\uff1a{self.stage_sources[index]}")
            else:
                self.image_path_label.setText("03 \u6a21\u5f0f\u4e0d\u4f7f\u7528\u56fe\u7247")
            self.image_label.setEnabled(False)
        self.start_task_button.setEnabled(not self.active_thread)

    def _resume_auto_stage(self):
        if self.pending_auto_stage is None or self.active_thread: return
        stage=self.pending_auto_stage; self.pending_auto_stage=None; self.result_text.capture_enter=False
        self._append_output(f"[\u7528\u6237\u8f93\u5165] \u56de\u8f66 -> \u5f00\u59cb{stage+1:02d}\n")
        if self.network_queue and self.network_queue[0]==stage: self.network_queue.pop(0)
        self.select_stage(stage); self._execute_stage(stage)

    def _apply_selection_styles(self):
        if getattr(self,'flow_index',None) is not None: return
        for i,button in enumerate(self.buttons):
            border='2px solid #1677ff' if i==self.selected_stage else '1px solid #253552'
            button.setStyleSheet(f'background:#0b1220;border:{border};border-radius:10px;')

    def run_selected_stage(self): self._execute_stage(self.selected_stage)

    def _reload_stage_image(self,index):
        """Re-read E:/photo/color.jpg and rebuild its upload cache."""
        source=INPUT_IMAGE
        cached,source_size,cached_size=cache_image_for_model(source)
        for stage in (0,1):
            self.stage_sources[stage]=source; self.stage_images[stage]=cached
            self.image_cache_info[stage]=(source_size,cached_size)
        stat=source.stat(); self.input_image_signature=(stat.st_mtime_ns,stat.st_size)
        return cached

    def _refresh_live_image(self):
        """Refresh the preview when E:/photo/color.jpg changes."""
        try:
            stat=INPUT_IMAGE.stat(); signature=(stat.st_mtime_ns,stat.st_size)
            if signature==self.input_image_signature: return
            cached=self._reload_stage_image(0)
            if self.selected_stage in (0,1):
                self._show_image(cached)
                source_size,cached_size=self.image_cache_info[self.selected_stage]
                self.image_path_label.setText(f"实时原图：{INPUT_IMAGE}\n上传缓存：{cached}\n{source_size/1024:.1f}KB → {cached_size/1024:.1f}KB")
        except (FileNotFoundError,OSError) as exc:
            self.input_image_signature=None
            if self.selected_stage in (0,1): self.image_path_label.setText(f"图片读取失败：{exc}")

    def _execute_stage(self,index):
        if self.active_thread: return
        self._begin_timer(); self.stage_ok[index]=False; self.start_task_button.setEnabled(False); self._start_flow(index)
        camera_host=self.local_ip_edit.text().strip()
        def captured_image(stage,status):
            status(f"正在向本机拍照服务 {camera_host}:6000 发送 123…")
            hikvision.one_shot(camera_host)
            status("拍照完成，正在读取最新图片…")
            return self._reload_stage_image(stage)
        functions=[lambda callback,status:self.service.identify_stage(captured_image(0,status),callback,status),lambda callback,status:self.service.workflow_stage(captured_image(1,status),callback,status),lambda _callback,_status:self.service.log_stage()]
        self.stream_started=False; self.stage_documents[index]=""
        pending=("\u6b63\u5728\u8c03\u7528\u89c6\u89c9\u6a21\u578b\u2026","\u6b63\u5728\u751f\u6210\u5de5\u4f5c\u6d41\u2026","\u6b63\u5728\u751f\u6210\u4efb\u52a1\u8bb0\u5f55\u2026")[index]
        self._append_output(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] {index+1:02d} \u5de5\u7a0b\u542f\u52a8\n===== {TASK_NAMES[index]} =====\n{pending}\n")
        self.progress.setRange(0,0)
        thread=QThread(self); worker=StageWorker(index,functions[index]); worker.moveToThread(thread); thread.started.connect(worker.run); worker.chunk.connect(self._append_stream); worker.status.connect(self._stage_status); worker.succeeded.connect(self._stage_success); worker.failed.connect(self._stage_error); worker.finished.connect(thread.quit); worker.finished.connect(worker.deleteLater); thread.finished.connect(self._thread_finished); thread.finished.connect(thread.deleteLater); self.active_worker=worker; self.active_thread=thread; thread.start()

    def _thread_finished(self):
        self.active_thread=None; self.active_worker=None; self.select_stage(self.selected_stage)

    def _start_flow(self,index):
        self.flow_index=index; self.flow_phase=0
        self.buttons[index].setText(f"{TASK_NAMES[index]}-\u6267\u884c\u4e2d")
        self.flow_timer.start(); self._animate_flow()
    def _animate_flow(self):
        if self.flow_index is None: return
        color=QColor.fromHsv((265+self.flow_phase)%360,190,245).name(); self.flow_phase+=2
        self.buttons[self.flow_index].setStyleSheet(f'background:#0b1220;border:2px solid {color};border-radius:10px;color:#52c41a;')
    def _stop_flow(self):
        self.flow_timer.stop()
        if self.flow_index is not None: self.buttons[self.flow_index].setText(TASK_NAMES[self.flow_index])
        self.flow_index=None; self._apply_selection_styles()

    def _append_stream(self,index,text):
        if not self.stream_started:
            self.stream_started=True
            self._append_timed_output(f"\u5927\u6a21\u578b\u8f93\u51fa {index+1:02d}")
        self.stage_documents[index]+=text
        self._append_output(text)

    def _stage_status(self,index,text):
        if text.startswith("QWEN_VL_RESULT\x00"):
            _marker,content=text.split("\x00",1)
            if content.strip():
                self.append_log("正在播报视觉大模型识别结果")
                self.voice_client.request_tts(content.strip())
            return
        if text.startswith("MODEL_STREAM_START\x00"):
            _marker,label=text.split("\x00",1)
            self._append_timed_output(label)
            return
        if text.startswith("MODEL_STREAM_CHUNK\x00"):
            _marker,content=text.split("\x00",1)
            self._append_output(content)
            return
        if text.startswith("MODEL_OUTPUT\x00"):
            _marker,label,content=text.split("\x00",2)
            self._append_timed_output(label,content)
            return
        self.append_log(f"{index+1:02d}\uff1a{text}")

    def _append_timed_output(self,label,content=None):
        self._append_output(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] {label}\uff1a\n")
        if content is not None: self._append_output(str(content)+"\n")

    def _stage_success(self,index,value):
        self._stop_flow(); self.stage_ok[index]=True; self.stage_values[index]=value; self.progress.setRange(0,100); self.progress.setValue((index+1)*100//3); self.append_log(f"OK {index+1}")
        if index==0:
            if not self.stage_documents[0]: self.stage_documents[0]=value; self._append_timed_output("\u5927\u6a21\u578b\u8f93\u51fa 01",value)
        elif index==1:
            workflow,command,path=value
            # Preserve the complete raw streamed model response; use the returned
            # response only when the provider did not stream any content.
            if not self.stage_documents[1]: self.stage_documents[1]=workflow; self._append_timed_output("\u5927\u6a21\u578b\u8f93\u51fa 02",workflow)
            self.path_label.setText(f"{path}\n{command}")
            self._append_timed_output("\u4efb\u52a1\u6307\u4ee4",command)
            if self.voice_triggered_stage==1:
                with self.pending_robot_command_lock:
                    self.pending_robot_command=command
                self.append_log("语音任务二分析完成，发送信息已存储，正在启动机械臂工程")
                self.voice_triggered_stage=None
                self._start_robot_project()
            else:
                self._send_task_command(command)
            self.append_log("02 \u6307\u4ee4\u5947\u5076\u524d\u7f00\uff1a"+";".join(f"{1 if index%2 else 2}{value}" for index,value in enumerate((item for item in command.split(";") if item),1))+";")
        else:
            path,command=value
            self.stage_documents[2]=Path(path).read_text(encoding="utf-8-sig")
            self._append_output(self.stage_documents[2]+"\n")
            self.path_label.setText(str(path))
            self._append_timed_output("\u4efb\u52a1\u6307\u4ee4",command)
        if index==2:
            self._append_output(f'\n\u65e5\u5fd7\u4fdd\u5b58\u5230\uff1a{Path(path).resolve()}\n')
        self.start_task_button.setEnabled(True)
        if index in (0,1):
            next_stage=index+1; self.pending_auto_stage=next_stage
            prompt=("\u8bf7\u952e\u5165\u56de\u8f66\u5f00\u59cb02" if next_stage==1 else "\u8bf7\u952e\u5165\u56de\u8f66\u5f00\u59cb03")
            self.stage_documents[index]+="\n\n"+prompt
            self._append_output("\n\n"+prompt+"\n"); self.result_text.capture_enter=True; self.result_text.setFocus()
            if self.network_request and self.network_request['command']=='auto':
                if index==1:
                    self.network_request['response']=value[1]; self.network_request['event'].set(); self.network_request=None
                return
        if self.network_request: QTimer.singleShot(100,self._run_next_network_stage)

    def _stage_error(self,index,error):
        if self.voice_triggered_stage==index: self.voice_triggered_stage=None
        self._stop_flow(); self.stage_ok[index]=False; self.progress.setRange(0,100)
        self.stage_documents[index]=f"\u4efb\u52a1\u5931\u8d25\uff0c\u53ef\u91cd\u8bd5\u3002\n{error}"
        self._append_output("\n"+self.stage_documents[index]+"\n")
        self.start_task_button.setEnabled(True); self.append_log(f"ERROR {index+1}: {error}")
        if self.network_request:
            self.network_queue.clear(); self.network_request['response']=f"Process failure: {error}"; self.network_request['event'].set(); self.network_request=None

    def _load_dropped_image(self,path):
        if self.selected_stage not in self.stage_images: return
        candidate=Path(path)
        if candidate.suffix.lower() not in ('.png','.jpg','.jpeg','.webp','.bmp','.tif','.tiff') or not candidate.is_file(): return
        try:
            cached,source_size,cached_size=cache_image_for_model(candidate)
        except Exception as exc:
            self.append_log(f"\u56fe\u7247\u538b\u7f29\u5931\u8d25\uff1a{exc}"); return
        if self._show_image(cached):
            self.stage_sources[self.selected_stage]=candidate.resolve(); self.stage_images[self.selected_stage]=cached
            self.image_cache_info[self.selected_stage]=(source_size,cached_size)
            self.image_path_label.setText(f"\u539f\u56fe\u53ea\u8bfb\uff1a{candidate.resolve()}\n\u7f13\u5b58\uff1a{cached}\n{source_size/1024:.1f}KB \u2192 {cached_size/1024:.1f}KB")
            self.append_log(f"\u56fe\u7247\u5df2\u538b\u7f29\u5e76\u7f13\u5b58\uff1a{cached_size/1024:.1f}KB")
    def _show_image(self,path):
        pix=QPixmap(str(path))
        if pix.isNull(): return False
        self._source_pixmap=pix; self._update_image(); return True
    def showEvent(self,event): super().showEvent(event); QTimer.singleShot(0,self._update_image)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'_source_pixmap'): self._update_image()
    def _update_image(self): self.image_label.setPixmap(self._source_pixmap.scaled(self.image_label.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
    def append_log(self,message):
        line=f"[{datetime.now():%H:%M:%S}] {message}"
        self.stage_documents[2]+=("\n" if self.stage_documents[2] else "")+line
        self._append_output(line+"\n")
    def _append_output(self,text):
        self.output_document+=text
        self.result_text.moveCursor(QTextCursor.MoveOperation.End); self.result_text.insertPlainText(text); self.result_text.ensureCursorVisible()
    def closeEvent(self,event):
        self.voice_client.stop()
        self.server.shutdown()
        if self.network_request: self.network_request['response']='Process failure: application closed'; self.network_request['event'].set()
        event.accept()

def main():
    app=QApplication(sys.argv); app.setStyle('Fusion'); app.setStyleSheet(STYLE); app.setFont(QFont('Microsoft YaHei UI',10)); window=MainWindow(); window.show(); return app.exec()
if __name__=='__main__': raise SystemExit(main())
