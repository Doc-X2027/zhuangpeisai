from openai import OpenAI
import os
import json
import base64
import time
import httpx
from io import BytesIO

def _http_client():
    """Use a direct connection unless an explicit proxy is requested."""
    proxy = os.environ.get("DASHSCOPE_PROXY", "").strip()
    if proxy:
        return httpx.Client(proxy=proxy, timeout=90.0)
    return httpx.Client(trust_env=False, timeout=90.0)

client = OpenAI(
    # 固定使用指定的阿里云百炼 API Key，不允许环境变量覆盖。
    api_key="sk-ws-H.PLIXIHM.bckZ.MEUCIQCgUtsCT_6IXyYiM8qIgPGVr7jOqpPb7P6MfDiRyzEGQAIgblsHPETDJ0OhyTUEWKGT6eYf0ZYbLcC1oTyxogyW-Ss",
    base_url=os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    http_client=_http_client(),
    timeout=90.0,
    max_retries=2,
)

def _prepare_image(image_path):
    """Reduce upload and vision-token cost without changing the source file."""
    import mimetypes
    raw= open(image_path,"rb").read()
    mime_type=mimetypes.guess_type(image_path)[0] or "image/jpeg"
    max_edge=int(os.environ.get("MODEL_IMAGE_MAX_EDGE","2560"))
    if len(raw)<1_000_000:
        return raw,mime_type,len(raw)
    try:
        from PIL import Image
        image=Image.open(BytesIO(raw)); image.thumbnail((max_edge,max_edge))
        if image.mode not in ("RGB","L"): image=image.convert("RGB")
        output=BytesIO(); image.save(output,"JPEG",quality=88,optimize=True)
        return output.getvalue(),"image/jpeg",len(raw)
    except Exception:
        return raw,mime_type,len(raw)


def identify_obj(image_path, text, on_chunk=None, on_status=None, report_reasoning=False):
    """识别图片内容，返回模型描述文本"""
    import mimetypes

    # Image preview is handled by the Qt application.
    image_bytes,mime_type,source_size=_prepare_image(image_path)
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    if on_status: on_status(f"图片处理完成：{source_size/1024:.1f}KB → 上传 {len(image_bytes)/1024:.1f}KB")
    
    # 根据文件扩展名自动推断 MIME 类型，默认为 jpeg
    print("当前时间：", time.time())
    print(f"正在识别图片: {image_path}")

    # 调用多模态视觉模型
    try:
        completion = client.chat.completions.create(
            model="qwen-vl-plus",  # 支持图片识别的视觉语言模型
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {"type": "image_url", "image_url": f"data:{mime_type};base64,{base64_image}"}
                ]
            }], stream=True
        )
        result=""; reasoning_started=False
        for chunk in completion:
            if not chunk.choices: continue
            delta=chunk.choices[0].delta
            reasoning=getattr(delta,"reasoning_content",None)
            if report_reasoning and reasoning:
                if not reasoning_started and on_status:
                    on_status("MODEL_STREAM_START\x00视觉大模型思考过程"); reasoning_started=True
                if on_status: on_status("MODEL_STREAM_CHUNK\x00"+str(reasoning))
            content=getattr(delta,"content",None)
            if content:
                content=str(content); result+=content
                if on_chunk: on_chunk(content)
        print(f"识别结果: {result}")
        if on_status:
            on_status("QWEN_VL_RESULT\x00" + result)
        return result
    except Exception as e:
        if isinstance(e, httpx.TimeoutException):
            detail = "百炼 API 请求超时，请检查网络或 DASHSCOPE_PROXY 配置"
        elif isinstance(e, httpx.ConnectError):
            detail = "无法连接百炼 API，请检查网络；默认已绕过系统代理，如需代理请设置 DASHSCOPE_PROXY"
        else:
            detail = str(e)
        print(f"图片识别失败: {detail}")
        raise RuntimeError(detail) from e
    
