from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import logging

logger = logging.getLogger(__name__)

class MongoConnection:
    def __init__(self, uri: str, db_name: str):
        self.uri = uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self._connect()

    def _connect(self):
        try:
            self.client = MongoClient(self.uri)
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            logger.info("MongoDB连接成功")
        except ConnectionFailure as e:
            logger.error(f"MongoDB连接失败: {e}")
            raise

    def get_collection(self, name: str):
        return self.db[name]

    def create_indexes(self, collection_configs: dict):
        """collection_configs: {collection_name: [index_fields]}"""
        for coll_name, indexes in collection_configs.items():
            coll = self.get_collection(coll_name)
            for idx in indexes:
                if isinstance(idx, str):
                    # 简单字段索引
                    coll.create_index(idx)
                elif isinstance(idx, dict):
                    # 字典形式：必须包含 'keys' 键
                    keys = idx.pop("keys")  # 必须提供
                    coll.create_index(keys, **idx)
                else:
                    # 假设是 pymongo 格式的索引（如 [("field", 1)]）
                    coll.create_index(idx)
        logger.info("数据库索引创建成功")

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB连接已关闭")