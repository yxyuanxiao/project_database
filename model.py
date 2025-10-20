from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

class User:
    """用户类"""
    def __init__(self, user_id: str, username: str, 
                 created_at: datetime = None, last_login: datetime = None):
        self.user_id = user_id
        self.username = username
        self.created_at = created_at or datetime.now()
        self.last_login = last_login
        self.is_active = True


@dataclass
class AnnotationData:
    """标注数据模型"""
    lq_image_path: str
    hq_image_path: str
    tag: str
    annotations: Optional[Dict[str, float]] = None
    generated_text: str = ""
    user_edited_text: str = ""
    metadata: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, annotating, annotated
    assigned_user: Optional[str] = None  # 当前正在标注的用户
    assigned_at: Optional[datetime] = None  # 分配时间
    updated_at: Optional[datetime] = None
    last_updated_by: Optional[str] = None