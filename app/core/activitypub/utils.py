import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from app.core.config import settings
from app.models.activitypub import Actor

def generate_actor_id(username: str) -> str:
    """生成 Actor ID"""
    return f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{username}"

def generate_activity_id(activity_type: str, username: str) -> str:
    """生成 Activity ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/activities/{activity_type}/{username}/{timestamp}-{unique_id}"

def generate_note_id(username: str) -> str:
    """生成 Note ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/notes/{username}/{timestamp}-{unique_id}"

def create_actor_object(actor: Actor) -> Dict[str, Any]:
    """建立 Actor 物件"""
    actor_id = generate_actor_id(actor.username)
    
    return {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            "https://w3id.org/security/v1"
        ],
        "id": actor_id,
        "type": "Person",
        "preferredUsername": actor.username,
        "name": actor.display_name or actor.username,
        "summary": actor.summary or "",
        "icon": {
            "type": "Image",
            "url": actor.icon_url or f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/default-avatar.png"
        },
        "inbox": f"{actor_id}/inbox",
        "outbox": f"{actor_id}/outbox",
        "followers": f"{actor_id}/followers",
        "following": f"{actor_id}/following",
        "publicKey": {
            "id": f"{actor_id}#main-key",
            "owner": actor_id,
            "publicKeyPem": actor.public_key_pem
        }
    }

def generate_key_pair() -> tuple[str, str]:
    """生成 RSA 金鑰對"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    public_key = private_key.public_key()
    
    # 序列化公鑰
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    # 序列化私鑰
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    return public_pem, private_pem

def create_activity_object(
    activity_type: str,
    actor: Actor,
    object_data: Dict[str, Any],
    target_data: Optional[Dict[str, Any]] = None,
    to: Optional[list] = None,
    cc: Optional[list] = None
) -> Dict[str, Any]:
    """建立 Activity 物件"""
    activity_id = generate_activity_id(activity_type, actor.username)
    actor_id = generate_actor_id(actor.username)
    
    activity = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": activity_id,
        "type": activity_type,
        "actor": actor_id,
        "object": object_data,
        "published": datetime.utcnow().isoformat() + "Z"
    }
    
    if target_data:
        activity["target"] = target_data
    
    if to:
        activity["to"] = to
    
    if cc:
        activity["cc"] = cc
    
    return activity

def create_note_object(
    actor: Actor,
    content: str,
    content_type: str = "text/html",
    summary: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    to: Optional[list] = None,
    cc: Optional[list] = None,
    attachment: Optional[list] = None,
    tags: Optional[list] = None
) -> Dict[str, Any]:
    """建立 Note 物件"""
    note_id = generate_note_id(actor.username)
    actor_id = generate_actor_id(actor.username)
    
    note = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": note_id,
        "type": "Note",
        "attributedTo": actor_id,
        "content": content,
        "contentType": content_type,
        "published": datetime.utcnow().isoformat() + "Z"
    }
    
    if summary:
        note["summary"] = summary
    
    if in_reply_to:
        note["inReplyTo"] = in_reply_to
    
    if to:
        note["to"] = to
    
    if cc:
        note["cc"] = cc
    
    if attachment:
        note["attachment"] = attachment
    
    if tags:
        note["tag"] = tags
    
    return note

def is_public_activity(activity: Dict[str, Any]) -> bool:
    """檢查活動是否為公開"""
    to = activity.get("to", [])
    cc = activity.get("cc", [])
    
    public_uris = [
        "https://www.w3.org/ns/activitystreams#Public",
        "as:Public",
        "Public"
    ]
    
    return any(uri in to or uri in cc for uri in public_uris)
