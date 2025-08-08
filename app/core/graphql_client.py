import httpx
from typing import Dict, Any, Optional, List
from app.core.config import settings

class GraphQLClient:
    """GraphQL client"""
    
    def __init__(self, endpoint: Optional[str] = None, token: Optional[str] = None):
        self.endpoint = endpoint or settings.GRAPHQL_ENDPOINT
        self.token = token or settings.GRAPHQL_TOKEN
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
    
    async def query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"data": {"mock": True}}
        payload = {"query": query, "variables": variables or {}}
        async with httpx.AsyncClient() as client:
            response = await client.post(self.endpoint, json=payload, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    async def mutation(self, mutation: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self.query(mutation, variables)
    
    async def get_member(self, member_id: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {
                "id": member_id,
                "name": "Local Test",
                "nickname": "localtest",
                "email": "local@test",
                "avatar": None,
                "intro": None,
                "is_active": True,
                "verified": False,
                "language": "zh_TW",
                "followerCount": 0,
                "followingCount": 0,
                "pickCount": 0,
                "commentCount": 0,
                "activitypub_enabled": True,
                "activitypub_auto_follow": True,
                "activitypub_public_posts": True,
                "activitypub_federation_enabled": True,
            }
        query = """
        query GetMember($id: ID!) {
            Member(where: { id: $id }) {
                id
                name
                nickname
                email
                avatar
                intro
                is_active
                verified
                language
            }
        }
        """
        try:
            result = await self.query(query, {"id": member_id})
            return result.get("data", {}).get("Member")
        except Exception as e:
            print(f"Error fetching member: {e}")
            return None
    
    async def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {
                "id": story_id,
                "title": "分享的文章",
                "content": "",
                "url": f"https://readr.tw/story/{story_id}",
                "image": None,
                "published_date": None,
                "state": "published",
                "is_active": True,
            }
        query = """
        query GetStory($id: ID!) {
            Story(where: { id: $id }) { id title url image published_date state is_active }
        }
        """
        try:
            result = await self.query(query, {"id": story_id})
            return result.get("data", {}).get("Story")
        except Exception as e:
            print(f"Error fetching story: {e}")
            return None
    
    async def create_pick(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": "mock-pick-id"}
        mutation = """
        mutation CreatePick($data: PickCreateInput!) {
            createPick(data: $data) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"data": input_data})
            return result.get("data", {}).get("createPick")
        except Exception as e:
            print(f"Error creating pick: {e}")
            return None
    
    async def create_comment(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": "mock-comment-id"}
        mutation = """
        mutation CreateComment($data: CommentCreateInput!) {
            createComment(data: $data) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"data": input_data})
            return result.get("data", {}).get("createComment")
        except Exception as e:
            print(f"Error creating comment: {e}")
            return None
    
    async def like_pick(self, pick_id: str, member_id: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": pick_id, "likeCount": 1}
        mutation = """
        mutation LikePick($pickId: ID!, $memberId: ID!) {
            likePick(pickId: $pickId, memberId: $memberId) { id likeCount }
        }
        """
        try:
            result = await self.mutation(mutation, {"pickId": pick_id, "memberId": member_id})
            return result.get("data", {}).get("likePick")
        except Exception as e:
            print(f"Error liking pick: {e}")
            return None
    
    async def like_comment(self, comment_id: str, member_id: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": comment_id, "likeCount": 1}
        mutation = """
        mutation LikeComment($commentId: ID!, $memberId: ID!) {
            likeComment(commentId: $commentId, memberId: $memberId) { id likeCount }
        }
        """
        try:
            result = await self.mutation(mutation, {"commentId": comment_id, "memberId": member_id})
            return result.get("data", {}).get("likeComment")
        except Exception as e:
            print(f"Error liking comment: {e}")
            return None
    
    async def follow_member(self, follower_id: str, following_id: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": f"{follower_id}->{following_id}"}
        mutation = """
        mutation FollowMember($followerId: ID!, $followingId: ID!) {
            followMember(followerId: $followerId, followingId: $followingId) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"followerId": follower_id, "followingId": following_id})
            return result.get("data", {}).get("followMember")
        except Exception as e:
            print(f"Error following member: {e}")
            return None
    
    async def create_activity(self, activity_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """建立活動記錄"""
        mutation = """
        mutation CreateActivity($input: ActivityInput!) {
            createActivity(input: $input) {
                id
                type
                actorId
                objectId
                createdAt
            }
        }
        """
        
        try:
            result = await self.mutation(mutation, {"input": activity_data})
            return result.get("data", {}).get("createActivity")
        except Exception as e:
            print(f"Error creating activity: {e}")
            return None
