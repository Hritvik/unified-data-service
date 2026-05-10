// MongoDB initialization script for Unified Data Service

// Switch to the unified data service database
db = db.getSiblingDB('unified_data_service');

// Create a user for the application
db.createUser({
  user: 'uds_user',
  pwd: 'uds_password',
  roles: [
    {
      role: 'readWrite',
      db: 'unified_data_service'
    }
  ]
});

// Create some initial collections (optional)
db.createCollection('service_configs');
db.createCollection('audit_logs');

print('MongoDB initialized for Unified Data Service');
