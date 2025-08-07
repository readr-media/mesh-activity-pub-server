#!/usr/bin/env python3
"""
Test script for ActivityPub to Mesh synchronization
"""

import asyncio
import json
from typing import Dict, Any

# Sample ActivityPub activities for testing
SAMPLE_PICK_ACTIVITY = {
    "type": "Create",
    "actor": "https://mastodon.social/users/testuser",
    "object": {
        "type": "Note",
        "id": "https://mastodon.social/objects/pick_123",
        "content": "這篇文章很有趣，推薦大家閱讀！",
        "attachment": [
            {
                "type": "Link",
                "href": "https://readr.tw/story/123",
                "name": "測試文章標題"
            }
        ],
        "published": "2024-01-01T12:00:00Z"
    },
    "published": "2024-01-01T12:00:00Z"
}

SAMPLE_COMMENT_ACTIVITY = {
    "type": "Create",
    "actor": "https://mastodon.social/users/testuser",
    "object": {
        "type": "Note",
        "id": "https://mastodon.social/objects/comment_456",
        "content": "我也覺得這篇文章很棒！",
        "inReplyTo": "https://activity.readr.tw/picks/pick_123",
        "published": "2024-01-01T12:30:00Z"
    },
    "published": "2024-01-01T12:30:00Z"
}

# Standard ActivityPub Note that should become a Pick
SAMPLE_SHARE_NOTE = {
    "type": "Create",
    "actor": "https://mastodon.social/users/testuser",
    "object": {
        "type": "Note",
        "id": "https://mastodon.social/objects/note_789",
        "content": "分享：這是一篇很棒的文章 https://readr.tw/story/456 推薦大家閱讀！",
        "published": "2024-01-01T15:00:00Z"
    },
    "published": "2024-01-01T15:00:00Z"
}

# Standard ActivityPub Note that should become a Comment
SAMPLE_GENERAL_NOTE = {
    "type": "Create",
    "actor": "https://mastodon.social/users/testuser",
    "object": {
        "type": "Note",
        "id": "https://mastodon.social/objects/note_101",
        "content": "今天天氣真好！",
        "published": "2024-01-01T16:00:00Z"
    },
    "published": "2024-01-01T16:00:00Z"
}

# Standard ActivityPub Note with URL attachment
SAMPLE_NOTE_WITH_ATTACHMENT = {
    "type": "Create",
    "actor": "https://mastodon.social/users/testuser",
    "object": {
        "type": "Note",
        "id": "https://mastodon.social/objects/note_202",
        "content": "這篇文章值得一讀",
        "attachment": [
            {
                "type": "Link",
                "href": "https://readr.tw/story/789",
                "name": "值得閱讀的文章"
            }
        ],
        "published": "2024-01-01T17:00:00Z"
    },
    "published": "2024-01-01T17:00:00Z"
}

SAMPLE_LIKE_ACTIVITY = {
    "type": "Like",
    "actor": "https://mastodon.social/users/testuser",
    "object": "https://activity.readr.tw/picks/pick_123",
    "published": "2024-01-01T13:00:00Z"
}

SAMPLE_FOLLOW_ACTIVITY = {
    "type": "Follow",
    "actor": "https://mastodon.social/users/testuser",
    "object": "https://activity.readr.tw/users/readruser",
    "published": "2024-01-01T14:00:00Z"
}

