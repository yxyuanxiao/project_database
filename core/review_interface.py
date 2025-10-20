# core/review_business_logic.py
import json
from typing import Dict, Any, List, Tuple
from utils.image_utils import open_image
from database import Database
from config import OPTIONS
from services.llm_service import generate_text

class ReviewBusinessLogic:
    def __init__(self, db_interface: Database):
        self.db = db_interface
        self.annotation_options = OPTIONS

    def load_task_list(self, page: int, page_size: int, filter_status: str, role: str = 'admin', user_id: str = None) -> Tuple[List[List[str]], int, int]:
        """加载分页任务列表"""
        skip = (page - 1) * page_size
        if filter_status == "all":
            query = {}
        else:
            query = {"status": filter_status}
        if role not in ['admin', 'super_admin']:
            if user_id:
                query["last_updated_by"] = user_id
            else:
                # 未登录用户，返回空
                query["_id"] = {"$exists": False}
        cursor = self.db.find_with_pagination(query, skip, page_size)
        total = self.db.count(query)

        table_data = []
        for doc in cursor:
            user_id_doc = doc.get('last_updated_by', '')
            user_name = 'Unknown'
            if user_id_doc:
                user_doc = self.db.get_user_by_id(user_id_doc)
                user_name = user_doc.username if user_doc else 'Unknown'
            table_data.append([
                str(doc['_id']),
                doc.get('metadata', {}).get('method_name', 'N/A'),
                doc.get('metadata', {}).get('image_name', 'N/A'),
                doc.get('status', 'N/A'),
                user_name,
                str(doc.get('updated_at', 'N/A'))
            ])
        total_pages = max(1, (total + page_size - 1) // page_size)
        return table_data, total_pages, page

    def load_task_for_review(self, task_id: str) -> Tuple:
        """加载任务详情用于审查"""
        task = self.db.get_annotation_by_id(task_id)
        if not task:
            default_opts = {a: opts[0] for a, opts in self.annotation_options.items()}
            return None, None, f"任务 {task_id} 不存在", default_opts, "", f"任务 {task_id} 不存在"

        lq_pil = open_image(task['lq_image_path'])
        hq_pil = open_image(task['hq_image_path'])
        user_id = task.get('last_updated_by', '')
        if user_id:
            use_name = self.db.get_user_by_id(user_id).username
        else:
            use_name = 'Unkown'
        current_annotations = task.get('annotations', {})
        selected_options = {
            angle: current_annotations.get(angle, options["value"])
            for angle, options in self.annotation_options.items()
        }
        user_text = task.get('user_edited_text', '')
        status_msg = f"任务: {task['_id']} | 状态: {task['status']} | 方法: {task.get('metadata', {}).get('method_name', 'N/A')} | 标注人: {use_name} |标签: {task.get('tag', 'N/A')} | 图像: {task.get('metadata', {}).get('image_name', 'N/A')}"

        return lq_pil, hq_pil, status_msg, selected_options, user_text, ""

    def update_task_in_db(self, task_id: str, selected_options: Dict[str, str], user_text: str) -> str:
        """更新任务（审查员可直接修改）"""
        if not task_id:
            return "任务ID不能为空"
        try:
            success = self.db.update_annotation_by_id(
                doc_id=task_id,
                annotations=selected_options,
                user_edited_text=user_text,
                status='annotated'
            )
            return f"任务 {task_id} 更新成功！" if success else f"任务 {task_id} 未找到或无变化"
        except Exception as e:
            return f"更新任务时出错: {str(e)}"
    
    def generate_text_with_llm(self, selected_options: Dict[str, str], lq_image, hq_image):
        return generate_text(selected_options, lq_image, hq_image)

    def export_data(self, query_str: str, filename: str) -> str:
        """导出数据"""
        try:
            query = json.loads(query_str) if query_str.strip() else {}
            count = self.db.export_annotations_to_json(query=query, filename=filename)
            return f"成功导出 {count} 条数据到 {filename}"
        except json.JSONDecodeError as e:
            return f"查询条件JSON格式错误: {e}"
        except Exception as e:
            return f"导出失败: {e}"

    def import_data(self, file_path: str) -> str:
        """导入数据"""
        try:
            count = self.db.import_annotations_from_json(file_path)
            return f"成功导入 {count} 条数据"
        except Exception as e:
            return f"导入失败: {e}"