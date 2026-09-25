import cv2
import numpy as np

# 预定义颜色HSV范围（可根据实际光照微调）
color_ranges = {
    'Red':   ([0, 100, 100], [10, 255, 255]),      # 红色范围1
    'Red2':  ([160, 100, 100], [179, 255, 255]),   # 红色范围2
    'Green': ([40, 50, 50], [80, 255, 255]),
    'Blue':  ([100, 100, 50], [130, 255, 255]),
    'Yellow':([20, 100, 100], [35, 255, 255])
}

# 颜色映射：中文到英文
color_map = {
    '红': 'Red',
    '绿': 'Green',
    '蓝': 'Blue',
    '黄': 'Yellow'
}

# BGR颜色值映射
color_bgr = {
    'Red': (0, 0, 255),
    'Green': (0, 255, 0),
    'Blue': (255, 0, 0),
    'Yellow': (0, 255, 255)
}

class Vision:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise ValueError("Cannot open camera")

    def get_color_mask(self, hsv, color_name):
        """返回指定颜色的HSV掩码。"""
        if color_name == 'Red':
            mask1 = cv2.inRange(hsv, np.array(color_ranges['Red'][0]), np.array(color_ranges['Red'][1]))
            mask2 = cv2.inRange(hsv, np.array(color_ranges['Red2'][0]), np.array(color_ranges['Red2'][1]))
            return cv2.bitwise_or(mask1, mask2)
        elif color_name == 'Green':
            return cv2.inRange(hsv, np.array(color_ranges['Green'][0]), np.array(color_ranges['Green'][1]))
        elif color_name == 'Blue':
            return cv2.inRange(hsv, np.array(color_ranges['Blue'][0]), np.array(color_ranges['Blue'][1]))
        elif color_name == 'Yellow':
            return cv2.inRange(hsv, np.array(color_ranges['Yellow'][0]), np.array(color_ranges['Yellow'][1]))
        raise ValueError(f"不支持的颜色: {color_name}")

    def calibrate(self, x, y, rz):
        """标定函数，暂时返回图像坐标与角度（后续可添加坐标转换）。"""
        return x, y, rz

    def draw_detections(self, frame, contours, eng_color, positions):
        """在帧上绘制识别结果：方框、中心点、坐标和角度。"""
        overlay = frame.copy()
        color = color_bgr.get(eng_color, (255, 255, 255))
        
        for cnt, (cal_x, cal_y, cal_rz) in zip(contours, positions):
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
            box = np.int32(box)
            
            # 绘制方框（带透明度）
            cv2.polylines(overlay, [box], True, color, 2)
            cv2.fillPoly(overlay, [box], color)
            
            # 绘制中心点
            cv2.circle(overlay, (int(cal_x), int(cal_y)), 5, (255, 255, 255), -1)
            cv2.circle(overlay, (int(cal_x), int(cal_y)), 7, color, 2)
            
            # 显示坐标和角度
            text = f"({cal_x:.1f}, {cal_y:.1f})\nAngle: {cal_rz:.1f}°"
            for line, txt in enumerate(text.split('\n')):
                # 白色背景文字（易识别）
                cv2.putText(overlay, txt, 
                           (int(cal_x) + 15, int(cal_y) + 15 + line * 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 3)
                # 彩色前景文字
                cv2.putText(overlay, txt, 
                           (int(cal_x) + 15, int(cal_y) + 15 + line * 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # 融合原图和叠加层，实现透明效果
        result = cv2.addWeighted(frame, 0.6, overlay, 0.4, 0)
        return result

    def get_block_positions(self, color):
        """获取指定颜色的物块位置，返回列表[(x, y, rz), ...]和当前帧图像，其中x,y为标定后的坐标，rz为旋转角度（度数，绝对值<=45°）。"""
        # 映射颜色
        eng_color = color_map.get(color, color)
        if eng_color not in color_ranges:
            return [], None
        
        ret, frame = self.cap.read()
        if not ret:
            return [], None
        
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = self.get_color_mask(hsv, eng_color)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        positions = []
        valid_contours = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 500:
                continue
            rect = cv2.minAreaRect(cnt)
            center, size, angle = rect
            x, y = center
            
            # 确保角度的绝对值 <= 45°
            # minAreaRect 返回的角度范围大约是 [-90, 0]，我们需要调整到 [-45, 45]
            if angle < -45:
                angle = angle + 90
            
            # 标定
            cal_x, cal_y, cal_rz = self.calibrate(x, y, angle)
            
            # 只保留角度绝对值 <= 45° 的物体
            if abs(cal_rz) <= 45:
                positions.append((cal_x, cal_y, cal_rz))
                valid_contours.append(cnt)
        
        # 绘制识别结果
        result_frame = frame.copy()
        if positions:
            result_frame = self.draw_detections(result_frame, valid_contours, eng_color, positions)
        
        return positions, result_frame