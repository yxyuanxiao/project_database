import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from bson import ObjectId
import logging
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)

class AnnotationRepository:
    def __init__(self, connection, collection_name: str, lock_collection_name: str, lock_timeout: int = 300):
        self.conn = connection
        self.collection = connection.get_collection(collection_name)
        self.lock_collection = connection.get_collection(lock_collection_name)
        self.lock_timeout = lock_timeout
    
    def initialize_annotations(self, annotation_pairs: List[Dict[str, Any]], tag_name:str) -> dict:
        inserted = 0
        skipped = 0

        for pair in annotation_pairs:
            metadata = {
                'method_name': pair['method_name'],
                'image_name': pair['image_name'],
            }
            metadata.update(pair['meta_data'])
            annotation_doc = {
                'lq_image_path': pair['lq_image_path'],
                'hq_image_path': pair['hq_image_path'],
                'tag': pair['meta_data'][tag_name],
                'metadata': metadata,
                'annotations': {},
                'user_edited_text': '',
                'status': 'pending',
                'assigned_user': None,
                'assigned_at': None,
                'updated_at': None,
                'last_updated_by': None
            }

            query = {
                'lq_image_path': annotation_doc['lq_image_path'],
                'hq_image_path': annotation_doc['hq_image_path'],
                'metadata.method_name': annotation_doc['metadata']['method_name'],
            }

            result = self.collection.update_one(
                query,
                {"$setOnInsert": annotation_doc},
                upsert=True
            )

            if result.upserted_id:
                inserted += 1
            else:
                skipped += 1

        return {'inserted': inserted, 'skipped': skipped}

    def _acquire_lock(self, doc_id: str, user_id: str) -> bool:
        """
        获取分布式锁
        
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            
        Returns:
            bool: 锁获取是否成功
        """
        try:
            expires_at = datetime.now() + timedelta(seconds=self.lock_timeout)
            
            # 尝试插入锁记录
            lock_doc = {
                "doc_id": doc_id,
                "user_id": user_id,
                "acquired_at": datetime.now(),
                "expires_at": expires_at
            }
            
            try:
                self.lock_collection.insert_one(lock_doc)
                print(f"用户 {user_id} 成功获取文档 {doc_id} 的锁")
                logger.info(f"用户 {user_id} 成功获取文档 {doc_id} 的锁")
                return True
            except DuplicateKeyError:
                # 锁已被其他用户获取，检查是否过期
                existing_lock = self.lock_collection.find_one({"doc_id": doc_id})
                if existing_lock and existing_lock["expires_at"] < datetime.now():
                    # 锁已过期，删除旧锁并重新获取
                    self.lock_collection.delete_one({"doc_id": doc_id})
                    self.lock_collection.insert_one(lock_doc)
                    logger.info(f"用户 {user_id} 获取了过期的文档 {doc_id} 锁")
                    return True
                else:
                    logger.info(f"用户 {user_id} 获取文档 {doc_id} 锁失败")
                    return False
                    
        except Exception as e:
            logger.error(f"获取锁时出错: {e}")
            return False

    def _release_lock(self, doc_id: str, user_id: str) -> bool:
        """
        释放分布式锁
        
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            
        Returns:
            bool: 锁释放是否成功
        """
        try:
            result = self.lock_collection.delete_one({
                "doc_id": doc_id,
                "user_id": user_id
            })
            
            if result.deleted_count > 0:
                logger.info(f"用户 {user_id} 成功释放文档 {doc_id} 的锁")
                return True
            else:
                logger.warning(f"用户 {user_id} 未能释放文档 {doc_id} 的锁")
                return False
                
        except Exception as e:
            logger.error(f"释放锁时出错: {e}")
            return False

    def get_by_id(self, doc_id: str) -> Optional[Dict]:
        try:
            object_id = ObjectId(doc_id)
            result = self.collection.find_one({"_id": object_id})
            
            if result:
                result['_id'] = str(result['_id'])
                return result
            else:
                logger.info(f"未找到ID为 {doc_id} 的标注数据")
                return None
                
        except Exception as e:
            logger.error(f"查询数据时出错: {e}")
            raise

    def get_next_pending(self, user_id: str) -> Optional[Dict]:
        """
        获取下一个待标注的数据（带锁机制）
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[Dict]: 标注数据字典，如果没有则返回None
        """
        try:
            # 查找状态为pending的数据
            pending_docs = self.collection.find({"status": "pending"}).sort("_id", 1)
            
            for doc in pending_docs:
                doc_id = str(doc['_id'])
                
                # 尝试获取锁
                if self._acquire_lock(doc_id, user_id):
                    # 成功获取锁，更新文档状态
                    now = datetime.now()
                    result = self.collection.update_one(
                        {"_id": doc["_id"]},
                        {
                            "$set": {
                                "status": "annotating",
                                "assigned_user": user_id,
                                "assigned_at": now,
                                "updated_at": now
                            }
                        }
                    )
                    
                    if result.modified_count > 0:
                        # 返回更新后的文档
                        updated_doc = self.collection.find_one({"_id": doc["_id"]})
                        updated_doc['_id'] = str(updated_doc['_id'])
                        logger.info(f"用户 {user_id} 成功获取文档 {doc_id} 进行标注")
                        return updated_doc
                    else:
                        # 更新失败，释放锁
                        self._release_lock(doc_id, user_id)
                        continue  # 尝试下一个
                    
            logger.info(f"用户 {user_id} 未能获取任何待标注任务")
            return None
            
        except Exception as e:
            logger.error(f"获取待标注数据时出错: {e}")
            raise

    def update_with_lock(self, doc_id: str, user_id: str,
                        annotations: Optional[Dict[str, float]] = None,
                        user_edited_text: Optional[str] = None,
                        status: Optional[str] = None) -> bool:
        """
        带锁机制的标注数据更新
        
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            annotations: 标注字典
            user_edited_text: 用户编辑文本
            status: 状态
            
        Returns:
            bool: 更新是否成功
        """
        try:
            object_id = ObjectId(doc_id)
            
            # 首先检查当前用户是否拥有该文档的锁
            lock = self.lock_collection.find_one({"doc_id": doc_id})
            if not lock or lock.get("user_id") != user_id:
                logger.warning(f"用户 {user_id} 无权更新文档 {doc_id}")
                return False
            
            # 构建更新数据
            update_data = {
                "updated_at": datetime.now(),
                "last_updated_by": user_id
            }
            
            if annotations is not None:
                update_data["annotations"] = annotations
            if user_edited_text is not None:
                update_data["user_edited_text"] = user_edited_text
            if status is not None:
                update_data["status"] = status
            
            # 如果状态变为annotated，清空分配信息
            if status == "annotated":
                update_data["assigned_user"] = None
                update_data["assigned_at"] = None
            
            result = self.collection.update_one(
                {"_id": object_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"用户 {user_id} 成功更新标注数据，ID: {doc_id}")
                
                # 如果标注完成，释放锁
                if status in ["annotated", "reviewed"]:
                    self._release_lock(doc_id, user_id)
            else:
                logger.warning(f"用户 {user_id} 未找到要更新的数据，ID: {doc_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"更新数据时出错: {e}")
            return False

    def update_by_id(self, doc_id: str, 
                    annotations: Optional[Dict[str, Any]] = None,
                    user_edited_text: Optional[str] = None,
                    status: Optional[str] = None) -> bool:
        try:
            object_id = ObjectId(doc_id)
            
            # 构建更新数据
            update_data = {"updated_at": datetime.now()}
            
            if annotations is not None:
                update_data["annotations"] = annotations
            if user_edited_text is not None:
                update_data["user_edited_text"] = user_edited_text
            if status is not None:
                update_data["status"] = status
            
            result = self.collection.update_one(
                {"_id": object_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"成功更新标注数据，ID: {doc_id}")
            else:
                logger.warning(f"未找到要更新的数据，ID: {doc_id}，或数据无变化")
            
            return success
            
        except Exception as e:
            logger.error(f"更新数据时出错: {e}")
            return False

    def update_user_edited_text(self, doc_id: str, text: str) -> bool:
        try:
            result = self._collection.update_one(
                {"_id": ObjectId(doc_id)},
                {
                    "$set": {
                        "user_edited_text": text,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"更新 user_edited_text 失败: {e}")
            return False
    
    def release_lock_and_reset(self, doc_id: str, user_id: str) -> bool:
        """
        释放标注任务锁（当用户取消标注时）
        
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            
        Returns:
            bool: 释放是否成功
        """
        try:
            # 释放锁
            lock_released = self._release_lock(doc_id, user_id)
            
            if lock_released:
                # 重置文档状态为pending
                result = self.collection.update_one(
                    {"_id": ObjectId(doc_id)},
                    {
                        "$set": {
                            "status": "pending",
                            "assigned_user": None,
                            "assigned_at": None,
                            "updated_at": datetime.now()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    logger.info(f"用户 {user_id} 释放了文档 {doc_id} 的标注任务")
                    return True
                else:
                    logger.warning(f"未能重置文档 {doc_id} 的状态")
                    return False
            else:
                logger.warning(f"用户 {user_id} 未能释放文档 {doc_id} 的锁")
                return False
                
        except Exception as e:
            logger.error(f"释放标注锁时出错: {e}")
            return False

    def get_statistics(self) -> Dict[str, int]:
        try:
            stats = {}
            
            # 按状态统计
            pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            # 初始化所有状态的计数
            all_statuses = ["pending", "annotating", "annotated"]
            for status in all_statuses:
                stats[status] = 0
            
            # 填充实际统计结果
            for result in results:
                stats[result['_id']] = result['count']
            
            # 计算总数量
            stats['total'] = sum(stats.values())
            
            logger.info(f"标注统计: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"获取统计信息时出错: {e}")
            raise
    
    def cleanup_expired_locks(self):
        """清理过期的锁"""
        try:
            now = datetime.now()
            expired_locks = self.lock_collection.find({"expires_at": {"$lt": now}})
            expired_doc_ids = [lock["doc_id"] for lock in expired_locks]

            if not expired_doc_ids:
                return 0, expired_doc_ids
            
            self.lock_collection.delete_many({"expires_at": {"$lt": now}})
            object_ids = [ObjectId(doc_id) for doc_id in expired_doc_ids]

            self.collection.update_many(
                {"_id": {"$in": object_ids}, "status": "annotating"},
                {
                    "$set": {
                        "status": "pending",
                        "assigned_user": None,
                        "assigned_at": None,
                        "updated_at": now
                    }
                }
            )
            logger.info(f"清理了 {len(expired_doc_ids)} 个过期锁及对应任务")
            
            return len(expired_doc_ids), expired_doc_ids
            
        except Exception as e:
            logger.error(f"清理过期锁时出错: {e}")
            return 0, []
    
    def find_with_pagination(self, query: dict, skip: int, limit: int):
        return list(self.collection.find(query).skip(skip).limit(limit))
    
    def find_all(self, query: dict) -> List[Dict]:
        return list(self.collection.find(query))

    def count(self, query: dict):
        return self.collection.count_documents(query)

    def import_from_json(self, filename: str) -> int:
        """
        从JSON文件导入标注数据到数据库
        
        Args:
            filename: 输入JSON文件名
            
        Returns:
            int: 导入的数据条数
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 预处理数据：将_id字符串转换回ObjectId，将ISO时间字符串转换回datetime对象
            processed_data = []
            for item in data:
                processed_item = item.copy()
                
                # 处理时间字段
                for key, value in processed_item.items():
                    if isinstance(value, str):
                        try:
                            # 尝试解析ISO格式的时间字符串
                            processed_item[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        except ValueError:
                            # 如果不是时间字符串，则保持原样
                            pass
                
                processed_data.append(processed_item)
            
            if processed_data:
                result = self.collection.insert_many(processed_data)
                count = len(result.inserted_ids)
                logger.info(f"成功导入 {count} 条数据")
                return count
            else:
                logger.info("导入文件为空")
                return 0
                
        except Exception as e:
            logger.error(f"导入数据时出错: {e}")
            raise