from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class UserHistoryRepository:
    def __init__(self, connection, collection_name: str):
        self.collection = connection.get_collection(collection_name)

    def add_task(self, user_id: str, task: Dict[str, Any]) -> bool:
        """
        将任务添加到用户历史记录
        
        Args:
            user_id: 用户ID
            task: 任务数据
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 获取用户当前历史记录
            history_doc = self.collection.find_one({"user_id": user_id})
            
            if history_doc:
                # 如果存在历史记录，更新历史记录
                history_doc['tasks'].append(task)
                history_doc['current_index'] = len(history_doc['tasks']) - 1
                history_doc['updated_at'] = datetime.now()
                
                result = self.collection.replace_one(
                    {"user_id": user_id},
                    history_doc
                )
            else:
                # 如果不存在历史记录，创建新的
                new_history_doc = {
                    "user_id": user_id,
                    "tasks": [task],
                    "current_index": 0,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                
                self.collection.insert_one(new_history_doc)
            
            logger.info(f"用户 {user_id} 的任务历史已更新")
            return True
            
        except Exception as e:
            logger.error(f"添加任务到用户历史时出错: {e}")
            return False

    def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户任务历史记录
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict]: 任务历史列表
        """
        try:
            history_doc = self.collection.find_one({"user_id": user_id})
            
            if history_doc:
                return history_doc.get('tasks', [])
            else:
                return []
                
        except Exception as e:
            logger.error(f"获取用户任务历史时出错: {e}")
            return []

    def get_current_index(self, user_id: str) -> int:
        """
        获取用户当前历史记录索引
        
        Args:
            user_id: 用户ID
            
        Returns:
            int: 当前索引，如果不存在则返回-1
        """
        try:
            history_doc = self.collection.find_one({"user_id": user_id})
            
            if history_doc:
                return history_doc.get('current_index', -1)
            else:
                return -1
        except Exception as e:
            logger.error(f"获取用户当前历史索引时出错: {e}")
            return -1

    def update_current_index(self, user_id: str, index: int) -> bool:
        """
        更新用户当前历史记录索引
        
        Args:
            user_id: 用户ID
            index: 新索引
            
        Returns:
            bool: 操作是否成功
        """
        try:
            result = self.collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "current_index": index,
                        "updated_at": datetime.now()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"更新用户当前历史索引时出错: {e}")
            return False
    
    def update_history(self, user_id, history):
        try:
            result = self.collection.update_one(
                {"user_id": user_id},
                {"$set": {"tasks": history}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"更新用户历史失败: {e}")
            return False
    
    def cleanup_user_histories_for_expired_tasks(self, expired_doc_ids: List[str]):
        """从用户历史中移除已过期的任务"""
        try:
            for doc_id in expired_doc_ids:
                # 查找所有 history 中包含该 task _id 的用户
                users_cursor = self.collection.find({
                    "tasks._id": doc_id
                })

                for user_doc in users_cursor:
                    user_id = user_doc["user_id"]
                    tasks = user_doc.get("tasks", [])
                    current_index = user_doc.get("current_index", -1)

                    # 过滤掉过期任务
                    new_tasks = [t for t in tasks if str(t.get("_id")) != doc_id]

                    # 调整 current_index
                    new_index = current_index
                    if 0 <= current_index < len(tasks):
                        if str(tasks[current_index].get("_id")) == doc_id:
                            # 当前任务被删除：回退到前一个，或设为 -1
                            if new_tasks:
                                new_index = min(current_index - 1, len(new_tasks) - 1)
                            else:
                                new_index = -1

                    # 更新用户历史
                    self.collection.update_one(
                        {"user_id": user_id},
                        {
                            "$set": {
                                "tasks": new_tasks,
                                "current_index": new_index,
                                "updated_at": datetime.now()
                            }
                        }
                    )
                    logger.debug(f"用户 {user_id} 的历史中移除了过期任务 {doc_id}")

        except Exception as e:
            logger.error(f"清理用户历史中的过期任务时出错: {e}")