from openai import OpenAI
import os
import json
import base64
import time

client = OpenAI(
    # 如果没有配置环境变量，请用阿里云百炼API Key替换：api_key="sk-xxx"
    api_key="sk-ws-H.ERYDIEH.BJc0.MEUCIF9C7kE6FUzROlva1h0Tqn9m8a8Y5U7elzkXNqXIiAM0AiEA0D9kry56N_L3RZE_92CeFn0cKSNcU0R6Dgl2_jyhSgw",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


def identify_obj(image_path, text):
    """识别图片内容，返回模型描述文本"""
    import mimetypes

    # 先展示图片 5 秒，然后自动关闭
    try:
        import cv2
        img = cv2.imread(image_path)
        if img is not None:
            display_size = (800, 600)
            display_img = cv2.resize(img, display_size, interpolation=cv2.INTER_AREA)

            window_name = "识别图片"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, *display_size)
            cv2.imshow(window_name, display_img)
            cv2.waitKey(5000)
            cv2.destroyAllWindows()
        else:
            print(f"无法读取图片文件: {image_path}")
    except Exception as e:
        print(f"显示图片失败: {e}")

    with open(image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')
    
    # 根据文件扩展名自动推断 MIME 类型，默认为 jpeg
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "image/jpeg"

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
            }]
        )
        result = completion.choices[0].message.content
        print(f"识别结果: {result}")
        return result
    except Exception as e:
        print(f"图片识别失败: {e}")
        raise
    
def generate_workflow_json(image_path, file_name):
    # 第一步：调用视觉模型识别图片内容，得到任务描述
    print("第一步：识别图片中的任务...")
    task_description = identify_obj(image_path, text = "识别图片中的A4纸上的文字内容，只输出你读取到的文字不输出其他内容")

    # 第二步：将图片描述作为任务，调用文本模型生成工作流 JSON
    prompt = """
    你是一个具身智能任务编排助手。请根据以下任务描述，生成一个 JSON 格式的工作流文件。

    任务描述：
    """ + task_description + """
    要求：
    - task_id 为 "pick_place_colors"
    - task_description 为任务描述
    - execution_mode 为 "sequential"
    - assembly_sequence 按顺序包含多个 pick和place 操作，颜色次序和step步数依照任务描述
    - 每个 step 包含 step, operation, object_color, action_description
    注意：
    1.请严格按以下 JSON 结构生成文件,只返回合法的 JSON 对象，不要修改字段名，不要添加额外字
    2.以下示例仅参考结构，颜色次序和数量一定要以任务描述为准，忘记下面示例中的顺序和step数量
    3.不要在任何位置添加注释、解释、前缀或后缀文字
    4.输出必须以 { 字符开头，以 } 字符结尾
    示例：
    {
      "task_id": "pick_place_colors",
      "task_description": "移动机械臂依次抓取红、绿、蓝、黄、橙、紫色方块,分别放入蓝、黄、红、绿、紫、橙色盘中",
      "execution_mode": "sequential",
      "assembly_sequence": [
        { "step": 1, "operation": "pick", "object_color": "red", "action_description": "pick red block(s)" },
        { "step": 2, "operation": "place", "object_color": "blue", "action_description": "place in blue plate" },
        { "step": 3, "operation": "pick", "object_color": "green", "action_description": "pick green block(s)" },
        { "step": 4, "operation": "place", "object_color": "yellow", "action_description": "place in yellow plate" },
        { "step": 5, "operation": "pick", "object_color": "blue", "action_description": "pick blue block(s)" },
        { "step": 6, "operation": "place", "object_color": "red", "action_description": "place in red plate" },
        { "step": 7, "operation": "pick", "object_color": "yellow", "action_description": "pick yellow block(s)" },
        { "step": 8, "operation": "place", "object_color": "green", "action_description": "place in green plate" },
        { "step": 9, "operation": "pick", "object_color": "orange", "action_description": "pick orange block(s)" },
        { "step": 10, "operation": "place", "object_color": "purple", "action_description": "place in purple plate" },
        { "step": 11, "operation": "pick", "object_color": "purple", "action_description": "pick purple block(s)" },
        { "step": 12, "operation": "place", "object_color": "orange", "action_description": "place in orange plate" }
      ]
    }

    直接输出我需要的JSON，不要其它文字。
    """
    print("\n第二步：请求大模型生成 JSON 工作流...")
    print("任务描述:", task_description)

    completion = client.chat.completions.create(
        model="qwen3.6-plus",  # 您可以按需更换为其它深度思考模型
        messages=[
            {"role": "system", "content": "你是一个 JSON 生成专家，只输出纯 JSON 内容。"},
                {"role": "user", "content": prompt}
        ],
        extra_body={"enable_thinking": False},
        stream=True
    )
    is_answering = False  # 是否进入回复阶段
    full_response = ""
    print("\n" + "=" * 20 + "思考过程" + "=" * 20)
    for chunk in completion:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
            if not is_answering:
                print(delta.reasoning_content, end="", flush=True)
        if hasattr(delta, "content") and delta.content:
            if not is_answering:
                print("\n" + "=" * 20 + "完整回复" + "=" * 20)
                is_answering = True
            print(delta.content, end="", flush=True)
            full_response += delta.content
    
    # 保存完整回复到workflow.json
    # 生成 JSON 文件
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(json.loads(full_response), f, ensure_ascii=False, indent=2)

    return full_response


# 如果直接运行此脚本，则执行生成
if __name__ == "__main__":
    file_name = "workflow"
    image_path = os.path.join(os.path.dirname(__file__), 'image', '2.png')
    generate_workflow_json(image_path, file_name)
