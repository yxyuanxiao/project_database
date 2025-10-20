import secrets
import datetime

from model import User

class UserRepository:
    def __init__(self, connection, collection_name: str):
        self.collection = connection.get_collection(collection_name)
    
    def _generate_user_id(self) -> str:
        """生成唯一的用户ID"""
        return secrets.token_urlsafe(16)

    def register_user(self, username):
        """注册新用户"""
        try:
            # 检查用户名是否已存在
            existing_user = self.collection.find_one({"username": username})
            
            if existing_user:
                if existing_user.get('username') == username:
                    raise ValueError("用户名已存在")
            
            # 生成用户ID和密码哈希
            user_id = self._generate_user_id()
            
            # 创建用户文档
            user_doc = {
                "user_id": user_id,
                "username": username,
                "created_at": datetime.datetime.now(),
                "last_login": None,
                "is_active": True,
            }
            
            result = self.collection.insert_one(user_doc)
            
            if result.inserted_id:
                return User(
                    user_id=user_id,
                    username=username,
                    created_at=user_doc['created_at']
                )
            else:
                return None
                
        except Exception as e:
            print(f"注册用户时出错: {e}")
            raise
    
    def login_user(self, username):
        """用户登录"""
        try:
            user_doc = self.collection.find_one({"username": username})
            
            if not user_doc:
                return None
            
            if not user_doc.get('is_active', True):
                return None
            
            # 更新最后登录时间
            self.collection.update_one(
                {"_id": user_doc['_id']},
                {"$set": {"last_login": datetime.datetime.now()}}
            )
            
            return User(
                user_id=user_doc['user_id'],
                username=user_doc['username'],
                created_at=user_doc['created_at'],
                last_login=datetime.datetime.now()
            )
                
        except Exception as e:
            print(f"登录时出错: {e}")
            return None
    
    def get_user_by_id(self, user_id):
        """根据ID获取用户"""
        try:
            user_doc = self.collection.find_one({"user_id": user_id})
            
            if user_doc:
                return User(
                    user_id=user_doc['user_id'],
                    username=user_doc['username'],
                    created_at=user_doc['created_at'],
                    last_login=user_doc.get('last_login')
                )
            else:
                return None
                
        except Exception as e:
            print(f"获取用户时出错: {e}")
            return None