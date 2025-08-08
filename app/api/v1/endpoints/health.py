from fastapi import APIRouter
from app.core.graphql_client import GraphQLClient

router = APIRouter()

@router.get("/")
async def health_check():
    """Health check endpoint"""
    gql_status = "healthy"
    try:
        gql = GraphQLClient()
        await gql.query("query __Ping { __typename }")
    except Exception as e:
        gql_status = f"unhealthy: {str(e)}"

    return {"status": "ok", "graphql": gql_status, "service": "READr Mesh ActivityPub Server"}
