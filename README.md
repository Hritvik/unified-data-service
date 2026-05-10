# Unified Data Service

A microservice for unified data operations with caching and business logic optimization.

## Overview

The Unified Data Service (UDS) provides a generic CRUD interface for any entity type with:
- **Caching** with Redis backend
- **Metrics** and monitoring
- **Business logic optimization** framework
- **Bulk operations** and pagination
- **Pluggable data sources** (MongoDB, APIs, etc.)

## Features

- **Generic CRUD Operations**: Create, Read, Update, Delete for any entity type
- **Advanced Querying**: Complex queries with filters, sorting, and pagination
- **Bulk Operations**: Efficient bulk create, update, and delete operations
- **Caching**: Redis-based caching with configurable TTL and invalidation strategies
- **Business Logic Optimization**: In-memory lookup structures for high-performance operations
- **Metrics & Monitoring**: Built-in metrics for operations, latency, and cache performance
- **Health Checks**: Comprehensive health monitoring for data sources and cache
- **Configuration Management**: Dynamic service registration and configuration

## Quick Start

### Installation

```bash
pip install unified-data-service
```

### Basic Usage

```python
from unified_data_service import UnifiedDataService
from unified_data_service.core import ServiceConfig
from unified_data_service.factories import ServiceFactory

# Create service configuration
config = ServiceConfig(
    name="my-service",
    entity_type="MyEntity",
    data_source={
        "type": "mongodb",
        "collection": "my_entities",
        "database": "my_db"
    },
    cache_backend="redis",
    cache_ttl=300
)

# Create service factory
factory = ServiceFactory()

# Create service
service = await factory.create_service(config)

# Use the service
entity = await service.create({"name": "test", "value": 123})
entities = await service.get_all()
```

### Running the Service

```bash
# Start the service
python -m api.main

# Or with uvicorn directly
uvicorn api.main:app --host 0.0.0.0 --port 8080
```

## API Documentation

Once running, the service provides comprehensive REST API endpoints:

### Core CRUD Endpoints

```
POST   /api/v1/services/{service_name}/entities
GET    /api/v1/services/{service_name}/entities/{id}
PUT    /api/v1/services/{service_name}/entities/{id}
DELETE /api/v1/services/{service_name}/entities/{id}
GET    /api/v1/services/{service_name}/entities
POST   /api/v1/services/{service_name}/entities/bulk
PUT    /api/v1/services/{service_name}/entities/bulk
DELETE /api/v1/services/{service_name}/entities/bulk
```

### Advanced Operations

```
GET    /api/v1/services/{service_name}/search
GET    /api/v1/services/{service_name}/count
POST   /api/v1/services/{service_name}/cache/warm
DELETE /api/v1/services/{service_name}/cache
GET    /api/v1/services/{service_name}/health
GET    /api/v1/services/{service_name}/stats
```

### Service Management

```
GET    /api/v1/services
POST   /api/v1/services
PUT    /api/v1/services/{service_name}
DELETE /api/v1/services/{service_name}
```

## Configuration

### Environment Variables

```bash
# Database
UDS_DATABASE__MONGODB_URI=mongodb://localhost:27017
UDS_DATABASE__MONGODB_DATABASE=unified_data_service

# Cache
UDS_CACHE__REDIS_HOST=localhost
UDS_CACHE__REDIS_PORT=6379
UDS_CACHE__REDIS_PASSWORD=your_password

# Application
UDS_HOST=0.0.0.0
UDS_PORT=8080
UDS_DEBUG=false

# Metrics
UDS_METRICS__ENABLED=true
UDS_METRICS__PORT=9090
```

### Service Configuration

Services can be configured via YAML files or API calls:

```yaml
# config/services/my-service.yaml
name: "my-service"
entity_type: "MyEntity"
data_source:
  type: "mongodb"
  collection: "my_entities"
  database: "my_db"
cache_backend: "redis"
cache_ttl: 300
enable_bulk_operations: true
enable_cache_warming: true
```

## Architecture

The service follows a layered architecture:

- **API Layer**: FastAPI application with REST endpoints
- **Service Layer**: Core business logic and unified data operations
- **Data Source Layer**: Pluggable data source implementations
- **Cache Layer**: Redis-based caching with invalidation strategies
- **Factory Layer**: Service creation and configuration management

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/modelswitch/unified-data-service.git
cd unified-data-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with hot reload
uvicorn api.main:app --reload
```

### Project Structure

```
unified-data-service/
├── api/                    # FastAPI application
│   ├── __init__.py
│   └── main.py            # Main FastAPI app
├── core/                   # Core service logic
│   ├── __init__.py
│   ├── interfaces.py        # Core interfaces
│   └── service.py          # UnifiedDataService implementation
├── config/                 # Configuration management
│   ├── __init__.py
│   └── settings.py         # Application settings
├── factories/              # Service factory
│   ├── __init__.py
│   └── service_factory.py  # Service creation logic
├── data_sources/           # Data source implementations
│   ├── __init__.py
│   └── mongodb_source.py   # MongoDB data source
├── tests/                  # Test suite
├── requirements.txt         # Dependencies
├── pyproject.toml         # Project configuration
└── README.md              # This file
```

## Performance

The service is optimized for:
- **High throughput**: Efficient bulk operations and connection pooling
- **Low latency**: Multi-level caching and optimized queries
- **Scalability**: Horizontal scaling with Redis clustering
- **Memory efficiency**: Configurable cache sizes and TTL strategies

## Monitoring

Built-in metrics include:
- Operation counts and success rates
- Request latency distributions
- Cache hit ratios and performance
- Entity counts and data source health
- Resource utilization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the documentation
- Contact the ModelSwitch team
