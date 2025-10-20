from typing import Dict, Any, Optional, Tuple
from utils.image_utils import open_image
from database import Database
from services.llm_service import generate_text
from config import OPTIONS

class AnnotationBusinessLogic:
    def __init__(self, db_interface: Database):
        self.db = db_interface
        self.annotation_options = OPTIONS

    # ==================== 用户管理 ====================
    def login_user(self, username: str) -> Tuple[Optional[str], str]:
        if not username:
            return None, "用户名不能为空"
        user = self.db.login_user(username)
        if user:
            return user.user_id, f"登录成功！欢迎，{user.username}"
        else:
            return None, "用户名错误"

    def register_user(self, username: str) -> Tuple[Optional[str], str]:
        if not username:
            return None, "用户名不能为空"
        try:
            user = self.db.register_user(username)
            if user:
                return user.user_id, f"注册成功！用户ID: {user.user_id}"
            else:
                return None, "注册失败"
        except Exception as e:
            return None, f"注册时出错: {str(e)}"

    def get_user_display_info(self, user_id: str) -> str:
        if not user_id:
            return "未登录"
        return f"用户ID: {user_id}"

    # ==================== 任务加载 ====================
    def _empty_task(self, status: str) -> Dict[str, Any]:
        return {
            'lq_image': None,
            'hq_image': None,
            'status': status,
            'selected_options': {angle: opts["value"] for angle, opts in self.annotation_options.items()},
            'user_text': ""
        }

    def load_task_by_id(self, task_id: str, user_id: str) -> Dict[str, Any]:
        if not user_id:
            return self._empty_task("请先登录")
        try:
            task = self.db.get_annotation_by_id(task_id)
            if not task:
                return self._empty_task("任务不存在")

            lq_pil = open_image(task['lq_image_path'])
            hq_pil = open_image(task['hq_image_path'])

            current_annotations = task.get('annotations', {})
            selected_options = {
                angle: current_annotations.get(angle, opts["value"])
                for angle, opts in self.annotation_options.items()
            }
            user_text = task.get('user_edited_text', '')
            status_msg = f"当前任务: {task['_id']} | 状态: {task['status']} | 方法: {task.get('metadata', {}).get('method_name', 'N/A')} | 标签: {task.get('tag', 'N/A')}"

            return {
                'lq_image': lq_pil,
                'hq_image': hq_pil,
                'status': status_msg,
                'selected_options': selected_options,
                'user_text': user_text
            }
        except Exception as e:
            return self._empty_task(f"加载任务失败: {str(e)}")

    def load_next_task(self, user_id: str) -> Dict[str, Any]:
        if not user_id:
            return self._empty_task("请先登录")
        try:
            history = self.db.get_user_task_history(user_id)
            current_index = self.db.get_user_current_history_index(user_id)
            if history and current_index < len(history) - 1:
                new_index = current_index + 1
                self.db.update_user_current_history_index(user_id, new_index)
                task = history[new_index]
                return self.load_task_by_id(task['_id'], user_id)

            task = self.db.get_next_pending_annotation(user_id)
            if not task:
                return self._empty_task("没有更多待标注的任务")

            # 添加到历史
            self.db.add_task_to_user_history(user_id, task)

            lq_pil = open_image(task['lq_image_path'])
            hq_pil = open_image(task['hq_image_path'])

            current_annotations = task.get('annotations', {})
            selected_options = {
                angle: current_annotations.get(angle, opts["value"])
                for angle, opts in self.annotation_options.items()
            }
            user_text = task.get('user_edited_text', '')
            status_msg = f"当前任务: {task['_id']} | 状态: {task['status']} | 方法: {task.get('metadata', {}).get('method_name', 'N/A')} | 标签: {task.get('tag', 'N/A')}"

            return {
                'lq_image': lq_pil,
                'hq_image': hq_pil,
                'status': status_msg,
                'selected_options': selected_options,
                'user_text': user_text
            }
        except Exception as e:
            return self._empty_task(f"加载任务失败: {str(e)}")

    def load_previous_task(self, user_id: str) -> Dict[str, Any]:
        if not user_id:
            return self._empty_task("请先登录")
        try:
            history = self.db.get_user_task_history(user_id)
            if not history:
                return self._empty_task("没有历史任务")

            current_index = self.db.get_user_current_history_index(user_id)
            new_index = current_index - 1
            self.db.update_user_current_history_index(user_id, new_index)
            if new_index < 0:
                return self._empty_task("已经是第一张任务")
            
            task = history[new_index]
            return self.load_task_by_id(task['_id'], user_id)
        except Exception as e:
            return self._empty_task(f"加载上一张任务失败: {str(e)}")
    
    def get_tag(self, task_id: str) -> str:
        task = self.db.get_annotation_by_id(task_id)
        return task.get('tag', '')

    # ==================== 任务操作 ====================
    def cancel_current_task(self, user_id: str, task_id: str) -> str:
        if not user_id or not task_id:
            return "用户或任务ID缺失"
        try:
            success = self.db.release_annotation_lock(task_id, user_id)
            if not success:
                return "取消失败：可能无权限或任务未被分配"
            
            history = self.db.get_user_task_history(user_id)
            current_index = self.db.get_user_current_history_index(user_id)
            
            if history and 0 <= current_index < len(history):
                current_task = history[current_index]
                if str(current_task.get('_id')) == task_id:
                    updated_history = history[:current_index] + history[current_index + 1:]
                    self.db.update_history(user_id, updated_history)

                    new_index = max(-1, current_index - 1)
                    self.db.update_user_current_history_index(user_id, new_index)

            return f"任务 {task_id} 已取消并从历史中移除"
        except Exception as e:
            return f"取消任务时出错: {str(e)}"

    def save_annotations(self, user_id: str, task_id: str, selected_options: Dict[str, str], user_text: str) -> str:
        if not user_id or not task_id:
            return "未登录或无当前任务"
        try:
            task = self.db.get_annotation_by_id(task_id)
            if not task:
                return f"任务 {task_id} 不存在"

            current_status = task.get('status')
            if current_status == 'annotated':
                success = self.db.update_annotation_by_id(task_id, selected_options, user_text, 'annotated')
            elif current_status == 'annotating':
                success = self.db.update_annotation_with_lock(task_id, user_id, selected_options, user_text, 'annotated')
            else:
                return f"任务状态 '{current_status}' 不允许保存"

            return "标注已保存！" if success else "保存失败！"
        except Exception as e:
            return f"保存标注时出错: {str(e)}"

    def update_task_in_db(self, task_id: str, selected_options: Dict[str, str], user_text: str) -> str:
        if not task_id:
            return "任务ID不能为空"
        try:
            success = self.db.update_annotation_by_id(task_id, selected_options, user_text, 'annotated')
            return f"任务 {task_id} 更新成功！" if success else f"任务 {task_id} 未找到或无变化"
        except Exception as e:
            return f"更新任务时出错: {str(e)}"

    # ==================== LLM & 统计 ====================
    def generate_text_with_llm(self, selected_options: Dict[str, str], lq_image, hq_image, tag) -> str:
        return generate_text(selected_options, lq_image, hq_image, tag)

    def get_annotation_statistics(self) -> Dict[str, int]:
        return self.db.get_annotation_statistics()
