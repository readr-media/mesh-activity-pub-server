import httpx
from typing import Dict, Any, Optional, List
from app.core.config import settings

class GraphQLClient:
    """GraphQL client"""
    # 共享 httpx AsyncClient（由應用啟動時注入）
    shared_client: Optional[httpx.AsyncClient] = None
    
    @classmethod
    def set_shared_client(cls, client: Optional[httpx.AsyncClient]) -> None:
        cls.shared_client = client
    
    def __init__(self, endpoint: Optional[str] = None, token: Optional[str] = None, client: Optional[httpx.AsyncClient] = None):
        self.endpoint = endpoint or settings.GRAPHQL_ENDPOINT
        self.token = token or settings.GRAPHQL_TOKEN
        # 優先採用注入 client；否則採用 shared_client；最後回退到本地臨時 client
        self.client = client or GraphQLClient.shared_client
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
    
    async def query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"data": {"mock": True}}
        payload = {"query": query, "variables": variables or {}}
        # 優先使用注入或共享 client，否則回退到臨時 client
        client: Optional[httpx.AsyncClient] = self.client
        if client is not None:
            response = await client.post(self.endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        # 回退：與舊邏輯相容
        async with httpx.AsyncClient() as temp_client:
            response = await temp_client.post(self.endpoint, json=payload, headers=self.headers, timeout=30.0)
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

    async def get_story_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": "mock-story-id", "url": url}
        query = """
        query GetStoryByUrl($url: String!) {
          Stories(where: { url: { equals: $url } }, take: 1) { id title url image published_date state is_active }
        }
        """
        try:
            result = await self.query(query, {"url": url})
            items = result.get("data", {}).get("Stories", [])
            return items[0] if items else None
        except Exception as e:
            print(f"Error fetching story by url: {e}")
            return None

    async def create_story(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": "mock-story-id"}
        mutation = """
        mutation CreateStory($data: StoryCreateInput!) {
          createStory(data: $data) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"data": data})
            return result.get("data", {}).get("createStory")
        except Exception as e:
            print(f"Error creating story: {e}")
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

    # Federation GraphQL APIs
    async def list_federation_instances(self, limit: int = 100, offset: int = 0, approved_only: bool = False, active_only: bool = True) -> List[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return []
        where: Dict[str, Any] = {}
        if approved_only:
            where.setdefault("is_approved", {"equals": True})
        if active_only:
            where.setdefault("is_active", {"equals": True})
        query = """
        query ListInstances($take: Int!, $skip: Int!, $where: FederationInstanceWhereInput) {
          FederationInstances(take: $take, skip: $skip, where: $where, orderBy: { last_seen: desc }) {
            id domain name description software version is_active is_approved is_blocked
            last_seen last_successful_connection user_count post_count connection_count error_count
            auto_follow auto_announce max_followers max_following
          }
        }
        """
        try:
            result = await self.query(query, {"take": limit, "skip": offset, "where": where or None})
            return result.get("data", {}).get("FederationInstances", [])
        except Exception as e:
            print(f"Error listing instances: {e}")
            return []

    async def get_federation_instance(self, domain: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return None
        query = """
        query GetInstance($domain: String!) {
          FederationInstances(where: { domain: { equals: $domain } }, take: 1) {
            id domain name description software version is_active is_approved is_blocked
            last_seen last_successful_connection user_count post_count connection_count error_count
            auto_follow auto_announce max_followers max_following
          }
        }
        """
        try:
            result = await self.query(query, {"domain": domain})
            items = result.get("data", {}).get("FederationInstances", [])
            return items[0] if items else None
        except Exception as e:
            print(f"Error getting instance: {e}")
            return None

    async def create_federation_instance(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": "mock-instance-id"}
        mutation = """
        mutation CreateInstance($data: FederationInstanceCreateInput!) {
          createFederationInstance(data: $data) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"data": data})
            return result.get("data", {}).get("createFederationInstance")
        except Exception as e:
            print(f"Error creating instance: {e}")
            return None

    async def update_federation_instance(self, id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": id}
        mutation = """
        mutation UpdateInstance($id: ID!, $data: FederationInstanceUpdateInput!) {
          updateFederationInstance(where: { id: $id }, data: $data) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"id": id, "data": data})
            return result.get("data", {}).get("updateFederationInstance")
        except Exception as e:
            print(f"Error updating instance: {e}")
            return None

    async def delete_federation_instance(self, id: str) -> bool:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return True
        mutation = """
        mutation DeleteInstance($id: ID!) {
          deleteFederationInstance(where: { id: $id }) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"id": id})
            return bool(result.get("data", {}).get("deleteFederationInstance"))
        except Exception as e:
            print(f"Error deleting instance: {e}")
            return False

    async def update_federation_instance_by_domain(self, domain: str, data: Dict[str, Any]) -> bool:
        instance = await self.get_federation_instance(domain)
        if not instance:
            return False
        return bool(await self.update_federation_instance(instance.get("id"), data))

    async def delete_federation_instance_by_domain(self, domain: str) -> bool:
        instance = await self.get_federation_instance(domain)
        if not instance:
            return False
        return await self.delete_federation_instance(instance.get("id"))
    
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
        """在 Keystone 的 Activity list 建立記錄"""
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": activity_data.get("activity_id", "mock-activity-id")}
        mutation = """
        mutation CreateActivity($data: ActivityCreateInput!) {
          createActivity(data: $data) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"data": activity_data})
            return result.get("data", {}).get("createActivity")
        except Exception as e:
            print(f"Error creating activity: {e}")
            return None
    
    async def get_activity_by_activity_id(self, activity_id: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return None
        query = """
        query GetActivity($id: String!) {
          Activities(where: { activity_id: { equals: $id } }, take: 1) { id activity_id }
        }
        """
        try:
            result = await self.query(query, {"id": activity_id})
            items = result.get("data", {}).get("Activities", [])
            return items[0] if items else None
        except Exception as e:
            print(f"Error fetching activity by activity_id: {e}")
            return None

    # --- Account Discovery / Mapping / SyncTask ---
    async def create_account_discovery(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {
                "id": "mock-discovery-id",
                **data,
                "confidence_score": data.get("confidence_score", 0.8),
            }
        mutation = """
        mutation CreateAccountDiscovery($data: AccountDiscoveryCreateInput!) {
          createAccountDiscovery(data: $data) {
            id
            discovery_method
            search_query
            discovered_actor_id
            discovered_username
            discovered_domain
            is_successful
            confidence_score
            match_reason
            created_at
            }
        }
        """
        try:
            result = await self.mutation(mutation, {"data": data})
            return result.get("data", {}).get("createAccountDiscovery")
        except Exception as e:
            print(f"Error creating account discovery: {e}")
            return None

    async def list_account_discoveries(self, member_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return []
        query = """
        query ListAccountDiscoveries($memberId: ID!, $take: Int!, $skip: Int!) {
          AccountDiscoveries(
            where: { mesh_member: { id: { equals: $memberId } } },
            take: $take,
            skip: $skip,
            orderBy: { created_at: desc }
          ) {
            id discovery_method search_query discovered_actor_id discovered_username discovered_domain is_successful confidence_score match_reason created_at
            }
        }
        """
        try:
            result = await self.query(query, {"memberId": member_id, "take": limit, "skip": offset})
            return result.get("data", {}).get("AccountDiscoveries", [])
        except Exception as e:
            print(f"Error listing account discoveries: {e}")
            return []
    
    async def get_account_mapping_by_member_and_remote_actor(self, member_id: str, remote_actor_id: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return None
        query = """
        query GetMapping($memberId: ID!, $remoteActor: String!) {
          AccountMappings(
            where: {
              AND: [
                { mesh_member: { id: { equals: $memberId } } },
                { remote_actor_id: { equals: $remoteActor } }
              ]
            },
            take: 1
          ) {
            id mesh_member { id } remote_actor_id remote_username remote_domain remote_display_name remote_avatar_url remote_summary is_verified verification_method verification_date sync_enabled sync_posts sync_follows sync_likes sync_announces last_sync_at sync_error_count remote_follower_count remote_following_count remote_post_count created_at updated_at
            }
        }
        """
        try:
            result = await self.query(query, {"memberId": member_id, "remoteActor": remote_actor_id})
            items = result.get("data", {}).get("AccountMappings", [])
            return items[0] if items else None
        except Exception as e:
            print(f"Error getting account mapping by member and remote actor: {e}")
            return None
    
    async def create_account_mapping(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": "mock-mapping-id", **data}
        mutation = """
        mutation CreateAccountMapping($data: AccountMappingCreateInput!) {
          createAccountMapping(data: $data) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"data": data})
            return result.get("data", {}).get("createAccountMapping")
        except Exception as e:
            print(f"Error creating account mapping: {e}")
            return None
    
    async def get_account_mappings(self, member_id: str) -> List[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return []
        query = """
        query GetAccountMappings($memberId: ID!) {
          AccountMappings(where: { mesh_member: { id: { equals: $memberId } } }, orderBy: { created_at: desc }) {
            id mesh_member { id } remote_actor_id remote_username remote_domain remote_display_name remote_avatar_url remote_summary is_verified verification_method verification_date sync_enabled sync_posts sync_follows sync_likes sync_announces last_sync_at sync_error_count remote_follower_count remote_following_count remote_post_count created_at updated_at
            }
        }
        """
        try:
            result = await self.query(query, {"memberId": member_id})
            return result.get("data", {}).get("AccountMappings", [])
        except Exception as e:
            print(f"Error fetching account mappings: {e}")
            return []
    
    async def get_account_mapping_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": id, "mesh_member": {"id": "mock-member"}}
        query = """
        query GetAccountMapping($id: ID!) {
          AccountMapping(where: { id: $id }) {
            id mesh_member { id } remote_actor_id remote_username remote_domain remote_display_name remote_avatar_url remote_summary is_verified verification_method verification_date sync_enabled sync_posts sync_follows sync_likes sync_announces last_sync_at sync_error_count remote_follower_count remote_following_count remote_post_count created_at updated_at
            }
        }
        """
        try:
            result = await self.query(query, {"id": id})
            return result.get("data", {}).get("AccountMapping")
        except Exception as e:
            print(f"Error getting account mapping: {e}")
            return None
    
    async def update_account_mapping(self, id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": id, **data}
        mutation = """
        mutation UpdateAccountMapping($id: ID!, $data: AccountMappingUpdateInput!) {
          updateAccountMapping(where: { id: $id }, data: $data) {
            id
            }
        }
        """
        try:
            result = await self.mutation(mutation, {"id": id, "data": data})
            return result.get("data", {}).get("updateAccountMapping")
        except Exception as e:
            print(f"Error updating account mapping: {e}")
            return None
    
    async def delete_account_mapping(self, id: str) -> bool:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return True
        mutation = """
        mutation DeleteAccountMapping($id: ID!) {
          deleteAccountMapping(where: { id: $id }) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"id": id})
            return bool(result.get("data", {}).get("deleteAccountMapping"))
        except Exception as e:
            print(f"Error deleting account mapping: {e}")
            return False

    async def create_account_sync_task(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": "mock-sync-task-id", **data, "status": data.get("status", "pending"), "progress": 0}
        mutation = """
        mutation CreateAccountSyncTask($data: AccountSyncTaskCreateInput!) {
          createAccountSyncTask(data: $data) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"data": data})
            return result.get("data", {}).get("createAccountSyncTask")
        except Exception as e:
            print(f"Error creating sync task: {e}")
            return None
    
    async def update_account_sync_task(self, id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": id, **data}
        mutation = """
        mutation UpdateAccountSyncTask($id: ID!, $data: AccountSyncTaskUpdateInput!) {
          updateAccountSyncTask(where: { id: $id }, data: $data) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"id": id, "data": data})
            return result.get("data", {}).get("updateAccountSyncTask")
        except Exception as e:
            print(f"Error updating sync task: {e}")
            return None

    async def list_account_sync_tasks(self, mapping_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return []
        query = """
        query ListSyncTasks($mappingId: ID!, $take: Int!, $skip: Int!) {
          AccountSyncTasks(
            where: { mapping: { id: { equals: $mappingId } } },
            take: $take,
            skip: $skip,
            orderBy: { created_at: desc }
          ) {
            id sync_type status progress items_processed items_synced items_failed created_at started_at completed_at error_message retry_count
            }
        }
        """
        try:
            result = await self.query(query, {"mappingId": mapping_id, "take": limit, "skip": offset})
            return result.get("data", {}).get("AccountSyncTasks", [])
        except Exception as e:
            print(f"Error listing sync tasks: {e}")
            return []

    async def get_account_sync_task(self, id: str) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": id, "status": "pending", "progress": 0}
        query = """
        query GetSyncTask($id: ID!) {
          AccountSyncTask(where: { id: $id }) {
            id sync_type status progress items_processed items_synced items_failed created_at started_at completed_at error_message retry_count mapping { id }
          }
        }
        """
        try:
            result = await self.query(query, {"id": id})
            return result.get("data", {}).get("AccountSyncTask")
        except Exception as e:
            print(f"Error getting sync task: {e}")
            return None
    
    async def create_inbox_item(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": data.get("activity_id", "mock-inbox-id")}
        mutation = """
        mutation CreateInbox($data: InboxItemCreateInput!) {
          createInboxItem(data: $data) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"data": data})
            return result.get("data", {}).get("createInboxItem")
        except Exception as e:
            print(f"Error creating inbox item: {e}")
            return None
    
    async def update_inbox_item_processed(self, id: str, is_processed: bool) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": id, "is_processed": is_processed}
        mutation = """
        mutation UpdateInbox($id: ID!, $data: InboxItemUpdateInput!) {
          updateInboxItem(where: { id: $id }, data: $data) { id is_processed }
        }
        """
        try:
            result = await self.mutation(mutation, {"id": id, "data": {"is_processed": is_processed}})
            return result.get("data", {}).get("updateInboxItem")
        except Exception as e:
            print(f"Error updating inbox item: {e}")
            return None
    
    async def create_outbox_item(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if getattr(settings, "GRAPHQL_MOCK", False):
            return {"id": data.get("activity_id", "mock-outbox-id")}
        mutation = """
        mutation CreateOutbox($data: OutboxItemCreateInput!) {
          createOutboxItem(data: $data) { id }
        }
        """
        try:
            result = await self.mutation(mutation, {"data": data})
            return result.get("data", {}).get("createOutboxItem")
        except Exception as e:
            print(f"Error creating outbox item: {e}")
            return None
