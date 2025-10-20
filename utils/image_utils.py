# utils/image_utils.py
import cv2
import os
from typing import List, Optional
from PIL import Image

def open_image(image_path: str) -> Optional[Image.Image]:
    try:
        if not os.path.exists(image_path):
            print(f"图像文件不存在: {image_path}")
            return None
        image = cv2.imread(image_path)
        if image is None:
            print(f"无法读取图像: {image_path}")
            return None
        
        return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    except Exception as e:
        print(f"读取图像时出错: {e}")
        return None