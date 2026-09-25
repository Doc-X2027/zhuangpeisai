import json
import shijue
# import aubo_robot  # 暂时注释掉，因为pyaubo_sdk未安装
import time
import cv2
import prompt
from datetime import datetime
import voice

file_name = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
# text = voice.run()
request = "你好，我想要你实现移动机械臂按照反的顺序抓取红、绿色方块，你必须满足我的要求"
# 生成workflow.json
prompt.generate_workflow_json(request, file_name)

# 加载这个JSON文件或接收大模型返回的JSON字符串
try:
    with open(file_name, 'r', encoding='utf-8') as f:
        task = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f'workflow.json 读取失败，重新生成：{e}')
    task = prompt.generate_workflow_json(request)

safe_z = 0.4  # 安全高度
# 初始化视觉模块和机器人
vision = shijue.Vision()
# robot = aubo_robot.Robot()  # 暂时注释，移动指令用print替代

# 逐个执行子任务
for item in task['assembly_sequence']:
    color = item['object_color']  # 获取颜色：红、绿、蓝、黄
    print(f"\n{'='*60}")
    print(f"正在执行步骤 {item['step']}: {item['action_description']}")
    print(f"{'='*60}")
    
    # 调用视觉模块，获取该颜色所有方块的坐标列表和当前帧图像
    positions, frame = vision.get_block_positions(color)  # 返回列表[(x, y, rz), ...] 和带识别效果的frame
    
    window_name = f"Step {item['step']}: Color Detection"
    cv2.imshow(window_name, frame)
    cv2.waitKey(5000)  # 显示3秒后自动继续
    cv2.destroyWindow(window_name)  # 关闭窗口
    
    # 如果有多个识别对象，分别移动到他们上方
    if positions:
        print(f"检测到 {len(positions)} 个 {color} 方块：")
        for i, (x, y, rz) in enumerate(positions, start=1):
            print(f"  #{i}: 坐标 ({x:.1f}, {y:.1f}), 角度 {rz:.1f}°" + " 抓取中...")
            time.sleep(10)  # 短暂延迟
            print(f"  #{i}: 坐标 ({x:.1f}, {y:.1f}), 角度 {rz:.1f}°" + " 已完成")
            time.sleep(1)  # 短暂延迟
            # robot.move_to(x, y, safe_z, rz)  # 移动到方块上方安全高度并旋转对准
    else:
        print(f"未检测到 {color} 方块")

print(f"\n{'='*60}")
print("所有任务执行完成！")
print(f"{'='*60}")
cv2.destroyAllWindows()  # 关闭所有窗口