"""
Cache Configuration for Admin Dashboard
Django cache settings and configuration
"""

# Cache Configuration for Django Settings
CACHE_CONFIG = {
    # Development Cache Configuration (SQLite-based)
    'DEVELOPMENT': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'admin_dashboard_cache',
        'TIMEOUT': 300,  # 5 minutes default
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,  # 1/3 of entries removed when max is reached
        }
    },
    
    # Production Cache Configuration (Redis-based)
    'PRODUCTION': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'admin_dashboard',
        'TIMEOUT': 300,  # 5 minutes default
    },
    
    # Memory Cache Configuration (for testing)
    'TESTING': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'admin_dashboard_test_cache',
        'TIMEOUT': 60,  # 1 minute for testing
        'OPTIONS': {
            'MAX_ENTRIES': 100,
        }
    },
}

# Cache Key Patterns
CACHE_KEY_PATTERNS = {
    'DASHBOARD_STATS': 'admin_dashboard:stats:{hash}',
    'USER_STATS': 'admin_dashboard:user_stats:{search}:{role}:{status}',
    'AUDIT_LOGS': 'admin_dashboard:audit_logs:{filters}:{page}',
    'SYSTEM_SETTINGS': 'admin_dashboard:settings:categories',
    'SECURITY_STATS': 'admin_dashboard:security:stats',
    'SESSION_DATA': 'admin_dashboard:session:{user_id}',
    'REPORTS': 'admin_dashboard:reports:{report_type}:{date_range}',
}

# Cache Timeouts (in seconds)
CACHE_TIMEOUTS = {
    'DASHBOARD_STATS': 300,      # 5 minutes
    'USER_STATS': 180,           # 3 minutes
    'AUDIT_LOGS': 120,           # 2 minutes
    'SYSTEM_SETTINGS': 600,      # 10 minutes
    'SECURITY_STATS': 300,       # 5 minutes
    'SESSION_DATA': 60,          # 1 minute
    'REPORTS': 900,             # 15 minutes
    'TEMPLATE_FRAGMENTS': 300,   # 5 minutes
    'API_RESPONSES': 180,        # 3 minutes
}

# Cache Invalidation Patterns
CACHE_INVALIDATION_PATTERNS = {
    'USER_CHANGED': [
        'admin_dashboard:user_stats:*',
        'admin_dashboard:session:*',
    ],
    'SETTING_CHANGED': [
        'admin_dashboard:settings:*',
        'admin_dashboard:stats:*',
    ],
    'AUDIT_LOG_ADDED': [
        'admin_dashboard:audit_logs:*',
        'admin_dashboard:security:stats',
    ],
    'SECURITY_EVENT': [
        'admin_dashboard:security:stats',
        'admin_dashboard:audit_logs:*',
    ],
}

# Cache Middleware Configuration
CACHE_MIDDLEWARE_CONFIG = {
    'CACHE_MIDDLEWARE_SECONDS': 300,  # 5 minutes
    'CACHE_MIDDLEWARE_KEY_PREFIX': 'admin_dashboard',
    'CACHE_MIDDLEWARE_ALIAS': 'default',
}

# Cache Backend Selection Helper
def get_cache_config(environment='DEVELOPMENT'):
    """
    Get cache configuration based on environment
    
    Args:
        environment: Environment type (DEVELOPMENT, PRODUCTION, TESTING)
        
    Returns:
        Cache configuration dictionary
    """
    return CACHE_CONFIG.get(environment, CACHE_CONFIG['DEVELOPMENT'])

# Cache Key Generation Helper
def generate_cache_key(pattern, **kwargs):
    """
    Generate cache key using pattern and parameters
    
    Args:
        pattern: Cache key pattern from CACHE_KEY_PATTERNS
        **kwargs: Parameters to substitute in pattern
        
    Returns:
        Generated cache key string
    """
    import hashlib
    
    # Replace placeholders in pattern
    key = pattern
    for key_name, value in kwargs.items():
        placeholder = f"{{{key_name}}}"
        if placeholder in key:
            key = key.replace(placeholder, str(value))
    
    # If key is too long, hash it
    if len(key) > 250:
        key = hashlib.md5(key.encode()).hexdigest()
    
    return key

