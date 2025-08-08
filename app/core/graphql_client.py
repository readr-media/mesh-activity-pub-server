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

    async def get_actor_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {
                "id": "mock-actor-id",
                "username": username,
                "domain": settings.ACTIVITYPUB_DOMAIN,
                "display_name": username,
                "is_local": True,
            }
        query = """
        query GetAPActor($username: String!) {
          ActivityPubActors(where: { username: { equals: $username } }, take: 1) {
            id username domain display_name summary icon_url inbox_url outbox_url followers_url following_url public_key_pem private_key_pem is_local
          }
        }
        """
        try:
            result = await self.query(query, {"username": username})
            items = result.get("data", {}).get("ActivityPubActors", [])
            return items[0] if items else None
        except Exception as e:
            print(f"Error fetching actor: {e}")
            return None

    async def create_actor(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": "mock-actor-id"}
        mutation = """
        mutation CreateAPActor($data: ActivityPubActorCreateInput!) {
          createActivityPubActor(data: $data) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"data": data})
            return result.get("data", {}).get("createActivityPubActor")
        except Exception as e:
            print(f"Error creating actor: {e}")
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
        """依 Keystone 6 的 createPick(data: PickCreateInput!) 格式組裝資料

        期望的 input_data 形狀（呼叫端傳入簡化鍵）：
        {
          "storyId": ID,
          "memberId": ID,
          "objective": str | None,
          "kind": str,
          "paywall": bool,
          "pickedDate": ISO8601 | None
        }
        轉換為 Keystone 的 data：
        {
          story: { connect: { id } },
          member: { connect: { id } },
          objective, kind, paywall, picked_date
        }
        """
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": "mock-pick-id"}
        data: Dict[str, Any] = {}
        if input_data.get("storyId"):
            data["story"] = {"connect": {"id": input_data["storyId"]}}
        if input_data.get("memberId"):
            data["member"] = {"connect": {"id": input_data["memberId"]}}
        if input_data.get("objective") is not None:
            data["objective"] = input_data["objective"]
        if input_data.get("kind") is not None:
            data["kind"] = input_data["kind"]
        if input_data.get("paywall") is not None:
            data["paywall"] = input_data["paywall"]
        if input_data.get("pickedDate") is not None:
            data["picked_date"] = input_data["pickedDate"]

        mutation = """
        mutation CreatePick($data: PickCreateInput!) {
            createPick(data: $data) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"data": data})
            return result.get("data", {}).get("createPick")
        except Exception as e:
            print(f"Error creating pick: {e}")
            return None
    
    async def create_comment(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """將簡化鍵轉為 Keystone 關聯輸入

        期望 input_data：
        { content, publishedDate?, memberId, pickId?, parentId?, storyId? }
        轉為：
        { content, published_date?, member: {connect:{id}}, pick/story/parent: {connect:{id}} }
        """
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": "mock-comment-id"}
        data: Dict[str, Any] = {}
        if input_data.get("content") is not None:
            data["content"] = input_data["content"]
        if input_data.get("publishedDate") is not None:
            data["published_date"] = input_data["publishedDate"]
        if input_data.get("memberId"):
            data["member"] = {"connect": {"id": input_data["memberId"]}}
        if input_data.get("pickId"):
            data["pick"] = {"connect": {"id": input_data["pickId"]}}
        if input_data.get("parentId"):
            data["parent"] = {"connect": {"id": input_data["parentId"]}}
        if input_data.get("storyId"):
            data["story"] = {"connect": {"id": input_data["storyId"]}}

        mutation = """
        mutation CreateComment($data: CommentCreateInput!) {
            createComment(data: $data) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"data": data})
            return result.get("data", {}).get("createComment")
        except Exception as e:
            print(f"Error creating comment: {e}")
            return None
    
    async def like_pick(self, pick_id: str, member_id: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": pick_id, "likeCount": 1}
        # 需在 Keystone 的 Pick 加上 like: relationship({ ref: 'Member.pick_like', many: true })
        mutation = """
        mutation LikePick($id: ID!, $memberId: ID!) {
          updatePick(where: { id: $id }, data: { like: { connect: { id: $memberId } } }) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"id": pick_id, "memberId": member_id})
            data = result.get("data", {}).get("updatePick")
            if data:
                return {"id": data.get("id"), "likeCount": 0}
            return None
        except Exception as e:
            print(f"Error liking pick: {e}")
            return None
    
    async def like_comment(self, comment_id: str, member_id: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": comment_id, "likeCount": 1}
        mutation = """
        mutation LikeComment($id: ID!, $memberId: ID!) {
            updateComment(where: { id: $id }, data: { like: { connect: { id: $memberId } } }) {
                id
            }
        }
        """
        try:
            result = await self.mutation(mutation, {"id": comment_id, "memberId": member_id})
            data = result.get("data", {}).get("updateComment")
            if data:
                return {"id": data.get("id"), "likeCount": 0}
            return None
        except Exception as e:
            print(f"Error liking comment: {e}")
            return None
    
    async def follow_member(self, follower_id: str, following_id: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": f"{follower_id}->{following_id}"}
        mutation = """
        mutation FollowMember($followerId: ID!, $followingId: ID!) {
            updateMember(
              where: { id: $followerId },
              data: { following: { connect: { id: $followingId } } }
            ) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"followerId": follower_id, "followingId": following_id})
            return result.get("data", {}).get("updateMember")
        except Exception as e:
            print(f"Error following member: {e}")
            return None

    async def get_member_picks(self, member_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return []
        query = """
        query MemberPicks($memberId: ID!, $take: Int!, $skip: Int!) {
          Picks(
            where: { member: { id: { equals: $memberId } } },
            take: $take,
            skip: $skip,
            orderBy: { picked_date: desc }
          ) {
            id
            objective
            kind
            picked_date
            story { id title url }
          }
        }
        """
        try:
            result = await self.query(query, {"memberId": member_id, "take": limit, "skip": offset})
            return result.get("data", {}).get("Picks", [])
        except Exception as e:
            print(f"Error fetching member picks: {e}")
            return []

    async def get_pick_comments(self, pick_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return []
        query = """
        query PickComments($pickId: ID!, $take: Int!, $skip: Int!) {
          Comments(
            where: { pick: { id: { equals: $pickId } } },
            take: $take,
            skip: $skip,
            orderBy: { published_date: desc }
          ) {
            id
            content
            published_date
            member { id }
            parent { id content }
          }
        }
        """
        try:
            result = await self.query(query, {"pickId": pick_id, "take": limit, "skip": offset})
            return result.get("data", {}).get("Comments", [])
        except Exception as e:
            print(f"Error fetching pick comments: {e}")
            return []

    async def update_member_activitypub_settings(
        self,
        member_id: str,
        activitypub_enabled: bool,
        activitypub_auto_follow: Optional[bool] = None,
        activitypub_public_posts: Optional[bool] = None,
        activitypub_federation_enabled: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {
                "id": member_id,
                "activitypub_enabled": activitypub_enabled,
                "activitypub_auto_follow": activitypub_auto_follow if activitypub_auto_follow is not None else True,
                "activitypub_public_posts": activitypub_public_posts if activitypub_public_posts is not None else True,
                "activitypub_federation_enabled": activitypub_federation_enabled if activitypub_federation_enabled is not None else True,
            }
        fields: Dict[str, Any] = {"activitypub_enabled": activitypub_enabled}
        if activitypub_auto_follow is not None:
            fields["activitypub_auto_follow"] = activitypub_auto_follow
        if activitypub_public_posts is not None:
            fields["activitypub_public_posts"] = activitypub_public_posts
        if activitypub_federation_enabled is not None:
            fields["activitypub_federation_enabled"] = activitypub_federation_enabled
        mutation = """
        mutation UpdateMemberAP($id: ID!, $data: MemberUpdateInput!) {
          updateMember(where: { id: $id }, data: $data) {
            id
            activitypub_enabled
            activitypub_auto_follow
            activitypub_public_posts
            activitypub_federation_enabled
          }
        }
        """
        try:
            result = await self.mutation(mutation, {"id": member_id, "data": fields})
            return result.get("data", {}).get("updateMember")
        except Exception as e:
            print(f"Error updating member settings: {e}")
            return None

    async def add_comment_to_pick(self, pick_id: str, comment_id: str) -> bool:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return True
        # Keystone pick.ts: pick_comment: relationship({ ref: 'Comment', many: true })
        mutation = """
        mutation AddCommentToPick($pickId: ID!, $commentId: ID!) {
          updatePick(where: { id: $pickId }, data: { pick_comment: { connect: { id: $commentId } } }) {
            id
          }
        }
        """
        try:
            result = await self.mutation(mutation, {"pickId": pick_id, "commentId": comment_id})
            return bool(result.get("data", {}).get("updatePick"))
        except Exception as e:
            print(f"Error linking comment to pick: {e}")
            return False
    
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
