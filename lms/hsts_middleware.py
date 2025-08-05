"""
Custom middleware to add HSTS headers for demo purposes
"""
"""
HSTS Middleware for adding Strict-Transport-Security headers

Author: Ahmed Moustafa Abdelkalek
UWE ID: 24033404
"""

from django.utils.deprecation import MiddlewareMixin

class HSTSMiddleware(MiddlewareMixin):
    """
    Middleware to add HSTS headers for demo purposes
    """
    def process_response(self, request, response):
        # Add HSTS header for HTTPS requests
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=3600; includeSubDomains'
        
        return response 