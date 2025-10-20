import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any

from database import Database

def load_json(json_file_path: str) -> Dict[str, Any]:
    """读取JSON配置文件"""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_annotation_pairs(json_config: Dict[str, Any], file_json: str) -> List[Dict[str, Any]]:
    """根据JSON配置生成标注数据对"""
    pairs = []
    
    lq_path = json_config['lq_path']
    methods = json_config['methods']
    

    annotation_list = load_json(file_json)
    for item in annotation_list:
        image_filename = item['image']

        lq_img_path = os.path.join(lq_path, image_filename)

        if not os.path.exists(lq_img_path):
            print(f"警告: LQ图像不存在 - {lq_img_path}")
            continue
        
        for method in methods:
            method_name = method['name']
            method_path = method['path']
            hq_img_path = os.path.join(method_path, image_filename)

            if not os.path.exists(hq_img_path):
                print(f"警告: HQ图像不存在 - {hq_img_path}")
                continue
            
            meta_data = {
                k: v for k, v in item.items()
                if k not in {'image'}
            }

            pair_data = {
                'lq_image_path': str(Path(lq_img_path).absolute()),
                'hq_image_path': str(Path(hq_img_path).absolute()),
                'meta_data': meta_data,
                'method_name': method_name,
                'image_name': image_filename,
                'status': 'pending',
            }

            pairs.append(pair_data)
    
    return pairs

def initialize_database(json_config_path: str, annotation_json_dir: str, db_interface: Database):
    """初始化数据库"""
    print("开始读取JSON配置文件...")
    config = load_json(json_config_path)
    
    print("生成标注数据对...")
    pairs = generate_annotation_pairs(config, annotation_json_dir)
    
    print(f"找到 {len(pairs)} 个标注数据对")
    
    if not pairs:
        print("没有有效的标注对，跳过数据库初始化。")
        return
    
    # 插入到数据库
    print("正在插入/更新数据库...")
    result = db_interface.initialize(pairs, tag_name='scene')
    
    inserted = result['inserted']
    skipped = result['skipped']
    
    print(f"数据库初始化完成！共插入 {inserted} 个新数据对，跳过 {skipped} 个已存在数据对")

def main():
    parser = argparse.ArgumentParser(description="初始化图像修复标注数据库")
    parser.add_argument('--json_config_path', type=str, required=True)
    parser.add_argument('--files_json_path', type=str, required=True)
    args = parser.parse_args()
    # 配置参数
    db_interface = Database(
        mongodb_uri="mongodb://localhost:27017/",
        db_name="annotation",
        collection_name="annotations"
    )
    
    # 初始化数据库
    initialize_database(args.json_config_path, args.files_json_path, db_interface)
    
    # 检查统计信息
    stats = db_interface.get_annotation_statistics()
    print(f"数据库统计: {stats}")

if __name__ == "__main__":
    main()