#!/usr/bin/env python3
"""
Test script to verify HSTS headers are properly set

Author: Ahmed Moustafa Abdelkalek
UWE ID: 24033404
"""
import requests
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_hsts_headers():
    """Test HSTS headers on the demo page"""
    print("🔒 Testing HSTS Implementation...")
    print("=" * 50)
    
    # Test URL - use HTTPS directly
    url = "https://127.0.0.1:8443/hsts-demo/"
    
    try:
        # Make request with SSL verification disabled
        response = requests.get(url, verify=False, allow_redirects=False)
        
        print(f"✅ Server is running at: {url}")
        print(f"📊 Status Code: {response.status_code}")
        print(f"🔗 Protocol: HTTPS")
        
        # Check for HSTS header
        hsts_header = response.headers.get('Strict-Transport-Security')
        if hsts_header:
            print(f"✅ HSTS Header Found: {hsts_header}")
        else:
            print("❌ HSTS Header NOT Found!")
        
        print()
        print("🔍 Security Headers Check:")
        
        # Check other security headers
        security_headers = {
            'X-Frame-Options': 'X-Frame-Options',
            'X-Content-Type-Options': 'X-Content-Type-Options',
            'X-XSS-Protection': 'X-XSS-Protection',
            'Referrer-Policy': 'Referrer-Policy',
            'Content-Security-Policy': 'Content-Security-Policy'
        }
        
        for header_name, display_name in security_headers.items():
            header_value = response.headers.get(header_name)
            if header_value:
                print(f"✅ {display_name}: {header_value}")
            else:
                print(f"⚠️  {display_name}: Not set")
        
        print()
        print("🎯 HSTS Test Instructions:")
        print("1. Visit https://127.0.0.1:8443/hsts-demo/ in your browser")
        print("2. Accept the security warning (self-signed certificate)")
        print("3. Try accessing http://127.0.0.1:8000/hsts-demo/ (note the http://)")
        print("4. Your browser should automatically redirect to HTTPS")
        print("5. This demonstrates HSTS preventing downgrade attacks!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running:")
        print("   cd /Users/ahmedmoustafa/hsts/Libsys/lms")
        print("   source ../venv/bin/activate")
        print("   python3 secure_server.py")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_hsts_headers() 