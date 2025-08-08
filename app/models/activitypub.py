from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from datetime import datetime
from typing import Optional, Dict, Any

class Actor(Base):
    """ActivityPub Actor model (corresponds to Mesh Member)"""
    __tablename__ = "actors"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    domain = Column(String(255), nullable=False)
    display_name = Column(String(255))
    summary = Column(Text)
    icon_url = Column(String(500))
    inbox_url = Column(String(500), nullable=False)
    outbox_url = Column(String(500), nullable=False)
    followers_url = Column(String(500))
    following_url = Column(String(500))
    public_key_pem = Column(Text, nullable=False)
    private_key_pem = Column(Text)
    is_local = Column(Boolean, default=True)
    is_bot = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Mesh Member corresponding fields
    mesh_member_id = Column(String(255), unique=True, index=True)  # Mesh Member ID
    mesh_custom_id = Column(String(255), unique=True, index=True)  # Mesh Member customId
    nickname = Column(String(255))  # Mesh Member nickname
    email = Column(String(255))  # Mesh Member email
    avatar = Column(String(500))  # Mesh Member avatar
    intro = Column(Text)  # Mesh Member intro
    is_active = Column(Boolean, default=True)  # Mesh Member is_active
    verified = Column(Boolean, default=False)  # Mesh Member verified
    language = Column(String(10))  # Mesh Member language
    firebase_id = Column(String(255))  # Mesh Member firebaseId
    wallet = Column(String(255))  # Mesh Member wallet
    balance = Column(Integer, default=0)  # Mesh Member balance
    
    # ActivityPub feature controls
    activitypub_enabled = Column(Boolean, default=False)  # Whether ActivityPub features are enabled
    activitypub_auto_follow = Column(Boolean, default=True)  # Whether to automatically accept follow requests
    activitypub_public_posts = Column(Boolean, default=True)  # Whether to publicly publish content
    activitypub_federation_enabled = Column(Boolean, default=True)  # Whether federation is enabled
    
    # Relationships
    activities = relationship("Activity", back_populates="actor")
    followers = relationship("Follow", foreign_keys="Follow.following_id", back_populates="following")
    following = relationship("Follow", foreign_keys="Follow.follower_id", back_populates="follower")
    picks = relationship("Pick", back_populates="actor")
    comments = relationship("Comment", back_populates="actor")
    account_mappings = relationship("AccountMapping", back_populates="local_actor")

class Activity(Base):
    """ActivityPub Activity model"""
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(String(500), unique=True, index=True, nullable=False)
    actor_id = Column(Integer, ForeignKey("actors.id"), nullable=False)
    activity_type = Column(String(100), nullable=False)  # Create, Follow, Like, Share, etc.
    object_data = Column(JSON, nullable=False)  # Activity object data
    target_data = Column(JSON)  # Target object data
    to = Column(JSON)  # Recipients list
    cc = Column(JSON)  # CC list
    signature = Column(Text)
    is_local = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    actor = relationship("Actor", back_populates="activities")

class Follow(Base):
    """Follow relationship model (corresponds to Mesh Member follow relationships)"""
    __tablename__ = "follows"
    
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("actors.id"), nullable=False)
    following_id = Column(Integer, ForeignKey("actors.id"), nullable=False)
    activity_id = Column(String(500), unique=True, index=True)
    is_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    accepted_at = Column(DateTime(timezone=True))
    
    # Relationships
    follower = relationship("Actor", foreign_keys=[follower_id], back_populates="following")
    following = relationship("Actor", foreign_keys=[following_id], back_populates="followers")

class Story(Base):
    """Story model (corresponds to Mesh articles)"""
    __tablename__ = "stories"
    
    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(String(500), unique=True, index=True, nullable=False)
    mesh_story_id = Column(String(255), index=True)  # Story ID in Mesh system
    title = Column(String(500))
    content = Column(Text)
    url = Column(String(1000))  # Article URL
    image_url = Column(String(1000))  # Article image
    published_date = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    state = Column(String(50), default="published")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Pick(Base):
    """Pick model (corresponds to Mesh pick functionality)"""
    __tablename__ = "picks"
    
    id = Column(Integer, primary_key=True, index=True)
    pick_id = Column(String(500), unique=True, index=True, nullable=False)
    mesh_pick_id = Column(String(255), index=True)  # Pick ID in Mesh system
    actor_id = Column(Integer, ForeignKey("actors.id"), nullable=False)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    kind = Column(String(50), default="share")  # share, like, bookmark, etc.
    objective = Column(Text)  # Sharing purpose/description
    paywall = Column(Boolean, default=False)
    picked_date = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    state = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    actor = relationship("Actor", back_populates="picks")
    story = relationship("Story")
    comments = relationship("Comment", back_populates="pick")

