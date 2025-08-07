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
        """Execute GraphQL query"""
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.endpoint,
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            return response.json()
    
    async def mutation(self, mutation: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute GraphQL mutation"""
        return await self.query(mutation, variables)
    
    async def get_member(self, member_id: str) -> Optional[Dict[str, Any]]:
        """Get Member information"""
        query = """
        query GetMember($id: ID!) {
            member(id: $id) {
                id
                name
                nickname
                email
                avatar
                intro
                is_active
                verified
                language
                createdAt
                updatedAt
                followerCount
                followingCount
                pickCount
                commentCount
                activitypub_enabled
                activitypub_auto_follow
                activitypub_public_posts
                activitypub_federation_enabled
                createdBy {
                    id
                    name
                    username
                }
            }
        }
        """
        
        try:
            result = await self.query(query, {"id": member_id})
            return result.get("data", {}).get("member")
        except Exception as e:
            print(f"Error fetching member: {e}")
            return None
    
    async def get_member_by_custom_id(self, custom_id: str) -> Optional[Dict[str, Any]]:
        """Get Member information by customId"""
        query = """
        query GetMemberByCustomId($customId: String!) {
            member(where: { customId: $customId }) {
                id
                name
                nickname
                email
                avatar
                intro
                is_active
                verified
                language
                createdAt
                updatedAt
                followerCount
                followingCount
                pickCount
                commentCount
                activitypub_enabled
                activitypub_auto_follow
                activitypub_public_posts
                activitypub_federation_enabled
                createdBy {
                    id
                    name
                    username
                }
            }
        }
        """
        
        try:
            result = await self.query(query, {"customId": custom_id})
            return result.get("data", {}).get("member")
        except Exception as e:
            print(f"Error fetching member by customId: {e}")
            return None
    
    async def update_member_activitypub_settings(
        self, 
        member_id: str, 
        activitypub_enabled: bool,
        activitypub_auto_follow: Optional[bool] = None,
        activitypub_public_posts: Optional[bool] = None,
        activitypub_federation_enabled: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Update Member's ActivityPub settings"""
        mutation = """
        mutation UpdateMemberActivityPubSettings(
            $memberId: ID!
            $activitypubEnabled: Boolean!
            $activitypubAutoFollow: Boolean
            $activitypubPublicPosts: Boolean
            $activitypubFederationEnabled: Boolean
        ) {
            updateMemberActivityPubSettings(
                memberId: $memberId
                activitypubEnabled: $activitypubEnabled
                activitypubAutoFollow: $activitypubAutoFollow
                activitypubPublicPosts: $activitypubPublicPosts
                activitypubFederationEnabled: $activitypubFederationEnabled
            ) {
                id
                activitypub_enabled
                activitypub_auto_follow
                activitypub_public_posts
                activitypub_federation_enabled
            }
        }
        """
        
        variables = {
            "memberId": member_id,
            "activitypubEnabled": activitypub_enabled
        }
        
        if activitypub_auto_follow is not None:
            variables["activitypubAutoFollow"] = activitypub_auto_follow
        if activitypub_public_posts is not None:
            variables["activitypubPublicPosts"] = activitypub_public_posts
        if activitypub_federation_enabled is not None:
            variables["activitypubFederationEnabled"] = activitypub_federation_enabled
        
        try:
            result = await self.mutation(mutation, variables)
            return result.get("data", {}).get("updateMemberActivityPubSettings")
        except Exception as e:
            print(f"Error updating member ActivityPub settings: {e}")
            return None
    
    async def get_member_picks(self, member_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """取得 Member 的 Picks"""
        query = """
        query GetMemberPicks($memberId: ID!, $limit: Int!, $offset: Int!) {
            member(id: $memberId) {
                pick(take: $limit, skip: $offset) {
                    id
                    kind
                    objective
                    paywall
                    picked_date
                    state
                    is_active
                    story {
                        id
                        title
                        content
                        url
                        image
                        published_date
                    }
                    pick_commentCount
                }
            }
        }
        """
        
        try:
            result = await self.query(query, {
                "memberId": member_id,
                "limit": limit,
                "offset": offset
            })
            return result.get("data", {}).get("member", {}).get("pick", [])
        except Exception as e:
            print(f"Error fetching member picks: {e}")
            return []
    
    async def get_member_comments(self, member_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """取得 Member 的 Comments"""
        query = """
        query GetMemberComments($memberId: ID!, $limit: Int!, $offset: Int!) {
            member(id: $memberId) {
                comment(take: $limit, skip: $offset) {
                    id
                    content
                    createdAt
                    published_date
                    is_active
                    is_edited
                    state
                    parent {
                        id
                        content
                    }
                    story {
                        id
                        title
                    }
                    pick {
                        id
                        objective
                    }
                    likeCount
                }
            }
        }
        """
        
        try:
            result = await self.query(query, {
                "memberId": member_id,
                "limit": limit,
                "offset": offset
            })
            return result.get("data", {}).get("member", {}).get("comment", [])
        except Exception as e:
            print(f"Error fetching member comments: {e}")
            return []
    
    async def get_member_followers(self, member_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """取得 Member 的追蹤者"""
        query = """
        query GetMemberFollowers($memberId: ID!, $limit: Int!, $offset: Int!) {
            member(id: $memberId) {
                follower(take: $limit, skip: $offset) {
                    id
                    name
                    nickname
                    avatar
                    intro
                    is_active
                    verified
                    followerCount
                    followingCount
                }
            }
        }
        """
        
        try:
            result = await self.query(query, {
                "memberId": member_id,
                "limit": limit,
                "offset": offset
            })
            return result.get("data", {}).get("member", {}).get("follower", [])
        except Exception as e:
            print(f"Error fetching member followers: {e}")
            return []
    
    async def get_member_following(self, member_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """取得 Member 追蹤中的使用者"""
        query = """
        query GetMemberFollowing($memberId: ID!, $limit: Int!, $offset: Int!) {
            member(id: $memberId) {
                following(take: $limit, skip: $offset) {
                    id
                    name
                    nickname
                    avatar
                    intro
                    is_active
                    verified
                    followerCount
                    followingCount
                }
            }
        }
        """
        
        try:
            result = await self.query(query, {
                "memberId": member_id,
                "limit": limit,
                "offset": offset
            })
            return result.get("data", {}).get("member", {}).get("following", [])
        except Exception as e:
            print(f"Error fetching member following: {e}")
            return []
    
    async def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        """取得 Mesh Story 資訊"""
        query = """
        query GetStory($id: ID!) {
            story(id: $id) {
                id
                title
                content
                url
                image
                published_date
                state
                is_active
                createdBy {
                    id
                    name
                    username
                }
            }
        }
        """
        
        try:
            result = await self.query(query, {"id": story_id})
            return result.get("data", {}).get("story")
        except Exception as e:
            print(f"Error fetching story: {e}")
            return None
    
    async def get_pick(self, pick_id: str) -> Optional[Dict[str, Any]]:
        """取得 Mesh Pick 資訊"""
        query = """
        query GetPick($id: ID!) {
            pick(id: $id) {
                id
                kind
                objective
                paywall
                picked_date
                state
                is_active
                member {
                    id
                    name
                    nickname
                    avatar
                }
                story {
                    id
                    title
                    content
                    url
                    image
                    published_date
                }
                pick_commentCount
            }
        }
        """
        
        try:
            result = await self.query(query, {"id": pick_id})
            return result.get("data", {}).get("pick")
        except Exception as e:
            print(f"Error fetching pick: {e}")
            return None
    
    async def get_comment(self, comment_id: str) -> Optional[Dict[str, Any]]:
        """取得 Mesh Comment 資訊"""
        query = """
        query GetComment($id: ID!) {
            comment(id: $id) {
                id
                content
                createdAt
                published_date
                is_active
                is_edited
                state
                member {
                    id
                    name
                    nickname
                    avatar
                }
                parent {
                    id
                    content
                }
                story {
                    id
                    title
                }
                pick {
                    id
                    objective
                }
                likeCount
            }
        }
        """
        
        try:
            result = await self.query(query, {"id": comment_id})
            return result.get("data", {}).get("comment")
        except Exception as e:
            print(f"Error fetching comment: {e}")
            return None
    
    async def get_pick_comments(self, pick_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """取得 Pick 的評論列表"""
        query = """
        query GetPickComments($pickId: ID!, $limit: Int!, $offset: Int!) {
            pick(id: $pickId) {
                pick_comment(take: $limit, skip: $offset) {
                    id
                    content
                    createdAt
                    published_date
                    is_active
                    member {
                        id
                        name
                        nickname
                        avatar
                    }
                    parent {
                        id
                        content
                    }
                    likeCount
                }
            }
        }
        """
        
        try:
            result = await self.query(query, {
                "pickId": pick_id,
                "limit": limit,
                "offset": offset
            })
            return result.get("data", {}).get("pick", {}).get("pick_comment", [])
        except Exception as e:
            print(f"Error fetching pick comments: {e}")
            return []
    
    async def create_pick(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """建立新的 Pick"""
        mutation = """
        mutation CreatePick($input: PickCreateInput!) {
            createPick(input: $input) {
                id
                kind
                objective
                picked_date
                member {
                    id
                    name
                    nickname
                }
                story {
                    id
                    title
                    url
                }
            }
        }
        """
        
        try:
            result = await self.mutation(mutation, {"input": input_data})
            return result.get("data", {}).get("createPick")
        except Exception as e:
            print(f"Error creating pick: {e}")
            return None
    
    async def create_comment(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """建立新的 Comment"""
        mutation = """
        mutation CreateComment($input: CommentCreateInput!) {
            createComment(input: $input) {
                id
                content
                createdAt
                published_date
                member {
                    id
                    name
                    nickname
                }
                parent {
                    id
                }
                story {
                    id
                    title
                }
                pick {
                    id
                    objective
                }
            }
        }
        """
        
        try:
            result = await self.mutation(mutation, {"input": input_data})
            return result.get("data", {}).get("createComment")
        except Exception as e:
            print(f"Error creating comment: {e}")
            return None
    
    async def like_pick(self, pick_id: str, member_id: str) -> Optional[Dict[str, Any]]:
        """對 Pick 按讚"""
        mutation = """
        mutation LikePick($pickId: ID!, $memberId: ID!) {
            likePick(pickId: $pickId, memberId: $memberId) {
                id
                likeCount
            }
        }
        """
        
        try:
            result = await self.mutation(mutation, {
                "pickId": pick_id,
                "memberId": member_id
            })
            return result.get("data", {}).get("likePick")
        except Exception as e:
            print(f"Error liking pick: {e}")
            return None
    
    async def like_comment(self, comment_id: str, member_id: str) -> Optional[Dict[str, Any]]:
        """對 Comment 按讚"""
        mutation = """
        mutation LikeComment($commentId: ID!, $memberId: ID!) {
            likeComment(commentId: $commentId, memberId: $memberId) {
                id
                likeCount
            }
        }
        """
        
        try:
            result = await self.mutation(mutation, {
                "commentId": comment_id,
                "memberId": member_id
            })
            return result.get("data", {}).get("likeComment")
        except Exception as e:
            print(f"Error liking comment: {e}")
            return None
    
    async def follow_member(self, follower_id: str, following_id: str) -> Optional[Dict[str, Any]]:
        """追蹤 Member"""
        mutation = """
        mutation FollowMember($followerId: ID!, $followingId: ID!) {
            followMember(followerId: $followerId, followingId: $followingId) {
                id
                followerCount
                followingCount
            }
        }
        """
        
        try:
            result = await self.mutation(mutation, {
                "followerId": follower_id,
                "followingId": following_id
            })
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