# Cache Performance Monitoring
CACHE_MONITORING = {
    'ENABLE_MONITORING': True,
    'LOG_CACHE_HITS': True,
    'LOG_CACHE_MISSES': True,
    'LOG_SLOW_CACHE_OPERATIONS': True,
    'SLOW_CACHE_THRESHOLD': 100,  # milliseconds
    'CACHE_STATS_INTERVAL': 3600,  # 1 hour
}

# Cache Compression Settings
CACHE_COMPRESSION = {
    'ENABLE_COMPRESSION': True,
    'COMPRESSION_THRESHOLD': 1024,  # bytes
    'COMPRESSION_LEVEL': 6,  # 0-9, higher = more compression
}

# Cache Serialization Settings
CACHE_SERIALIZATION = {
    'SERIALIZER': 'json',  # json, pickle, msgpack
    'ENABLE_COMPRESSION': True,
    'COMPRESSION_LEVEL': 6,
}

# Database Cache Table Creation SQL
CACHE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS "django_cache" (
    "cache_key" varchar(255) NOT NULL PRIMARY KEY,
    "value" text NOT NULL,
    "expires" integer(11) NOT NULL
);
CREATE INDEX IF NOT EXISTS "django_cache_expires" ON "django_cache" ("expires");
"""

# Cache Management Commands
CACHE_MANAGEMENT_COMMANDS = {
    'CLEAR_ALL': 'python manage.py clearcache',
    'CLEAR_PATTERN': 'python manage.py clearcache --pattern "admin_dashboard:*"',
    'SHOW_STATS': 'python manage.py cache_stats',
    'WARM_CACHE': 'python manage.py warm_cache',
}

# Cache Health Check Configuration
CACHE_HEALTH_CHECK = {
    'ENABLE_HEALTH_CHECK': True,
    'HEALTH_CHECK_INTERVAL': 300,  # 5 minutes
    'HEALTH_CHECK_TIMEOUT': 5,     # 5 seconds
    'HEALTH_CHECK_KEY': 'admin_dashboard:health_check',
}

# Cache Error Handling
CACHE_ERROR_HANDLING = {
    'GRACEFUL_DEGRADATION': True,
    'FALLBACK_TO_DATABASE': True,
    'LOG_CACHE_ERRORS': True,
    'RETRY_ATTEMPTS': 3,
    'RETRY_DELAY': 1,  # seconds
}

# Cache Security Settings
CACHE_SECURITY = {
    'ENABLE_KEY_ENCRYPTION': False,  # For sensitive data
    'KEY_PREFIX': 'admin_dashboard',
    'SECURE_KEY_GENERATION': True,
    'PREVENT_KEY_COLLISION': True,
}

# Implementation Guide
IMPLEMENTATION_STEPS = [
    "1. Add cache configuration to settings.py",
    "2. Create cache table: python manage.py createcachetable",
    "3. Import and use AdminDashboardCacheManager in views",
    "4. Add cache middleware to MIDDLEWARE setting",
    "5. Configure cache backends based on environment",
    "6. Test cache functionality",
    "7. Monitor cache performance",
]

# Cache Backend Requirements
CACHE_REQUIREMENTS = {
    'DEVELOPMENT': [
        'django.core.cache.backends.db.DatabaseCache',
    ],
    'PRODUCTION': [
        'django-redis',
        'redis',
    ],
    'TESTING': [
        'django.core.cache.backends.locmem.LocMemCache',
    ],
}

# Cache Performance Metrics
CACHE_METRICS = [
    'Cache hit rate',
    'Cache miss rate',
    'Average response time',
    'Cache size',
    'Eviction rate',
    'Memory usage',
    'Network latency (for Redis)',
    'Connection pool usage',
]

# Cache Optimization Tips
CACHE_OPTIMIZATION_TIPS = [
    "Use appropriate cache timeouts for different data types",
    "Implement cache warming for frequently accessed data",
    "Use cache key patterns for easy invalidation",
    "Monitor cache hit rates and adjust accordingly",
    "Use compression for large cache entries",
    "Implement graceful degradation when cache is unavailable",
    "Use cache decorators for function-level caching",
    "Implement cache versioning for data structure changes",
] 