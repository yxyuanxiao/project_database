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
    
    def export_to_csv_for_download(self, query):
        import tempfile
        import csv
        import json
        try:
            # 解析查询
            query = json.loads(query) if query.strip() else {}
            cursor = self.annotations.collection.find(query)
            rows = []
            all_fieldnames = set()
            for doc in cursor:
                # 提取基础字段
                base_fields = {
                    "_id": str(doc.get("_id", "")),
                    "last_updated_by": "",
                    "status": doc.get("status", ""),
                    "tag": doc.get("tag", ""),
                    "updated_at": doc.get("updated_at", ""),
                    "user_edited_text": doc.get("user_edited_text", ""),
                }
                user_id = doc.get("last_updated_by")
                if user_id:
                    user = self.get_user_by_id(user_id)
                    base_fields["last_updated_by"] = user.username if user else f"unknown({user_id})"
                else:
                    base_fields["last_updated_by"] = "N/A"
                meta = doc.get("metadata", {})
                anno = doc.get("annotations", {})
                flat_meta = {f"metadata.{k}": v for k, v in meta.items()}
                flat_anno = {f"annotations.{k}": v for k, v in anno.items()}
                row = {**base_fields, **flat_meta, **flat_anno}
                all_fieldnames.update(row.keys())
                rows.append(row)
            
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8-sig', newline='')
            if rows:
                fieldnames = sorted(list(all_fieldnames))
                writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            else:
                # 空结果也写表头
                writer = csv.DictWriter(temp_file, fieldnames=[
                    "_id", "status", "method_name", "image_name", "tag",
                    "last_updated_by", "updated_at", "user_edited_text", "revision_advice"
                ])
                writer.writeheader()
            temp_file.close()

            return temp_file.name, f"成功导出 {len(rows)} 条数据"
    
        except Exception as e:
            temp_err = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8', newline='')
            writer = csv.DictWriter(temp_err, fieldnames=["error"])
            writer.writeheader()
            writer.writerow({"error": str(e)})
            temp_err.close()
            return temp_err.name, f"导出失败: {e}"

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
    
