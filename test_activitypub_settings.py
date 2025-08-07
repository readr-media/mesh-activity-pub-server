#!/usr/bin/env python3
"""
Test script for ActivityPub settings functionality
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8000"
MEMBER_ID = "test_member_123"

async def test_activitypub_settings():
    """Test ActivityPub settings functionality"""
    async with httpx.AsyncClient() as client:
        print("🧪 Starting ActivityPub settings test...")
        
        # 1. Get Member info (including ActivityPub settings)
        print("\n1. Getting Member info...")
        try:
            response = await client.get(f"{BASE_URL}/api/v1/mesh/members/{MEMBER_ID}")
            if response.status_code == 200:
                member_data = response.json()
                print(f"✅ Member info retrieved successfully")
                print(f"   - ActivityPub enabled: {member_data.get('activitypub_enabled', False)}")
                print(f"   - Auto follow: {member_data.get('activitypub_auto_follow', True)}")
                print(f"   - Public posts: {member_data.get('activitypub_public_posts', True)}")
                print(f"   - Federation enabled: {member_data.get('activitypub_federation_enabled', True)}")
            else:
                print(f"❌ Failed to get Member info: {response.status_code}")
                return
        except Exception as e:
            print(f"❌ Error getting Member info: {e}")
            return
        
        # 2. Get ActivityPub settings
        print("\n2. Getting ActivityPub settings...")
        try:
            response = await client.get(f"{BASE_URL}/api/v1/mesh/members/{MEMBER_ID}/activitypub-settings")
            if response.status_code == 200:
                settings = response.json()
                print(f"✅ ActivityPub settings retrieved successfully")
                print(f"   - Settings content: {json.dumps(settings, indent=2, ensure_ascii=False)}")
            else:
                print(f"❌ Failed to get ActivityPub settings: {response.status_code}")
                return
        except Exception as e:
            print(f"❌ Error getting ActivityPub settings: {e}")
            return
        
        # 3. Update ActivityPub settings
        print("\n3. Updating ActivityPub settings...")
        new_settings = {
            "activitypub_enabled": True,
            "activitypub_auto_follow": False,
            "activitypub_public_posts": True,
            "activitypub_federation_enabled": False
        }
        
        try:
            response = await client.put(
                f"{BASE_URL}/api/v1/mesh/members/{MEMBER_ID}/activitypub-settings",
                json=new_settings
            )
            if response.status_code == 200:
                updated_settings = response.json()
                print(f"✅ ActivityPub settings updated successfully")
                print(f"   - Updated settings: {json.dumps(updated_settings, indent=2, ensure_ascii=False)}")
            else:
                print(f"❌ Failed to update ActivityPub settings: {response.status_code}")
                print(f"   - Error message: {response.text}")
                return
        except Exception as e:
            print(f"❌ Error updating ActivityPub settings: {e}")
            return
        
        # 4. Verify settings have been updated
        print("\n4. Verifying settings have been updated...")
        try:
            response = await client.get(f"{BASE_URL}/api/v1/mesh/members/{MEMBER_ID}/activitypub-settings")
            if response.status_code == 200:
                settings = response.json()
                print(f"✅ Settings verification successful")
                print(f"   - Verification result: {json.dumps(settings, indent=2, ensure_ascii=False)}")
                
                # Check if settings were updated correctly
                if (settings.get("activitypub_enabled") == True and
                    settings.get("activitypub_auto_follow") == False and
                    settings.get("activitypub_public_posts") == True and
                    settings.get("activitypub_federation_enabled") == False):
                    print("✅ All settings updated correctly!")
                else:
                    print("❌ Settings update verification failed")
            else:
                print(f"❌ Settings verification failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error verifying settings: {e}")
        
        print("\n🎉 ActivityPub settings functionality test completed!")

if __name__ == "__main__":
    asyncio.run(test_activitypub_settings())