class Comment(Base):
    """Comment 模型（對應 Mesh 的 comment 功能）"""
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(String(500), unique=True, index=True, nullable=False)
    mesh_comment_id = Column(String(255), index=True)  # Mesh 系統中的 Comment ID
    actor_id = Column(Integer, ForeignKey("actors.id"), nullable=False)
    pick_id = Column(Integer, ForeignKey("picks.id"), nullable=True)  # 可選，如果是 pick 的評論
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True)  # 回覆的評論
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    is_edited = Column(Boolean, default=False)
    state = Column(String(50), default="published")
    published_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 關聯
    actor = relationship("Actor", back_populates="comments")
    pick = relationship("Pick", back_populates="comments")
    parent = relationship("Comment", remote_side=[id], backref="replies")

class Note(Base):
    """ActivityPub Note 模型（對應 READr 文章）"""
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(String(500), unique=True, index=True, nullable=False)
    actor_id = Column(Integer, ForeignKey("actors.id"), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="text/html")
    summary = Column(Text)
    in_reply_to = Column(String(500))  # 回覆的 Note ID
    to = Column(JSON)  # 收件者列表
    cc = Column(JSON)  # 抄送列表
    attachment = Column(JSON)  # 附件列表
    tags = Column(JSON)  # 標籤列表
    is_public = Column(Boolean, default=True)
    is_sensitive = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 關聯
    actor = relationship("Actor")

class InboxItem(Base):
    """收件匣項目模型"""
    __tablename__ = "inbox_items"
    
    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(String(500), unique=True, index=True, nullable=False)
    actor_id = Column(String(500), nullable=False)  # 發送者 ID
    activity_data = Column(JSON, nullable=False)  # 完整活動資料
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))

class OutboxItem(Base):
    """發件匣項目模型"""
    __tablename__ = "outbox_items"
    
    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(String(500), unique=True, index=True, nullable=False)
    actor_id = Column(Integer, ForeignKey("actors.id"), nullable=False)
    activity_data = Column(JSON, nullable=False)  # 完整活動資料
    is_delivered = Column(Boolean, default=False)
    delivery_attempts = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True))
    
    # 關聯
    actor = relationship("Actor")

class FederationInstance(Base):
    """聯邦實例管理模型"""
    __tablename__ = "federation_instances"
    
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255))  # 實例名稱
    description = Column(Text)  # 實例描述
    software = Column(String(100))  # 使用的軟體（Mastodon, Pleroma, etc.）
    version = Column(String(50))  # 軟體版本
    protocol = Column(String(10), default="https")  # 協議
    port = Column(Integer, default=443)  # 端口
    
    # 狀態資訊
    is_active = Column(Boolean, default=True)  # 是否啟用
    is_approved = Column(Boolean, default=False)  # 是否已核准
    is_blocked = Column(Boolean, default=False)  # 是否被封鎖
    last_seen = Column(DateTime(timezone=True))  # 最後活動時間
    last_successful_connection = Column(DateTime(timezone=True))  # 最後成功連接時間
    
    # 統計資訊
    user_count = Column(Integer, default=0)  # 使用者數量
    post_count = Column(Integer, default=0)  # 文章數量
    connection_count = Column(Integer, default=0)  # 連接次數
    error_count = Column(Integer, default=0)  # 錯誤次數
    
    # 設定
    auto_follow = Column(Boolean, default=False)  # 是否自動追蹤
    auto_announce = Column(Boolean, default=True)  # 是否自動轉發
    max_followers = Column(Integer, default=1000)  # 最大追蹤者數量
    max_following = Column(Integer, default=1000)  # 最大追蹤中數量
    
    # 技術資訊
    nodeinfo_url = Column(String(500))  # NodeInfo URL
    webfinger_url = Column(String(500))  # WebFinger URL
    inbox_url = Column(String(500))  # 收件匣 URL
    outbox_url = Column(String(500))  # 發件匣 URL
    
    # 元資料
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 關聯
    connections = relationship("FederationConnection", back_populates="instance")
    activities = relationship("FederationActivity", back_populates="instance")

class FederationConnection(Base):
    """聯邦連接記錄模型"""
    __tablename__ = "federation_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("federation_instances.id"), nullable=False)
    connection_type = Column(String(50), nullable=False)  # follow, announce, like, etc.
    direction = Column(String(20), nullable=False)  # inbound, outbound
    
    # 連接詳情
    source_actor = Column(String(500))  # 來源 Actor
    target_actor = Column(String(500))  # 目標 Actor
    activity_id = Column(String(500))  # 活動 ID
    
    # 狀態
    status = Column(String(20), default="pending")  # pending, success, failed, blocked
    error_message = Column(Text)  # 錯誤訊息
    
    # 時間戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))  # 處理時間
    
    # 關聯
    instance = relationship("FederationInstance", back_populates="connections")

class FederationActivity(Base):
    """聯邦活動記錄模型"""
    __tablename__ = "federation_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("federation_instances.id"), nullable=False)
    activity_type = Column(String(100), nullable=False)  # Create, Follow, Like, etc.
    activity_id = Column(String(500), unique=True, index=True, nullable=False)
    
    # 活動內容
    actor_id = Column(String(500))  # 活動發送者
    object_data = Column(JSON)  # 活動物件資料
    target_data = Column(JSON)  # 目標物件資料
    
    # 狀態
    is_processed = Column(Boolean, default=False)  # 是否已處理
    is_public = Column(Boolean, default=True)  # 是否公開
    is_sensitive = Column(Boolean, default=False)  # 是否敏感內容
    
    # 時間戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))  # 處理時間
    
    # 關聯
    instance = relationship("FederationInstance", back_populates="activities")

