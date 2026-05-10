"""FastAPI application for Unified Data Service.

This module provides the main FastAPI application that exposes the unified data
service functionality via RESTful endpoints.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Union, Type

from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from core.interfaces import (
    DataSourceQuery,
    BulkOperationResult,
    PaginatedResult,
    ServiceConfig,
)
from core.service import UnifiedDataService
from factories.service_factory import ServiceFactory
from config.settings import Settings

# Infrastructure imports
import motor.motor_asyncio
from beanie import init_beanie, Document
from redis.asyncio import Redis
from common_utils.redis_client import RedisClient
from common_utils.work_in_progress.events import EventBroadcastService, EventRegistry
from common_utils.logger import get_logger

import importlib
import pkgutil
from typing import Type

logger = get_logger("api.main")


from common_utils.unified_data.hierarchical.service import HierarchicalUnifiedService

# Global service registry
service_registry: Dict[str, Union[UnifiedDataService, HierarchicalUnifiedService]] = {}
service_factory: Optional[ServiceFactory] = None
settings: Optional[Settings] = None


async def discover_beanie_documents(package_name: str) -> List[Type[Document]]:
    """Recursively discover all Beanie Document classes in a package."""
    documents = []
    try:
        package = importlib.import_module(package_name)
        if not hasattr(package, "__path__"):
            return []
        for loader, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            try:
                module = importlib.import_module(module_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, Document)
                        and attr is not Document
                    ):
                        if attr not in documents:
                            documents.append(attr)
            except Exception as e:
                logger.warning(f"Error importing module {module_name}: {e}")
    except Exception as e:
        logger.error(f"Error discovering documents in {package_name}: {e}")
    return documents

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global service_factory, settings
    
    # Initialize settings
    settings = Settings()
    
    # 1. Initialize MongoDB & Beanie
    logger.info("Initializing MongoDB & Beanie...")
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(settings.database.mongodb_uri)
    db_name = settings.database.mongodb_database
    
    # Ping Mongo
    try:
        await mongo_client.admin.command('ping')
        logger.info("MongoDB connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise
    
    # Discover all models
    document_models = await discover_beanie_documents("common_utils.models")
    await init_beanie(database=mongo_client[db_name], document_models=document_models)
    logger.info(f"Beanie initialized with {len(document_models)} models")
    
    # 2. Initialize Redis
    logger.info("Initializing Redis...")
    redis_client = None
    redis_conn = None
    try:
        redis_params = settings.get_redis_connection_params()
        logger.info(f"Redis params: {redis_params}")
        redis_conn = Redis(**redis_params)
        await redis_conn.ping()
        logger.info("Redis connected successfully")
        redis_client = RedisClient(redis_conn)
    except Exception as e:
        logger.warning(f"Failed to connect to Redis, falling back to in-memory: {e}")
        redis_client = None # ServiceFactory will handle None as in-memory
    
    # 3. Initialize Event Broadcast Service
    logger.info("Initializing Event Broadcast Service...")
    event_service = None
    if redis_client:
        try:
            event_registry = EventRegistry()
            event_service = EventBroadcastService(redis_client, event_registry)
            await event_service.start_listening()
        except Exception as e:
            logger.warning(f"Failed to start Event Broadcast Service: {e}")
            event_service = None
    else:
        logger.warning("Event Broadcast Service disabled (requires Redis)")
    
    # 4. Initialize Service Factory
    service_factory = ServiceFactory(settings)
    
    # Load initial services from configuration
    await service_factory.load_services_from_config(
        redis_client=redis_client,
        event_service=event_service,
        mongo_client=mongo_client
    )
    
    # Get all registered services
    service_registry.update(service_factory.get_all_services())
    
    # Register custom endpoints
    for service_name, service in service_registry.items():
        if hasattr(service, 'config') and service.config.controller:
            register_custom_endpoints(app, service_name, service)
    
    logger.info(f"Unified Data Service started with {len(service_registry)} services")
    
    yield
    
    # Cleanup
    logger.info("Unified Data Service shutting down")
    if event_service:
        await event_service.stop_listening()
    if redis_conn:
        await redis_conn.close()
    mongo_client.close()


# Create FastAPI application
app = FastAPI(
    title="Unified Data Service",
    description="Microservice for unified data operations with caching and business logic optimization",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.hierarchical import router as hierarchical_router

app.include_router(hierarchical_router)


# Helper functions
def get_service(service_name: str) -> UnifiedDataService:
    """Get service instance by name."""
    if service_name not in service_registry:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    return service_registry[service_name]


def parse_query_params(
    filters: Optional[str] = Query(None, description="JSON string of filters"),
    limit: Optional[int] = Query(None, description="Maximum number of results"),
    skip: Optional[int] = Query(None, description="Number of results to skip"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: int = Query(1, description="Sort order: 1 for ascending, -1 for descending"),
) -> DataSourceQuery:
    """Parse query parameters into DataSourceQuery."""
    import json
    
    parsed_filters = None
    if filters:
        try:
            parsed_filters = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in filters parameter")
    
    return DataSourceQuery(
        filters=parsed_filters,
        limit=limit,
        skip=skip,
        sort_by=sort_by,
        sort_order=sort_order,
    )


def register_custom_endpoints(app: FastAPI, service_name: str, service: UnifiedDataService):
    """Register custom endpoints from service configuration."""
    if not service.config.controller or not service.config.controller.custom_endpoints:
        return

    for endpoint in service.config.controller.custom_endpoints:
        method = endpoint.method.upper()
        path = endpoint.path
        service_method_name = endpoint.service_method
        description = endpoint.description or ""

        # Full path includes service name prefix
        # Note: In YAML, paths start with /, so we join carefully
        full_path = f"/api/v1/{service_name}{path}"

        logger.info(f"Registering custom endpoint: {method} {full_path} -> {service_method_name}")

        def create_handler(svc, method_path):
            # Split method path (e.g., 'business.resolve_template')
            parts = method_path.split(".")
            
            async def handler(*args, **kwargs):
                target = svc
                for part in parts:
                    target = getattr(target, part, None)
                    if target is None:
                        raise HTTPException(
                            status_code=500, 
                            detail=f"Method {method_path} not found on service {service_name}"
                        )
                
                try:
                    # Call the target method (assume it's async)
                    if asyncio.iscoroutinefunction(target):
                        result = await target(**kwargs)
                    else:
                        result = target(**kwargs)
                    
                    if service.config.controller.response_envelope:
                        return {"success": True, "data": result}
                    return result
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))
                except Exception as e:
                    logger.error(f"Error in custom endpoint {method_path}: {e}", exc_info=True)
                    raise HTTPException(status_code=500, detail=str(e))
            
            return handler

        handler = create_handler(service, service_method_name)
        
        # Add to FastAPI
        app.add_api_route(
            full_path,
            handler,
            methods=[method],
            name=f"{service_name}_{service_method_name}",
            description=description
        )


# Health check endpoints
@app.get("/health")
async def health_check():
    """Overall service health check."""
    health_status = {
        "status": "healthy",
        "service_count": len(service_registry),
        "services": {}
    }
    
    # Check each service
    for service_name, service in service_registry.items():
        try:
            service_health = await service.health_check()
            health_status["services"][service_name] = service_health
            
            if service_health.get("status") != "healthy":
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["services"][service_name] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    
    return health_status


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "name": "Unified Data Service",
        "version": "1.0.0",
        "description": "Microservice for unified data operations",
        "services": list(service_registry.keys()),
    }


# Service management endpoints
@app.get("/api/v1/services")
async def list_services():
    """List all available services."""
    services_info = {}
    for service_name, service in service_registry.items():
        services_info[service_name] = await service.get_service_stats()
    
    return {
        "services": services_info,
        "count": len(service_registry)
    }


@app.get("/api/v1/services/{service_name}")
async def get_service_info(service_name: str = Path(..., description="Service name")):
    """Get detailed information about a specific service."""
    service = get_service(service_name)
    return await service.get_service_stats()


@app.post("/api/v1/services")
async def register_service(config: ServiceConfig):
    """Register a new service."""
    global service_registry
    
    if service_factory is None:
        raise HTTPException(status_code=500, detail="Service factory not initialized")
    
    try:
        service = service_factory.create_service(config)
        service_registry[config.name] = service
        
        return {
            "message": f"Service '{config.name}' registered successfully",
            "service_name": config.name
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/v1/services/{service_name}")
async def update_service(
    service_name: str = Path(..., description="Service name"),
    config: ServiceConfig = Body(...)
):
    """Update an existing service configuration."""
    global service_registry
    
    if service_name not in service_registry:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    try:
        # Remove old service
        del service_registry[service_name]
        
        # Create new service with updated config
        if service_factory is None:
            raise HTTPException(status_code=500, detail="Service factory not initialized")
        
        service = service_factory.create_service(config)
        service_registry[config.name] = service
        
        return {
            "message": f"Service '{config.name}' updated successfully",
            "service_name": config.name
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/v1/services/{service_name}")
async def unregister_service(service_name: str = Path(..., description="Service name")):
    """Unregister a service."""
    global service_registry
    
    if service_name not in service_registry:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    del service_registry[service_name]
    
    return {
        "message": f"Service '{service_name}' unregistered successfully"
    }


# CRUD endpoints for entities
@app.post("/api/v1/services/{service_name}/entities")
async def create_entity(
    service_name: str = Path(..., description="Service name"),
    data: Dict[str, Any] = Body(...)
):
    """Create a new entity."""
    service = get_service(service_name)
    entity = await service.create(data)
    return entity


@app.get("/api/v1/services/{service_name}/entities/{id}")
async def get_entity(
    service_name: str = Path(..., description="Service name"),
    id: str = Path(..., description="Entity ID")
):
    """Get entity by ID."""
    service = get_service(service_name)
    entity = await service.get_by_id(id)
    
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return entity


@app.put("/api/v1/services/{service_name}/entities/{id}")
async def update_entity(
    service_name: str = Path(..., description="Service name"),
    id: str = Path(..., description="Entity ID"),
    data: Dict[str, Any] = Body(...)
):
    """Update entity by ID."""
    service = get_service(service_name)
    entity = await service.update(id, data)
    
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return entity


@app.delete("/api/v1/services/{service_name}/entities/{id}")
async def delete_entity(
    service_name: str = Path(..., description="Service name"),
    id: str = Path(..., description="Entity ID")
):
    """Delete entity by ID."""
    service = get_service(service_name)
    success = await service.delete(id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return {"message": "Entity deleted successfully"}


@app.get("/api/v1/services/{service_name}/entities")
async def list_entities(
    service_name: str = Path(..., description="Service name"),
    query: DataSourceQuery = Depends(parse_query_params)
):
    """List entities with optional filtering and pagination."""
    service = get_service(service_name)
    
    if query.limit is not None or query.skip is not None:
        # Use paginated result
        result = await service.get_paginated(query)
        return result
    else:
        # Use regular list
        entities = await service.get_all(query)
        return {"items": entities, "total": len(entities)}


# Search and query endpoints
@app.get("/api/v1/services/{service_name}/search")
async def search_entities(
    service_name: str = Path(..., description="Service name"),
    query: DataSourceQuery = Depends(parse_query_params)
):
    """Search entities with complex query."""
    service = get_service(service_name)
    entities = await service.search(query)
    return {"items": entities, "total": len(entities)}


@app.get("/api/v1/services/{service_name}/count")
async def count_entities(
    service_name: str = Path(..., description="Service name"),
    query: DataSourceQuery = Depends(parse_query_params)
):
    """Count entities matching query."""
    service = get_service(service_name)
    count = await service.count(query)
    return {"count": count}


# Bulk operations endpoints
@app.post("/api/v1/services/{service_name}/entities/bulk")
async def bulk_create_entities(
    service_name: str = Path(..., description="Service name"),
    data_list: List[Dict[str, Any]] = Body(...)
):
    """Bulk create entities."""
    service = get_service(service_name)
    result = await service.bulk_create(data_list)
    return result


@app.put("/api/v1/services/{service_name}/entities/bulk")
async def bulk_update_entities(
    service_name: str = Path(..., description="Service name"),
    updates: Dict[str, Dict[str, Any]] = Body(...)
):
    """Bulk update entities."""
    service = get_service(service_name)
    result = await service.bulk_update(updates)
    return result


@app.delete("/api/v1/services/{service_name}/entities/bulk")
async def bulk_delete_entities(
    service_name: str = Path(..., description="Service name"),
    ids: List[str] = Body(...)
):
    """Bulk delete entities."""
    service = get_service(service_name)
    result = await service.bulk_delete(ids)
    return result


# Cache management endpoints
@app.post("/api/v1/services/{service_name}/cache/warm")
async def warm_cache(service_name: str = Path(..., description="Service name")):
    """Warm cache for a service."""
    service = get_service(service_name)
    count = await service.warm_cache()
    return {"message": f"Cache warmed with {count} entities", "count": count}


@app.delete("/api/v1/services/{service_name}/cache")
async def invalidate_cache(
    service_name: str = Path(..., description="Service name"),
    keys: Optional[List[str]] = Body(None, description="Specific cache keys to invalidate")
):
    """Invalidate cache for a service."""
    service = get_service(service_name)
    await service.invalidate_cache(keys)
    
    if keys:
        return {"message": f"Invalidated {len(keys)} cache keys"}
    else:
        return {"message": "Invalidated all cache entries"}


# Statistics and monitoring endpoints
@app.get("/api/v1/services/{service_name}/stats")
async def get_service_stats(service_name: str = Path(..., description="Service name")):
    """Get service statistics."""
    service = get_service(service_name)
    stats = await service.get_service_stats()
    return stats


@app.get("/api/v1/services/{service_name}/cache/stats")
async def get_cache_stats(service_name: str = Path(..., description="Service name")):
    """Get cache statistics."""
    service = get_service(service_name)
    stats = await service.get_cache_stats()
    return stats


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
