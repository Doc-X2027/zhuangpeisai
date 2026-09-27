"""Qt client for the remote ARM speech service HTTP/WebSocket protocol."""
from __future__ import annotations

import json
import uuid
from urllib.parse import urlparse, urlunparse

from PySide6.QtCore import QByteArray, QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkProxy, QNetworkReply, QNetworkRequest
from PySide6.QtWebSockets import QWebSocket


def normalize_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if not value:
        raise ValueError("语音服务地址不能为空")
    if "://" not in value:
        value = "http://" + value
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("语音服务地址必须是 HTTP/HTTPS URL")
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))


def events_url(base_url: str) -> str:
    parsed = urlparse(normalize_base_url(base_url))
    scheme = "wss" if parsed.scheme == "https" else "ws"
    path = parsed.path.rstrip("/") + "/v1/events"
    return urlunparse((scheme, parsed.netloc, path, "", "", ""))


def parse_event(message: str) -> tuple[str, dict]:
    payload = json.loads(message)
    if not isinstance(payload, dict):
        raise ValueError("语音事件必须是 JSON 对象")
    event_type = payload.get("event") or payload.get("type")
    if not isinstance(event_type, str) or not event_type:
        raise ValueError("语音事件缺少 event/type")
    return event_type, payload


class RemoteSpeechClient(QObject):
    """Discover a remote service, reconnect automatically and expose ASR results."""

    status_changed = Signal(str, bool)
    recognition_received = Signal(str, object)
    event_received = Signal(str, object)
    error_received = Signal(str)
    tts_finished = Signal(str, bool)

    def __init__(self, base_url: str, parent: QObject | None = None, probe_interval_ms: int = 2000,
                 auto_listen: bool = False, events_enabled: bool = True):
        super().__init__(parent)
        self.base_url = normalize_base_url(base_url)
        self._stopped = True
        self._health_pending = False
        self._connected = False
        self._service_ready = False
        self._asr_pending = False
        self._tts_pending = False
        self._next_wakeup_required = True
        self.auto_listen = auto_listen
        self.events_enabled = events_enabled

        self.http = QNetworkAccessManager(self)
        self.http.setProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
        self.socket = QWebSocket("ARM speech events")
        self.socket.setProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
        self.socket.connected.connect(self._on_connected)
        self.socket.disconnected.connect(self._on_disconnected)
        self.socket.textMessageReceived.connect(self._on_message)
        self.socket.errorOccurred.connect(self._on_socket_error)

        self.probe_timer = QTimer(self)
        self.probe_timer.setInterval(max(500, probe_interval_ms))
        self.probe_timer.timeout.connect(self._probe)

    def start(self) -> None:
        self._stopped = False
        self.probe_timer.start()
        self._set_status("正在等待 ARM 语音服务…", False)
        self._probe()

    def stop(self) -> None:
        self._stopped = True
        self._asr_pending = False
        self.probe_timer.stop()
        self.socket.close()
        self._connected = False
        self._service_ready = False

    def set_base_url(self, value: str) -> None:
        new_url = normalize_base_url(value)
        if new_url == self.base_url:
            return
        self.socket.close()
        self._connected = False
        self._service_ready = False
        self.base_url = new_url
        if not self._stopped:
            self._set_status("正在等待 ARM 语音服务…", False)
            QTimer.singleShot(0, self._probe)

    def request_asr(self, wakeup_required: bool | None = None) -> None:
        if self._asr_pending:
            return
        if not self._service_ready:
            self.error_received.emit("语音服务尚未连接")
            return
        if wakeup_required is None:
            # Use short-utterance ASR and let the Windows client match the exact
            # phrase.  The packaged keyword table accepts several homophones,
            # so it cannot enforce an exact "小聚同学" match by itself.
            wakeup_required = False
        self._next_wakeup_required = True
        payload = {
            "request_id": str(uuid.uuid4()),
            "mode": "live_capture",
            "wakeup_required": wakeup_required,
            "start_timeout_s": 2.0,
            "max_record_seconds": 6.0,
            "vad_threshold": 0.5,
            "language": "zh-CN",
        }
        request = QNetworkRequest(QUrl(self.base_url + "/v1/asr"))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        # The real ARM endpoint intentionally keeps this request open while it
        # waits for the wake word.  A fixed transfer timeout would turn normal
        # silence into a false disconnect/reconnect cycle.
        request.setTransferTimeout(0)
        self._asr_pending = True
        reply = self.http.post(request, QByteArray(json.dumps(payload).encode("utf-8")))
        reply.finished.connect(lambda reply=reply: self._handle_asr_reply(reply))
        if not self.auto_listen:
            self._set_status("语音识别中…", True)

    def request_tts(self, text: str) -> None:
        """Speak text through the ARM service and resume ASR after playback."""
        text = str(text).strip()
        if not text:
            return
        if not self._service_ready:
            self.error_received.emit("语音服务尚未连接，无法播报")
            self.tts_finished.emit(text, False)
            return
        payload = {
            "request_id": str(uuid.uuid4()),
            "text": text,
            "backend": "piper",
            "voice": "default",
            "interrupt_policy": "cancel_on_wakeup",
        }
        request = QNetworkRequest(QUrl(self.base_url + "/v1/tts"))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        request.setTransferTimeout(0)
        self._tts_pending = True
        reply = self.http.post(request, QByteArray(json.dumps(payload, ensure_ascii=False).encode("utf-8")))
        reply.finished.connect(lambda reply=reply, text=text: self._handle_tts_reply(reply, text))

    def pause_auto_listen(self) -> None:
        """Stop starting new ASR requests while a voice-triggered task is running."""
        self.auto_listen = False

    def resume_auto_listen(self) -> None:
        """Resume wake-word listening after task-result playback has finished."""
        self.auto_listen = True
        self._schedule_asr()

    def listen_for_command_after_tts(self, text: str) -> None:
        """Acknowledge a wake word, then capture one command without another wake word."""
        self._next_wakeup_required = False
        self.request_tts(text)

    def _handle_tts_reply(self, reply, text: str) -> None:
        ok = False
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self.error_received.emit(f"语音播报失败：{reply.errorString()}")
                return
            payload = json.loads(bytes(reply.readAll()).decode("utf-8"))
            ok = isinstance(payload, dict) and bool(payload.get("ok"))
            if not ok:
                self.error_received.emit(f"语音播报失败：{payload.get('message', '未知错误')}")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self.error_received.emit(f"语音播报响应无效：{exc}")
        finally:
            self._tts_pending = False
            reply.deleteLater()
            self.tts_finished.emit(text, ok)
            self._schedule_asr(150)

    def _probe(self) -> None:
        if self._stopped or self._health_pending or self._connected:
            return
        self._health_pending = True
        reply = self.http.get(QNetworkRequest(QUrl(self.base_url + "/health")))
        reply.finished.connect(lambda reply=reply: self._handle_health(reply))

    def _handle_health(self, reply) -> None:
        self._health_pending = False
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self._service_ready = False
                self._set_status("等待 ARM 语音服务", False)
                return
            payload = json.loads(bytes(reply.readAll()).decode("utf-8"))
            if not isinstance(payload, dict) or not payload.get("ready"):
                self._service_ready = False
                message = payload.get("message", "服务未就绪") if isinstance(payload, dict) else "响应格式错误"
                self._set_status(f"ARM 语音服务未就绪：{message}", False)
                return
            self._service_ready = True
            if self.events_enabled:
                self._set_status("已发现 ARM 语音服务，正在连接事件通道…", True)
                self.socket.open(QUrl(events_url(self.base_url)))
            else:
                self._connected = True
                self._set_status("语音服务已连接（HTTP 连续识别）", True)
            self._schedule_asr()
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._set_status(f"ARM 语音服务响应无效：{exc}", False)
        finally:
            reply.deleteLater()

    def _handle_asr_reply(self, reply) -> None:
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self._service_ready = False
                self._connected = False
                self._set_status("语音服务已断开，等待重连…", False)
                self.error_received.emit(f"语音识别请求失败：{reply.errorString()}")
                QTimer.singleShot(1000, self._probe)
                return
            payload = json.loads(bytes(reply.readAll()).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("响应不是 JSON 对象")
            if not payload.get("ok"):
                error_code = payload.get("error_code", "ASR_FAILED")
                if not (self.auto_listen and error_code in (
                    "WAKEUP_TIMEOUT", "ASR_TIMEOUT", "NO_SPEECH_DETECTED"
                )):
                    self.error_received.emit(f"{error_code}：{payload.get('message', '语音识别失败')}")
                return
            digest = payload.get("result_digest") or {}
            text = digest.get("instruction") or ""
            if text:
                self.recognition_received.emit(text, payload)
            self._set_status("语音服务已连接", True)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self.error_received.emit(f"语音服务响应无效：{exc}")
        finally:
            self._asr_pending = False
            reply.deleteLater()
            self._schedule_asr(300)

    def _on_connected(self) -> None:
        self._connected = True
        self._set_status("语音服务已连接", True)
        self._schedule_asr()

    def _on_disconnected(self) -> None:
        self._connected = False
        if not self._stopped:
            self._set_status("语音事件通道已断开，正在重连…", self._service_ready)
            QTimer.singleShot(500, self._probe)

    def _on_socket_error(self, _error) -> None:
        if not self._stopped:
            self._set_status("语音 HTTP 可用，事件通道等待重连…", self._service_ready)

    def _on_message(self, message: str) -> None:
        try:
            event_type, payload = parse_event(message)
            self.event_received.emit(event_type, payload)
            if event_type == "asr.final":
                text = payload.get("text") or (payload.get("result_digest") or {}).get("instruction") or ""
                if text:
                    self.recognition_received.emit(text, payload)
            elif event_type == "asr.failed":
                self.error_received.emit(f"{payload.get('error_code', 'ASR_FAILED')}：{payload.get('message', '语音识别失败')}")
        except (json.JSONDecodeError, ValueError) as exc:
            self.error_received.emit(f"忽略无效语音事件：{exc}")

    def _set_status(self, text: str, connected: bool) -> None:
        self.status_changed.emit(text, connected)

    def _schedule_asr(self, delay_ms: int = 0) -> None:
        if not self.auto_listen or self._stopped or not self._service_ready or self._asr_pending or self._tts_pending:
            return
        QTimer.singleShot(delay_ms, self._auto_request_asr)

    def _auto_request_asr(self) -> None:
        if self.auto_listen and not self._stopped and self._service_ready and not self._asr_pending and not self._tts_pending:
            self.request_asr()
