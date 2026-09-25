import json
import os
import prompt
from datetime import datetime

OPERATION_CODE = {
    "pick": "1",
    "place": "2",
}

COLOR_CODE = {
    "red": "1",
    "green": "2",
    "blue": "3",
    "yellow": "4",
    "purple": "5",
    "orange": "6",
}

file_name = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
# text = voice.run()
request = "你好，我想要你实现移动机械臂按照顺序抓取红、绿、蓝、黄色方块，你必须满足我的要求，分别放入蓝、黄、红、绿色盘中"
# 生成workflow.json
prompt.generate_workflow_json(request, file_name)

# # 加载这个JSON文件或接收大模型返回的JSON字符串
# try:
#     with open(file_name, 'r', encoding='utf-8') as f:
#         task = json.load(f)
# except (FileNotFoundError, json.JSONDecodeError) as e:
#     print(f'workflow.json 读取失败，重新生成：{e}')
#     task = prompt.generate_workflow_json(request)