def generate_workflow_json(image_path, file_name, on_chunk=None, on_status=None):
    def vision_status(text):
        if not on_status: return
        on_status(text if text.startswith(("MODEL_OUTPUT\x00", "QWEN_VL_RESULT\x00")) else "文字识别："+text)
    if on_status: on_status("MODEL_STREAM_START\x00图片文字识别")
    task_description=identify_obj(
        image_path,
        "识别图片中的A4纸上的文字内容，只输出你读取到的文字不输出其他内容",
        on_chunk=(lambda text:on_status("MODEL_STREAM_CHUNK\x00"+text)) if on_status else None,
        on_status=vision_status if on_status else None,
        report_reasoning=True,
    )
    if not task_description.strip():
        task_description="图片未识别到可用文字，使用系统预设任务指令生成顺序装配工作流"
        if on_status: on_status("图片文字识别结果为空，已切换到预设任务指令")
    instruction=("你是一个具身智能任务编排助手。请根据任务描述生成 JSON 工作流。\n"
        f"任务描述：{task_description}\n"
        "严格规则：\n"
        "1. 根对象只能包含 task_id、task_description、execution_mode、assembly_sequence 四个字段。\n"
        "2. task_id 必须为 pick_place_colors，execution_mode 必须为 sequential。\n"
        "3. assembly_sequence 中每项只能包含 step、operation、object_color、action_description。\n"
        "4. operation 只允许字符串 pick 或 place，绝对禁止 pick_and_place、pickplace、move 等任何其他值。\n"
        "5. 每个抓放必须拆成两个独立步骤：奇数步骤为 pick，偶数步骤为 place；step 从 1 连续递增。\n"
        "6. object_color 只允许 red、orange、yellow、green、blue、purple、pink、cyan、brown。"
        "颜色数字编码固定为 red=1、orange=2、yellow=3、green=4、blue=5、purple=6、pink=7、cyan=8、brown=9。\n"
        "7. 任务可在原始六组抓放（12 步）后增加句段，例如‘把粉色方块放到红色方块上’。"
        "此类表述中，前一个颜色是待抓取物块 obj；后一个颜色指向该颜色物块在前文中已被放置的托盘，必须沿用该托盘的颜色作为 target，"
        "不得把被引用物块自身的颜色直接当作 target。必须先从前文找到‘后一颜色物块 -> 它的放置托盘’的对应关系。\n"
        "8. 每个新增句段只增加两个步骤：第一步 pick 的 object_color 是 obj 颜色，第二步 place 的 object_color 是解析后的 target 托盘颜色。"
        "如原任务有 12 步，一个新增句段的结果必须为 14 步；若分别新增粉色、青色、棕色三个物块的抓放句段，则每个句段各增加两步。\n"
        "9. 只输出合法 JSON，不得输出解释、注释、Markdown 或代码围栏。\n"
        "格式示例：\n"
        '{"task_id":"pick_place_colors","task_description":"移动红色方块到蓝色盘中",'
        '"execution_mode":"sequential","assembly_sequence":['
        '{"step":1,"operation":"pick","object_color":"red","action_description":"pick red block(s)"},'
        '{"step":2,"operation":"place","object_color":"blue","action_description":"place in blue plate"}]}\n'
        "间接指代示例：若前文是‘把红色方块放到蓝色托盘’，后文新增‘把粉色方块放到红色方块上’，"
        "则新增两步必须是 pick pink 和 place blue；即 obj=pink(编码7)、target=blue(编码5)，绝不是 target=red。")

    def parse_and_validate(response):
        cleaned=response.strip()
        if cleaned.startswith("```"):
            cleaned=cleaned.split("\n",1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.rstrip().endswith("```"): cleaned=cleaned.rstrip()[:-3]
        first,last=cleaned.find("{"),cleaned.rfind("}")
        if first<0 or last<first: raise ValueError("未返回 JSON 对象")
        cleaned=cleaned[first:last+1]; parsed=json.loads(cleaned)
        root_keys={"task_id","task_description","execution_mode","assembly_sequence"}
        if not isinstance(parsed,dict) or set(parsed)!=root_keys: raise ValueError("根对象字段必须且只能是四个规定字段")
        if parsed["task_id"]!="pick_place_colors": raise ValueError("task_id 必须为 pick_place_colors")
        if parsed["execution_mode"]!="sequential": raise ValueError("execution_mode 必须为 sequential")
        if not isinstance(parsed["task_description"],str): raise ValueError("task_description 必须是字符串")
        sequence=parsed["assembly_sequence"]
        if not isinstance(sequence,list) or not sequence: raise ValueError("assembly_sequence 必须是非空数组")
        item_keys={"step","operation","object_color","action_description"}
        colors={"red","orange","yellow","green","blue","purple","pink","cyan","brown"}
        for position,item in enumerate(sequence,1):
            if not isinstance(item,dict) or set(item)!=item_keys: raise ValueError(f"第 {position} 步字段不符合规定")
            expected="pick" if position%2 else "place"
            if item["step"]!=position: raise ValueError(f"第 {position} 步的 step 必须为 {position}")
            if item["operation"]!=expected: raise ValueError(f"第 {position} 步 operation 必须为 {expected}，不能为 {item['operation']}")
            if item["object_color"] not in colors: raise ValueError(f"第 {position} 步颜色无效：{item['object_color']}")
            if not isinstance(item["action_description"],str): raise ValueError(f"第 {position} 步 action_description 必须是字符串")
        return cleaned,parsed

    parsed=cleaned=None; last_error=None
    for attempt in range(2):
        full_response=""
        request_text=instruction if attempt==0 else instruction+f"\n上一次输出校验失败：{last_error}。请彻底重写，不要沿用错误 operation。"
        completion=client.chat.completions.create(
            model="qwen3.6-plus",
            messages=[{"role":"system","content":"你是一个 JSON 生成专家，只输出纯 JSON 内容。"},{"role":"user","content":request_text}],
            extra_body={"enable_thinking":False},stream=True)
        for chunk in completion:
            if not chunk.choices: continue
            delta=chunk.choices[0].delta
            if getattr(delta,"content",None):
                full_response+=delta.content
                if on_chunk: on_chunk(delta.content)
        try:
            cleaned,parsed=parse_and_validate(full_response); break
        except (ValueError,TypeError,json.JSONDecodeError) as exc:
            last_error=str(exc)
            if on_status: on_status(f"工作流模型第 {attempt+1} 次输出被拒绝：{last_error}")
            if attempt==0 and on_status: on_status("MODEL_OUTPUT\x00无效工作流输出（已拒绝）\x00"+full_response)
    if parsed is None: raise ValueError(f"模型连续两次未返回合规工作流：{last_error}")
    if on_status: on_status("工作流模型输出校验通过")
    
    # 保存完整回复到workflow.json
    # 生成 JSON 文件
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    return cleaned


# 如果直接运行此脚本，则执行生成
if __name__ == "__main__":
    file_name = "workflow"
    image_path = os.path.join(os.path.dirname(__file__), 'image', '2.png')
    generate_workflow_json(image_path, file_name)
