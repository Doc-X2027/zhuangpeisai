"""Competition workflow business layer shared by GUI and TCP."""
from __future__ import annotations
import json
import hashlib
import os
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
import prompt
import read_json

BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys,"_MEIPASS",BASE_DIR))
IDENTIFY_IMAGE = RESOURCE_DIR / "image" / "1.png"
WORKFLOW_IMAGE = RESOURCE_DIR / "image" / "2.png"
LOG_PATH = BASE_DIR / "机车装配小队比赛文档日志.txt"
IMAGE_CACHE_DIR = BASE_DIR / "image_cache"
MODEL_IMAGE_LIMIT = 1_000_000
TASK_COMMAND = "1;3;4;1;2;5;5;6;3;2;6;4;7;1;8;2;9;3;"
IDENTIFY_PROMPT = (
    "请用200字描述任务卡中的每个元素，一共有六个，可能有三通管、齿轮、伞、"
    "文件夹等（图片里没有则不用说明）。请保证物体和数量识别正确。"
)

def compact_json_text(value: str) -> str:
    try:
        return json.dumps(json.loads(value), ensure_ascii=False, separators=(",", ":"))
    except (TypeError, json.JSONDecodeError):
        return " ".join(str(value).split())

def cache_image_for_model(source_path: Path, limit: int = MODEL_IMAGE_LIMIT) -> tuple[Path,int,int]:
    """Create a model/preview cache under limit bytes; never modify source_path."""
    from io import BytesIO
    from PIL import Image,ImageOps
    source_path=Path(source_path).resolve()
    if not source_path.is_file(): raise FileNotFoundError(f"图片不存在：{source_path}")
    source_bytes=source_path.read_bytes(); source_size=len(source_bytes)
    digest=hashlib.sha256(source_bytes).hexdigest()[:16]
    IMAGE_CACHE_DIR.mkdir(parents=True,exist_ok=True)
    supported={".jpg",".jpeg",".png",".webp"}
    if source_size<limit and source_path.suffix.lower() in supported:
        cached=IMAGE_CACHE_DIR/f"{source_path.stem}_{digest}{source_path.suffix.lower()}"
        if not cached.is_file() or cached.stat().st_size!=source_size: cached.write_bytes(source_bytes)
        return cached,source_size,cached.stat().st_size
    cached=IMAGE_CACHE_DIR/f"{source_path.stem}_{digest}.jpg"
    if cached.is_file() and cached.stat().st_size<limit: return cached,source_size,cached.stat().st_size
    image=ImageOps.exif_transpose(Image.open(BytesIO(source_bytes)))
    if image.mode!="RGB":
        background=Image.new("RGB",image.size,"white")
        if "A" in image.getbands(): background.paste(image,mask=image.getchannel("A"))
        else: background.paste(image.convert("RGB"))
        image=background
    quality=90
    while True:
        output=BytesIO(); image.save(output,"JPEG",quality=quality,optimize=True)
        data=output.getvalue()
        if len(data)<limit: break
        if quality>50: quality-=10
        else:
            width,height=image.size
            image=image.resize((max(1,int(width*.85)),max(1,int(height*.85))),Image.Resampling.LANCZOS)
    cached.write_bytes(data)
    return cached,source_size,len(data)

@dataclass
class CompetitionResult:
    identification: str = ""
    workflow: str = ""
    command_result: str = ""
    workflow_path: Path | None = None
    log_path: Path | None = None
    robot_visual_log: list[str] | None = None

class CompetitionService:
    """Thread-safe implementation of the three competition stages."""
    def __init__(self, client_addr: tuple[str, int] = ("GUI", 0)) -> None:
        self.client_addr = client_addr
        self.start_time = datetime.now()
        self.result = CompetitionResult()
        self.result.robot_visual_log = []
        self._lock = threading.RLock()

    def record_robot_visual_log(self, text: str) -> str:
        line=f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {text.rstrip()}"
        with self._lock:
            self.result.robot_visual_log.append(line)
        return line

    def identify_stage(self, image_path: Path = IDENTIFY_IMAGE, on_chunk=None, on_status=None) -> str:
        if not image_path.is_file():
            raise FileNotFoundError(f"任务图片不存在：{image_path}")
        value = prompt.identify_obj(str(image_path), IDENTIFY_PROMPT, on_chunk=on_chunk, on_status=on_status)
        if not value or not value.strip():
            raise RuntimeError("任务卡元素识别失败：模型未返回内容")
        with self._lock:
            self.result.identification = value.strip()
        return self.result.identification

    def workflow_stage(self, image_path: Path = WORKFLOW_IMAGE, on_chunk=None, on_status=None) -> tuple[str, str, Path]:
        if not image_path.is_file():
            raise FileNotFoundError(f"工作流图片不存在：{image_path}")
        path = BASE_DIR / f"workflow_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        workflow = prompt.generate_workflow_json(str(image_path), str(path), on_chunk=on_chunk, on_status=on_status)
        if not workflow:
            raise RuntimeError("装配工作流生成失败")
        parsed = json.loads(workflow)
        if not isinstance(parsed.get("assembly_sequence"), list):
            raise ValueError("工作流 JSON 缺少 assembly_sequence 数组")
        command = TASK_COMMAND
        with self._lock:
            self.result.workflow = json.dumps(parsed, ensure_ascii=False, indent=2)
            self.result.command_result = command
            self.result.workflow_path = path
        return self.result.workflow, command, path

    def log_stage(self) -> tuple[Path, str]:
        result = self.result
        now = datetime.now()
        start_time=self.start_time or now
        identification=result.identification or "未运行 01，暂无识别结果"
        workflow=result.workflow or "未运行 02，暂无装配工作流"
        command=result.command_result or "暂无执行指令"
        robot_visual_log="\n".join(result.robot_visual_log or []) or "暂无回传数据"
        client = f"{self.client_addr[0]}:{self.client_addr[1]}" if self.client_addr[1] else self.client_addr[0]
        content = (
            "机车装配小队比赛文档日志\n" + "=" * 32 + "\n"
            f"工程开始时间：{start_time:%Y年%m月%d日 %H:%M:%S}\n"
            f"客户端：{client}\n触发命令：auto\n\n"
            f"【任务卡元素识别】\n{identification}\n\n"
            f"【装配工作流（大模型原始输出）】\n{compact_json_text(workflow)}\n\n"
            f"【下发执行序列】\n{command.strip()}\n\n"
            f"【机器人与视觉软件日志】\n{robot_visual_log}\n"
        )
        LOG_PATH.write_text(content, encoding="utf-8-sig")
        with self._lock:
            self.result.log_path = LOG_PATH
        return LOG_PATH, command

    def run_all(self, status: Callable[[str], None] | None = None) -> CompetitionResult:
        notify = status or (lambda _message: None)
        notify("正在识别任务卡")
        self.identify_stage()
        notify("正在生成装配工作流")
        self.workflow_stage()
        notify("正在生成比赛日志")
        self.log_stage()
        notify("三阶段任务已完成")
        return self.result
