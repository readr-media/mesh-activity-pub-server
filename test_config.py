"""
測試環境配置
用於 CI/CD 和本地測試的 mock data 設定
"""

import os
from typing import Dict, Any

# 測試環境的 mock data
TEST_MOCK_DATA = {
    "members": {
        "test": {
            "id": "test-member-id",
            "nickname": "test",
            "name": "Test User",
            "email": "test@example.com",
            "avatar": "https://example.com/avatar.jpg",
            "bio": "Test user bio"
        }
    },
    "actors": {
        "test": {
            "id": "test-actor-id",
            "username": "test",
            "domain": "activity.readr.tw",
            "display_name": "Test User",
            "summary": "Test user summary",
            "icon_url": "https://example.com/avatar.jpg",
            "is_local": True,
            "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----"
        }
    },
    "stories": [
        {
            "id": "test-story-1",
            "title": "Test Story",
            "content": "This is a test story content",
            "author_id": "test-member-id",
            "created_at": "2024-01-01T00:00:00Z"
        }
    ],
    "picks": [
        {
            "id": "test-pick-1",
            "story_id": "test-story-1",
            "member_id": "test-member-id",
            "comment": "Great story!",
            "created_at": "2024-01-01T00:00:00Z"
        }
    ],
    "comments": [
        {
            "id": "test-comment-1",
            "story_id": "test-story-1",
            "member_id": "test-member-id",
            "content": "Interesting article",
            "created_at": "2024-01-01T00:00:00Z"
        }
    ],
    "federation_instances": [
        {
            "id": "test-instance-1",
            "domain": "mastodon.social",
            "name": "Mastodon Social",
            "description": "Test federation instance",
            "software": "mastodon",
            "version": "4.0.0",
            "is_active": True
        }
    ]
}

# 測試環境變數
TEST_ENV_VARS = {
    "GRAPHQL_MOCK": "true",
    "ACTIVITYPUB_DOMAIN": "localhost:8000",
    "SECRET_KEY": "test-secret-key-for-ci-cd",
    "REDIS_URL": "redis://localhost:6379",
    "GRAPHQL_ENDPOINT": "http://localhost:3000/api/graphql",
    "FEDERATION_ENABLED": "true",
    "MAX_FOLLOWERS": "1000",
    "MAX_FOLLOWING": "1000"
}

def get_test_config() -> Dict[str, Any]:
    """獲取測試配置"""
    return {
        "mock_data": TEST_MOCK_DATA,
        "env_vars": TEST_ENV_VARS
    }

def setup_test_environment():
    """設定測試環境變數"""
    for key, value in TEST_ENV_VARS.items():
        os.environ[key] = value

def get_mock_member(username: str) -> Dict[str, Any]:
    """獲取 mock member 資料"""
    return TEST_MOCK_DATA["members"].get(username, {})

def get_mock_actor(username: str) -> Dict[str, Any]:
    """獲取 mock actor 資料"""
    return TEST_MOCK_DATA["actors"].get(username, {})

def get_mock_stories() -> list:
    """獲取 mock stories 資料"""
    return TEST_MOCK_DATA["stories"]

def get_mock_picks() -> list:
    """獲取 mock picks 資料"""
    return TEST_MOCK_DATA["picks"]

def get_mock_comments() -> list:
    """獲取 mock comments 資料"""
    return TEST_MOCK_DATA["comments"]

def get_mock_federation_instances() -> list:
    """獲取 mock federation instances 資料"""
    return TEST_MOCK_DATA["federation_instances"]

# CI/CD 特定的測試配置
CI_TEST_CONFIG = {
    "timeout": 30,  # 秒
    "retry_count": 3,
    "health_check_endpoints": [
        "/",
        "/api/v1/health/",
        "/.well-known/nodeinfo"
    ],
    "expected_status_codes": {
        "basic_endpoints": 200,
        "activitypub_endpoints": [200, 404],  # 某些端點可能返回 404
        "api_endpoints": [200, 400, 500]  # API 端點可能返回各種狀態碼
    }
}
