"""Aggregated API Routers and GraphQL IDE setup."""

from fastapi import APIRouter
from strawberry.fastapi import GraphQLRouter

from gravitypress.api.graphql_schema import schema
from gravitypress.api.rest import router as rest_router

api_router = APIRouter()
api_router.include_router(rest_router)

# Mount Strawberry GraphQL
graphql_app = GraphQLRouter(schema)