class AccountMapping(Base):
    """帳號映射模型（對應 Mesh Member 在其他聯邦網站的帳號）"""
    __tablename__ = "account_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    mesh_member_id = Column(String(255), index=True, nullable=False)  # Mesh Member ID
    local_actor_id = Column(Integer, ForeignKey("actors.id"), nullable=False)  # 本地 Actor ID
    
    # 遠端帳號資訊
    remote_actor_id = Column(String(500), nullable=False)  # 遠端 Actor ID (完整 URL)
    remote_username = Column(String(255), nullable=False)  # 遠端使用者名稱
    remote_domain = Column(String(255), nullable=False)  # 遠端域名
    remote_display_name = Column(String(255))  # 遠端顯示名稱
    remote_avatar_url = Column(String(500))  # 遠端頭像 URL
    remote_summary = Column(Text)  # 遠端個人簡介
    
    # 映射狀態
    is_verified = Column(Boolean, default=False)  # 是否已驗證
    verification_method = Column(String(50))  # 驗證方法 (manual, webfinger, activity)
    verification_date = Column(DateTime(timezone=True))  # 驗證日期
    
    # 同步設定
    sync_enabled = Column(Boolean, default=True)  # 是否啟用同步
    sync_posts = Column(Boolean, default=True)  # 是否同步貼文
    sync_follows = Column(Boolean, default=True)  # 是否同步追蹤
    sync_likes = Column(Boolean, default=True)  # 是否同步按讚
    sync_announces = Column(Boolean, default=True)  # 是否同步轉發
    
    # 同步狀態
    last_sync_at = Column(DateTime(timezone=True))  # 最後同步時間
    sync_error_count = Column(Integer, default=0)  # 同步錯誤次數
    last_sync_error = Column(Text)  # 最後同步錯誤訊息
    
    # 統計資訊
    remote_follower_count = Column(Integer, default=0)  # 遠端追蹤者數量
    remote_following_count = Column(Integer, default=0)  # 遠端追蹤中數量
    remote_post_count = Column(Integer, default=0)  # 遠端貼文數量
    
    # 元資料
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 關聯
    local_actor = relationship("Actor", back_populates="account_mappings")
    sync_tasks = relationship("AccountSyncTask", back_populates="account_mapping")

class AccountSyncTask(Base):
    """帳號同步任務模型"""
    __tablename__ = "account_sync_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    mapping_id = Column(Integer, ForeignKey("account_mappings.id"), nullable=False)
    sync_type = Column(String(50), nullable=False)  # posts, follows, likes, announces, profile
    
    # 任務狀態
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)  # 進度百分比 (0-100)
    
    # 同步範圍
    since_date = Column(DateTime(timezone=True))  # 同步起始日期
    until_date = Column(DateTime(timezone=True))  # 同步結束日期
    max_items = Column(Integer, default=100)  # 最大同步項目數
    
    # 結果統計
    items_processed = Column(Integer, default=0)  # 已處理項目數
    items_synced = Column(Integer, default=0)  # 已同步項目數
    items_failed = Column(Integer, default=0)  # 失敗項目數
    
    # 錯誤資訊
    error_message = Column(Text)  # 錯誤訊息
    retry_count = Column(Integer, default=0)  # 重試次數
    max_retries = Column(Integer, default=3)  # 最大重試次數
    
    # 時間戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))  # 開始時間
    completed_at = Column(DateTime(timezone=True))  # 完成時間
    
    # 關聯
    account_mapping = relationship("AccountMapping", back_populates="sync_tasks")

class AccountDiscovery(Base):
    """帳號發現記錄模型"""
    __tablename__ = "account_discoveries"
    
    id = Column(Integer, primary_key=True, index=True)
    mesh_member_id = Column(String(255), ForeignKey("actors.mesh_member_id"), index=True, nullable=False)  # Mesh Member ID
    
    # 發現資訊
    discovery_method = Column(String(50), nullable=False)  # manual, webfinger, activity, search
    search_query = Column(String(500))  # 搜尋查詢
    discovered_actor_id = Column(String(500))  # 發現的 Actor ID
    discovered_username = Column(String(255))  # 發現的使用者名稱
    discovered_domain = Column(String(255))  # 發現的域名
    
    # 發現結果
    is_successful = Column(Boolean, default=False)  # 是否成功
    confidence_score = Column(Float, default=0.0)  # 信心分數 (0-1)
    match_reason = Column(Text)  # 匹配原因
    
    # 驗證資訊
    verification_attempted = Column(Boolean, default=False)  # 是否嘗試驗證
    verification_successful = Column(Boolean, default=False)  # 驗證是否成功
    verification_method = Column(String(50))  # 驗證方法
    
    # 元資料
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))  # 處理時間
    
    # 關聯（已於欄位定義中設置 ForeignKey）
