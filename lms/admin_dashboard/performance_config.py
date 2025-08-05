"""
Performance Configuration for Admin Dashboard
This file contains settings and configurations for optimizing admin dashboard performance
"""

# Cache Configuration
CACHE_CONFIG = {
    'STATS_CACHE_TIMEOUT': 300,  # 5 minutes for dashboard statistics
    'SESSION_CACHE_TIMEOUT': 60,  # 1 minute for session validation
    'SETTINGS_CACHE_TIMEOUT': 600,  # 10 minutes for system settings
    'USER_STATS_CACHE_TIMEOUT': 180,  # 3 minutes for user statistics
}

# Database Query Optimization
DB_OPTIMIZATION = {
    'USE_SELECT_RELATED': True,  # Use select_related for foreign keys
    'USE_PREFETCH_RELATED': True,  # Use prefetch_related for many-to-many
    'BATCH_SIZE': 20,  # Pagination batch size
    'MAX_QUERY_RESULTS': 1000,  # Maximum results per query
}

# Session Optimization
SESSION_OPTIMIZATION = {
    'CACHE_SESSION_VALIDATION': True,  # Cache session validation results
    'REDUCE_SESSION_UPDATES': True,  # Reduce frequency of session updates
    'SESSION_CHECK_INTERVAL': 60,  # Seconds between session checks
    'TIMEOUT_CHECK_INTERVAL': 30,  # Seconds between timeout checks
}

# Lazy Loading Configuration
LAZY_LOADING = {
    'ENABLED': True,  # Enable lazy loading
    'LOAD_TRIGGERS': ['scroll', 'click', 'tab'],  # Available triggers
    'DEFAULT_TRIGGER': 'scroll',  # Default trigger type
    'LOAD_MARGIN': 50,  # Pixels from viewport to trigger loading
    'DEBOUNCE_DELAY': 250,  # Milliseconds to debounce scroll events
}

# AJAX Endpoints
AJAX_ENDPOINTS = {
    'DASHBOARD_STATS': '/admin/dashboard/stats-ajax/',
    'USER_STATS': '/admin/dashboard/user-stats-ajax/',
    'SECURITY_STATS': '/admin/dashboard/security-stats-ajax/',
    'ACTIVITY_STATS': '/admin/dashboard/activity-stats-ajax/',
}

# Performance Monitoring
PERFORMANCE_MONITORING = {
    'ENABLE_QUERY_LOGGING': False,  # Log slow queries
    'QUERY_TIMEOUT_THRESHOLD': 1000,  # Milliseconds
    'ENABLE_CACHE_MONITORING': True,  # Monitor cache hit rates
    'ENABLE_SESSION_MONITORING': True,  # Monitor session performance
}

# Template Optimization
TEMPLATE_OPTIMIZATION = {
    'USE_TEMPLATE_FRAGMENT_CACHING': True,  # Cache template fragments
    'FRAGMENT_CACHE_TIMEOUT': 300,  # 5 minutes for template fragments
    'MINIFY_TEMPLATES': True,  # Minify HTML output
    'COMPRESS_STATIC_FILES': True,  # Compress CSS/JS files
}

# Security Optimization
SECURITY_OPTIMIZATION = {
    'CACHE_CSRF_TOKENS': True,  # Cache CSRF tokens
    'REDUCE_AUDIT_LOG_FREQUENCY': True,  # Reduce audit log writes
    'BATCH_AUDIT_LOGS': True,  # Batch audit log entries
    'AUDIT_LOG_BATCH_SIZE': 10,  # Number of logs to batch
}

# Implementation Guide
IMPLEMENTATION_STEPS = [
    "1. Replace views.py with views_optimized.py",
    "2. Replace middleware.py with middleware_optimized.py",
    "3. Add lazy_loading.js to static files",
    "4. Update settings.py to use optimized middleware",
    "5. Add cache configuration to settings.py",
    "6. Update templates to use lazy loading attributes",
    "7. Test performance improvements",
]

# Cache Keys
CACHE_KEYS = {
    'DASHBOARD_STATS': 'admin_dashboard_stats',
    'USER_STATS': 'user_stats_{search}_{role}_{status}',
    'SETTINGS_CATEGORIES': 'system_settings_categories',
    'SESSION_VALID': 'session_valid_{user_id}',
    'USER_TIMEOUT': 'user_timeout_{user_id}',
    'PASSWORD_POLICY': 'password_policy_{user_id}',
}

# Database Indexes (for manual creation)
REQUIRED_INDEXES = [
    "CREATE INDEX idx_user_role ON users_user(role);",
    "CREATE INDEX idx_user_created_at ON users_user(created_at);",
    "CREATE INDEX idx_user_is_active ON users_user(is_active);",
    "CREATE INDEX idx_audit_log_timestamp ON admin_dashboard_auditlog(timestamp);",
    "CREATE INDEX idx_audit_log_user ON admin_dashboard_auditlog(user_id);",
    "CREATE INDEX idx_audit_log_action ON admin_dashboard_auditlog(action);",
    "CREATE INDEX idx_user_session_user ON admin_dashboard_usersession(user_id);",
    "CREATE INDEX idx_user_session_active ON admin_dashboard_usersession(is_active);",
]

# Performance Metrics to Monitor
PERFORMANCE_METRICS = [
    'Page load time',
    'Database query count',
    'Cache hit rate',
    'Session validation time',
    'Memory usage',
    'CPU usage',
    'Network requests',
    'Time to first byte (TTFB)',
]

# Optimization Checklist
OPTIMIZATION_CHECKLIST = [
    "✅ Implement lazy loading for statistics",
    "✅ Cache session validation results",
    "✅ Add database indexes",
    "✅ Implement template fragment caching",
    "✅ Optimize database queries with select_related",
    "✅ Reduce audit log frequency",
    "✅ Add AJAX endpoints for dynamic loading",
    "✅ Implement progressive enhancement",
    "✅ Add error handling for failed AJAX requests",
    "✅ Monitor performance metrics",
] 