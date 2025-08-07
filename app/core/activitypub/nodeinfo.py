from fastapi import APIRouter
from typing import Dict, Any
from app.core.config import settings

nodeinfo_router = APIRouter()

def get_nodeinfo() -> Dict[str, Any]:
    """取得 NodeInfo 資訊"""
    return {
        "links": [
            {
                "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
                "href": f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/.well-known/nodeinfo/2.0"
            }
        ]
    }

@nodeinfo_router.get("/2.0")
def get_nodeinfo_2_0() -> Dict[str, Any]:
    """取得 NodeInfo 2.0 資訊"""
    return {
        "version": "2.0",
        "software": {
            "name": "readr-mesh-activitypub",
            "version": "1.0.0",
            "repository": "https://github.com/readr-media/mesh-activity-pub-server",
            "homepage": "https://readr.tw"
        },
        "protocols": [
            "activitypub"
        ],
        "services": {
            "inbound": [],
            "outbound": [
                "atom1.0",
                "rss2.0"
            ]
        },
        "openRegistrations": False,
        "usage": {
            "users": {
                "total": 0,  # TODO: 實作使用者計數
                "activeMonth": 0,
                "activeHalfyear": 0
            },
            "localPosts": 0,  # TODO: 實作文章計數
            "localComments": 0
        },
        "metadata": {
            "nodeName": "READr Mesh ActivityPub",
            "nodeDescription": "ActivityPub server for READr Mesh federation",
            "maintainer": {
                "name": "READr",
                "email": "tech@readr.tw"
            },
            "langs": [
                "zh-TW",
                "en"
            ],
            "themeColor": "#1a1a1a"
        }
    }
