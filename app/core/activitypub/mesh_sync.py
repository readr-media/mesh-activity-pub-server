"""
Mesh synchronization module for ActivityPub activities
Handles syncing ActivityPub activities to Mesh system via GraphQL
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.graphql_client import GraphQLClient
from app.models.activitypub import Actor, Pick, Comment, Story
from app.core.activitypub.mesh_utils import parse_mesh_pick_from_activity, parse_mesh_comment_from_activity
from app.core.config import settings

class MeshSyncManager:
    """Mesh synchronization manager for ActivityPub activities"""
    
    def __init__(self):
        self.graphql_client = GraphQLClient()
    
    async def sync_activity_to_mesh(self, activity_data: Dict[str, Any], db: AsyncSession) -> bool:
        """Sync ActivityPub activity to Mesh system"""
        activity_type = activity_data.get("type")
        
        if activity_type == "Create":
            return await self._sync_create_activity(activity_data, db)
        elif activity_type == "Like":
            return await self._sync_like_activity(activity_data, db)
        elif activity_type == "Announce":
            return await self._sync_announce_activity(activity_data, db)
        elif activity_type == "Follow":
            return await self._sync_follow_activity(activity_data, db)
        
        return False
    
    async def _sync_create_activity(self, activity_data: Dict[str, Any], db: AsyncSession) -> bool:
        """Sync Create activity to Mesh"""
        object_data = activity_data.get("object", {})
        object_type = object_data.get("type")
        
        if object_type == "Note":
            # Check if it's a Mesh Pick or Comment
            if await self._is_mesh_pick(object_data):
                return await self._sync_pick_to_mesh(activity_data, db)
            elif await self._is_mesh_comment(object_data):
                return await self._sync_comment_to_mesh(activity_data, db)
            else:
                # Handle standard ActivityPub Note
                return await self._sync_standard_note_to_mesh(activity_data, db)
        elif object_type == "Article":
            return await self._sync_article_to_mesh(activity_data, db)
        
        return False
    
    async def _sync_standard_note_to_mesh(self, activity_data: Dict[str, Any], db: AsyncSession) -> bool:
        """Sync standard ActivityPub Note to Mesh (Pick + Comment)"""
        try:
            object_data = activity_data.get("object", {})
            
            # Get or create Actor
            actor_id = activity_data.get("actor")
            actor = await self._get_or_create_actor(actor_id, db)
            
            if not actor:
                print(f"Failed to get/create actor: {actor_id}")
                return False
            
            # Check if Note already exists
            existing_pick = await self._get_existing_pick(activity_data.get("object", {}).get("id"), db)
            if existing_pick:
                print(f"Note already synced as Pick: {existing_pick.pick_id}")
                return True
            
            # Determine if this Note should become a Pick or Comment
            if await self._should_become_pick(object_data):
                return await self._convert_note_to_pick(activity_data, db)
            else:
                return await self._convert_note_to_comment(activity_data, db)
                
        except Exception as e:
            print(f"Error syncing standard Note to Mesh: {e}")
            return False
    
    async def _should_become_pick(self, object_data: Dict[str, Any]) -> bool:
        """Determine if ActivityPub Note should become a Mesh Pick"""
        content = object_data.get("content", "")
        
        # Check for URL patterns in content
        import re
        url_patterns = [
            r'https?://[^\s]+',
            r'www\.[^\s]+',
            r'readr\.tw',
            r'分享',
            r'推薦',
            r'分享這篇文章',
            r'推薦閱讀'
        ]
        
        for pattern in url_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        # Check for attachments with URLs
        attachments = object_data.get("attachment", [])
        for attachment in attachments:
            if attachment.get("type") == "Link" and attachment.get("href"):
                return True
        
        # Check for tags that indicate sharing
        tags = object_data.get("tag", [])
        for tag in tags:
            if isinstance(tag, dict) and tag.get("name") in ["分享", "推薦", "文章"]:
                return True
        
        return False
    
    async def _convert_note_to_pick(self, activity_data: Dict[str, Any], db: AsyncSession) -> bool:
        """Convert ActivityPub Note to Mesh Pick"""
        try:
            object_data = activity_data.get("object", {})
            content = object_data.get("content", "")
            
            # Extract URL from content
            import re
            url_match = re.search(r'https?://[^\s]+', content)
            url = url_match.group(0) if url_match else None
            
            # Extract title from content or use default
            title_match = re.search(r'分享[：:]\s*(.+)', content)
            title = title_match.group(1) if title_match else "分享的文章"
            
            # Get or create Actor
            actor_id = activity_data.get("actor")
            actor = await self._get_or_create_actor(actor_id, db)
            
            if not actor:
                return False
            
            # Create story info
            story_info = {
                "title": title,
                "url": url,
                "image_url": None
            }
            
            # Get or create story ID
            story_id = await self._get_or_create_story_id(story_info)
            
            # Prepare Pick data
            pick_input = {
                "storyId": story_id,
                "objective": content,
                "kind": "share",
                "paywall": False,
                "memberId": actor.mesh_member_id
            }
            
            # Create Pick in Mesh
            result = await self.graphql_client.create_pick(pick_input)
            
            if result:
                # Update local Pick record
                await self._update_local_pick_with_mesh_id(
                    activity_data.get("object", {}).get("id"),
                    result.get("id"),
                    db
                )
                print(f"Successfully converted Note to Pick: {result.get('id')}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error converting Note to Pick: {e}")
            return False
    
    async def _convert_note_to_comment(self, activity_data: Dict[str, Any], db: AsyncSession) -> bool:
        """Convert ActivityPub Note to Mesh Comment"""
        try:
            object_data = activity_data.get("object", {})
            content = object_data.get("content", "")
            
            # Get or create Actor
            actor_id = activity_data.get("actor")
            actor = await self._get_or_create_actor(actor_id, db)
            
            if not actor:
                return False
            
            # Check if this is a reply to a Pick
            in_reply_to = object_data.get("inReplyTo")
            pick_id = None
            
            if in_reply_to:
                # Try to find the Pick this comment is replying to
                pick = await self._find_pick_by_activity_id(in_reply_to, db)
                if pick and pick.mesh_pick_id:
                    pick_id = pick.mesh_pick_id
            
            # Prepare Comment data
            comment_input = {
                "content": content,
                "memberId": actor.mesh_member_id
            }
            
            if pick_id:
                comment_input["pickId"] = pick_id
            
            # Create Comment in Mesh
            result = await self.graphql_client.create_comment(comment_input)
            
            if result:
                # Update local Comment record
                await self._update_local_comment_with_mesh_id(
                    activity_data.get("object", {}).get("id"),
                    result.get("id"),
                    db
                )
                print(f"Successfully converted Note to Comment: {result.get('id')}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error converting Note to Comment: {e}")
            return False
    
    async def _sync_pick_to_mesh(self, activity_data: Dict[str, Any], db: AsyncSession) -> bool:
        """Sync Pick activity to Mesh system"""
        try:
            # Parse Pick data from ActivityPub
            pick_info = parse_mesh_pick_from_activity(activity_data)
            
            # Get or create Actor
            actor_id = activity_data.get("actor")
            actor = await self._get_or_create_actor(actor_id, db)
            
            if not actor:
                print(f"Failed to get/create actor: {actor_id}")
                return False
            
            # Check if Pick already exists
            existing_pick = await self._get_existing_pick(activity_data.get("object", {}).get("id"), db)
            if existing_pick:
                print(f"Pick already exists: {existing_pick.pick_id}")
                return True
            
            # Prepare Pick data for Mesh
            pick_input = {
                "storyId": await self._get_or_create_story_id(pick_info["story"]),
                "objective": pick_info["pick"]["objective"],
                "kind": pick_info["pick"]["kind"],
                "paywall": False,
                "memberId": actor.mesh_member_id
            }
            
            # Create Pick in Mesh via GraphQL
            result = await self.graphql_client.create_pick(pick_input)
            
            if result:
                # Update local Pick record with Mesh ID
                await self._update_local_pick_with_mesh_id(
                    activity_data.get("object", {}).get("id"),
                    result.get("id"),
                    db
                )
                print(f"Successfully synced Pick to Mesh: {result.get('id')}")
                return True
            else:
                print("Failed to create Pick in Mesh system")
                return False
                
        except Exception as e:
            print(f"Error syncing Pick to Mesh: {e}")
            return False
    
    async def _sync_comment_to_mesh(self, activity_data: Dict[str, Any], db: AsyncSession) -> bool:
        """Sync Comment activity to Mesh system"""
        try:
            # Parse Comment data from ActivityPub
            comment_info = parse_mesh_comment_from_activity(activity_data)
            
            # Get or create Actor
            actor_id = activity_data.get("actor")
            actor = await self._get_or_create_actor(actor_id, db)
            
            if not actor:
                print(f"Failed to get/create actor: {actor_id}")
                return False
            
            # Check if Comment already exists
            existing_comment = await self._get_existing_comment(activity_data.get("object", {}).get("id"), db)
            if existing_comment:
                print(f"Comment already exists: {existing_comment.comment_id}")
                return True
            
            # Prepare Comment data for Mesh
            comment_input = {
                "content": comment_info["content"],
                "memberId": actor.mesh_member_id
            }
            
            # Add parent comment if exists
            if comment_info["in_reply_to"]:
                parent_comment = await self._get_comment_by_activity_id(comment_info["in_reply_to"], db)
                if parent_comment and parent_comment.mesh_comment_id:
                    comment_input["parentId"] = parent_comment.mesh_comment_id
            
            # Add pick reference if exists
            if comment_info["in_reply_to"] and "picks" in comment_info["in_reply_to"]:
                pick = await self._get_pick_by_activity_id(comment_info["in_reply_to"], db)
                if pick and pick.mesh_pick_id:
                    comment_input["pickId"] = pick.mesh_pick_id
            
            # Create Comment in Mesh via GraphQL
            result = await self.graphql_client.create_comment(comment_input)
            
            if result:
                # Update local Comment record with Mesh ID
                await self._update_local_comment_with_mesh_id(
                    activity_data.get("object", {}).get("id"),
                    result.get("id"),
                    db
                )
                print(f"Successfully synced Comment to Mesh: {result.get('id')}")
                return True
            else:
                print("Failed to create Comment in Mesh system")
                return False
                
        except Exception as e:
            print(f"Error syncing Comment to Mesh: {e}")
            return False
    
    async def _sync_like_activity(self, activity_data: Dict[str, Any], db: AsyncSession) -> bool:
        """Sync Like activity to Mesh system"""
        try:
            # Get Actor
            actor_id = activity_data.get("actor")
            actor = await self._get_or_create_actor(actor_id, db)
            
            if not actor:
                return False
            
            # Get liked object
            object_id = activity_data.get("object")
            
            # Check if it's a Pick like（Keystone 目前不支援 Pick like 關聯，僅送出 AP Like）
            pick = await self._get_pick_by_activity_id(object_id, db)
            if pick and pick.mesh_pick_id:
                return True
            
            # Check if it's a Comment like
            comment = await self._get_comment_by_activity_id(object_id, db)
            if comment and comment.mesh_comment_id:
                result = await self.graphql_client.like_comment(comment.mesh_comment_id, actor.mesh_member_id)
                if result:
                    print(f"Successfully synced Comment like to Mesh: {result.get('id')}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error syncing Like activity to Mesh: {e}")
            return False
    
    async def _sync_follow_activity(self, activity_data: Dict[str, Any], db: AsyncSession) -> bool:
        """Sync Follow activity to Mesh system"""
        try:
            # Get follower and following actors
            follower_id = activity_data.get("actor")
            following_id = activity_data.get("object")
            
            follower = await self._get_or_create_actor(follower_id, db)
            following = await self._get_or_create_actor(following_id, db)
            
            if not follower or not following:
                return False
            
            # Create follow relationship in Mesh
            result = await self.graphql_client.follow_member(
                follower.mesh_member_id,
                following.mesh_member_id
            )
            
            if result:
                print(f"Successfully synced Follow to Mesh: {result.get('id')}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error syncing Follow activity to Mesh: {e}")
            return False
    
    async def _is_mesh_pick(self, object_data: Dict[str, Any]) -> bool:
        """Check if object is a Mesh Pick"""
        attachments = object_data.get("attachment", [])
        for attachment in attachments:
            if attachment.get("type") == "Link" and attachment.get("href"):
                return True
        return False
    
    async def _is_mesh_comment(self, object_data: Dict[str, Any]) -> bool:
        """Check if object is a Mesh Comment"""
        in_reply_to = object_data.get("inReplyTo")
        if in_reply_to and ("picks" in in_reply_to or "comments" in in_reply_to):
            return True
        return False
    
    async def _get_or_create_actor(self, actor_id: str, db: AsyncSession) -> Optional[Actor]:
        """Get or create Actor from ActivityPub actor ID"""
        # Extract domain and username from actor ID
        # Format: https://domain.com/users/username
        parts = actor_id.split("/")
        if len(parts) >= 2:
            domain = parts[2]  # domain.com
            username = parts[-1]  # username
            
            # Check if actor exists
            result = await db.execute(
                select(Actor).where(
                    Actor.username == username,
                    Actor.domain == domain
                )
            )
            actor = result.scalar_one_or_none()
            
            if actor:
                return actor
            
            # Create new actor (basic info)
            actor = Actor(
                username=username,
                domain=domain,
                is_local=False,
                public_key_pem="",  # Will be fetched later
                inbox_url=f"{actor_id}/inbox",
                outbox_url=f"{actor_id}/outbox"
            )
            
            db.add(actor)
            await db.commit()
            await db.refresh(actor)
            
            return actor
        
        return None
    
    async def _get_or_create_story_id(self, story_info: Dict[str, Any]) -> str:
        """Get or create Story ID in Mesh system"""
        # This would typically involve creating a story in Mesh
        # For now, return a placeholder
        return "story_placeholder"
    
    async def _get_existing_pick(self, activity_id: str, db: AsyncSession) -> Optional[Pick]:
        """Get existing Pick by ActivityPub ID"""
        result = await db.execute(
            select(Pick).where(Pick.pick_id == activity_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_existing_comment(self, activity_id: str, db: AsyncSession) -> Optional[Comment]:
        """Get existing Comment by ActivityPub ID"""
        result = await db.execute(
            select(Comment).where(Comment.comment_id == activity_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_pick_by_activity_id(self, activity_id: str, db: AsyncSession) -> Optional[Pick]:
        """Get Pick by ActivityPub ID"""
        result = await db.execute(
            select(Pick).where(Pick.pick_id == activity_id)
        )
        return result.scalar_one_or_none()
    
    async def _find_pick_by_activity_id(self, activity_id: str, db: AsyncSession) -> Optional[Pick]:
        """Find Pick by ActivityPub ID (including partial matches)"""
        # Try exact match first
        pick = await self._get_pick_by_activity_id(activity_id, db)
        if pick:
            return pick
        
        # Try partial match (for cases where activity_id is a Note ID that might be related to a Pick)
        # This is a simplified approach - in practice, you might need more sophisticated logic
        return None
    
    async def _get_comment_by_activity_id(self, activity_id: str, db: AsyncSession) -> Optional[Comment]:
        """Get Comment by ActivityPub ID"""
        result = await db.execute(
            select(Comment).where(Comment.comment_id == activity_id)
        )
        return result.scalar_one_or_none()
    
    async def _update_local_pick_with_mesh_id(self, activity_id: str, mesh_id: str, db: AsyncSession):
        """Update local Pick record with Mesh ID"""
        result = await db.execute(
            select(Pick).where(Pick.pick_id == activity_id)
        )
        pick = result.scalar_one_or_none()
        
        if pick:
            pick.mesh_pick_id = mesh_id
            await db.commit()
    
    async def _update_local_comment_with_mesh_id(self, activity_id: str, mesh_id: str, db: AsyncSession):
        """Update local Comment record with Mesh ID"""
        result = await db.execute(
            select(Comment).where(Comment.comment_id == activity_id)
        )
        comment = result.scalar_one_or_none()
        
        if comment:
            comment.mesh_comment_id = mesh_id
            await db.commit()

# Global instance
mesh_sync_manager = MeshSyncManager()
