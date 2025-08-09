"""Local ORM models removed (migrated to GraphQL).

This file is intentionally left as a placeholder to avoid import errors
while downstream code is being fully migrated. Do not reintroduce ORM here.
"""

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
