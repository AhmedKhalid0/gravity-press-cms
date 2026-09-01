"""Main ASGI FastAPI Application for GravityPress CMS."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from gravitypress.api.routes import api_router, graphql_app
from gravitypress.web.admin import admin_router

app = FastAPI(
    title="GravityPress Headless CMS Engine",
    description="High-Performance Headless Git-Based Content Engine & Static Site Generator with GraphQL & Free Cloudflare Pages Edge Deployment",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for headless frontend & mobile apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API
app.include_router(api_router)

# Mount Strawberry GraphQL IDE & Endpoint at /graphql
app.include_router(graphql_app, prefix="/graphql")

# Mount Admin Web Studio
app.include_router(admin_router)