async def test_mesh_sync():
    """Test Mesh synchronization functionality"""
    print("🧪 Testing ActivityPub to Mesh synchronization...")
    
    # Import required modules
    from app.core.activitypub.mesh_sync import mesh_sync_manager
    from app.core.database import get_db
    
    async with get_db() as db:
        print("\n1. Testing Mesh Pick synchronization...")
        success = await mesh_sync_manager.sync_activity_to_mesh(SAMPLE_PICK_ACTIVITY, db)
        print(f"   Mesh Pick sync result: {'✅ Success' if success else '❌ Failed'}")
        
        print("\n2. Testing Mesh Comment synchronization...")
        success = await mesh_sync_manager.sync_activity_to_mesh(SAMPLE_COMMENT_ACTIVITY, db)
        print(f"   Mesh Comment sync result: {'✅ Success' if success else '❌ Failed'}")
        
        print("\n3. Testing standard Note to Pick conversion...")
        success = await mesh_sync_manager.sync_activity_to_mesh(SAMPLE_SHARE_NOTE, db)
        print(f"   Note to Pick conversion result: {'✅ Success' if success else '❌ Failed'}")
        
        print("\n4. Testing standard Note to Comment conversion...")
        success = await mesh_sync_manager.sync_activity_to_mesh(SAMPLE_GENERAL_NOTE, db)
        print(f"   Note to Comment conversion result: {'✅ Success' if success else '❌ Failed'}")
        
        print("\n5. Testing Note with attachment to Pick conversion...")
        success = await mesh_sync_manager.sync_activity_to_mesh(SAMPLE_NOTE_WITH_ATTACHMENT, db)
        print(f"   Note with attachment to Pick result: {'✅ Success' if success else '❌ Failed'}")
        
        print("\n6. Testing Like synchronization...")
        success = await mesh_sync_manager.sync_activity_to_mesh(SAMPLE_LIKE_ACTIVITY, db)
        print(f"   Like sync result: {'✅ Success' if success else '❌ Failed'}")
        
        print("\n7. Testing Follow synchronization...")
        success = await mesh_sync_manager.sync_activity_to_mesh(SAMPLE_FOLLOW_ACTIVITY, db)
        print(f"   Follow sync result: {'✅ Success' if success else '❌ Failed'}")
    
    print("\n🎉 Mesh synchronization test completed!")

async def test_note_classification():
    """Test Note classification logic"""
    print("\n🧪 Testing Note classification logic...")
    
    from app.core.activitypub.mesh_sync import mesh_sync_manager
    from app.core.database import get_db
    
    async with get_db() as db:
        # Test different types of notes
        test_cases = [
            ("Share note with URL", SAMPLE_SHARE_NOTE),
            ("General note", SAMPLE_GENERAL_NOTE),
            ("Note with attachment", SAMPLE_NOTE_WITH_ATTACHMENT),
        ]
        
        for description, activity in test_cases:
            print(f"\nTesting: {description}")
            object_data = activity.get("object", {})
            
            # Test classification logic
            should_be_pick = await mesh_sync_manager._should_become_pick(object_data)
            print(f"   Should become Pick: {'✅ Yes' if should_be_pick else '❌ No'}")
            
            # Test actual conversion
            success = await mesh_sync_manager.sync_activity_to_mesh(activity, db)
            print(f"   Conversion result: {'✅ Success' if success else '❌ Failed'}")
    
    print("\n🎉 Note classification test completed!")

async def test_activity_processing():
    """Test complete activity processing pipeline"""
    print("\n🧪 Testing complete activity processing pipeline...")
    
    from app.core.activitypub.processor import process_activity
    from app.core.database import get_db
    
    async with get_db() as db:
        test_cases = [
            ("Mesh Pick", SAMPLE_PICK_ACTIVITY),
            ("Mesh Comment", SAMPLE_COMMENT_ACTIVITY),
            ("Standard Note (should become Pick)", SAMPLE_SHARE_NOTE),
            ("Standard Note (should become Comment)", SAMPLE_GENERAL_NOTE),
            ("Note with attachment", SAMPLE_NOTE_WITH_ATTACHMENT),
            ("Like", SAMPLE_LIKE_ACTIVITY),
            ("Follow", SAMPLE_FOLLOW_ACTIVITY),
        ]
        
        for description, activity in test_cases:
            print(f"\nProcessing: {description}")
            try:
                await process_activity(activity, db)
                print(f"   ✅ {description} processed successfully")
            except Exception as e:
                print(f"   ❌ {description} processing failed: {e}")
    
    print("\n🎉 Activity processing test completed!")

if __name__ == "__main__":
    asyncio.run(test_mesh_sync())
    asyncio.run(test_note_classification())
    asyncio.run(test_activity_processing())
