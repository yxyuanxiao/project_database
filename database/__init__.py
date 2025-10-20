from typing import Optional, Dict, Any, List
from .connection import MongoConnection
from .annotation_repository import AnnotationRepository
from .user_repository import UserRepository
from .user_history_repository import UserHistoryRepository
from model import User

class Database:
    def __init__(self, mongodb_uri="mongodb://localhost:27017/", db_name="annotation_db",
                 collection_name="annotations", lock_collection_name="annotation_locks",
                 use_collection_name="users", user_history_collection_name="user_task_history"):
        
        self.conn = MongoConnection(mongodb_uri, db_name)
        
        # 创建索引配置
        index_config = {
            collection_name: ["status", "assigned_user", "assigned_at"],
            lock_collection_name: [{"keys": "doc_id", "unique": True}, "expires_at"],
            use_collection_name: ["username", "user_id"],
            user_history_collection_name: ["user_id"]
        }
        self.conn.create_indexes(index_config)

        # 初始化子模块
        self.annotations = AnnotationRepository(
            self.conn, collection_name, lock_collection_name
        )
        self.user = UserRepository(
            self.conn, use_collection_name
        )
        self.user_history = UserHistoryRepository(
            self.conn, user_history_collection_name
        )

    def initialize(self, annotation_pairs, tag_name):
        return self.annotations.initialize_annotations(annotation_pairs, tag_name)

    def _cleanup_expired_locks(self):
        num_expired_doc, expired_doc_ids = self.annotations.cleanup_expired_locks()
        if num_expired_doc>0:
            self.user_history.cleanup_user_histories_for_expired_tasks(expired_doc_ids)

    def get_annotation_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        self._cleanup_expired_locks()
        return self.annotations.get_by_id(doc_id)

    def get_next_pending_annotation(self, user_id: str) -> Optional[Dict[str, Any]]:
        self._cleanup_expired_locks()
        return self.annotations.get_next_pending(user_id)

    def release_annotation_lock(self, doc_id: str, user_id: str) -> bool:
        return self.annotations.release_lock_and_reset(doc_id, user_id)

    def update_annotation_by_id(self, doc_id: str, annotations: Dict[str, Any], user_edited_text: str, status: str) -> bool:
        return self.annotations.update_by_id(doc_id, annotations, user_edited_text, status)
    
    def update_user_edited_text(self, doc_id: str, text: str) -> bool:
        return self.annotations.update_user_edited_text(doc_id, text)

    def update_annotation_with_lock(self, doc_id: str, user_id: str, 
                                    annotations: Dict[str, Any], 
                                    user_edited_text: str = "", 
                                    status: str = "annotated"):
        return self.annotations.update_with_lock(doc_id, user_id, annotations, user_edited_text, status)

    def get_annotation_statistics(self) -> Dict[str, int]:
        return self.annotations.get_statistics()
    
    def find_with_pagination(self, query: dict, skip: int, limit: int):
        return self.annotations.find_with_pagination(query, skip, limit)
    
    def export_annotations_to_json(self, query, filename):
        return self.annotations.export_to_json(query, filename)

    def import_annotations_from_json(self, file_path):
        return self.annotations.import_from_json(file_path)

    def find_all(self, query):
        return self.annotations.find_all(query)
    
    def count(self, query):
        return self.annotations.count(query)

    ### user ###
    def register_user(self, username: str) -> Optional[User]:
        return self.user.register_user(username)
    
    def login_user(self, username: str) -> Optional[User]:
        return self.user.login_user(username)
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.user.get_user_by_id(user_id)
    
    ### user history ###
    def add_task_to_user_history(self, user_id: str, task: Dict[str, Any]) -> bool:
        return self.user_history.add_task(user_id, task)

    def get_user_task_history(self, user_id: str) -> List[Dict[str, Any]]:
        return self.user_history.get_history(user_id)

    def get_user_current_history_index(self, user_id: str) -> int:
        return self.user_history.get_current_index(user_id)

    def update_user_current_history_index(self, user_id: str, index: int) -> bool:
        return self.user_history.update_current_index(user_id, index)

    def update_history(self, user_id: str, history: List[Dict]) -> bool:
        return self.user_history.update_history(user_id, history)
    
    def close_connection(self):
        self.conn.close()
    
