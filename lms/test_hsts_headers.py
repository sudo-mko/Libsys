#!/usr/bin/env python3
"""
Test script to verify HSTS headers are working correctly
"""
import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for self-signed certificate
urllib3.disable_warnings(InsecureRequestWarning)

def test_hsts_headers():
    """Test HSTS headers on the local server"""
    url = "https://127.0.0.1:8443/hsts-demo/"
    
    try:
        print("🔒 Testing HSTS Implementation...")
        print("=" * 50)
        
        # Make request to HTTPS endpoint
        response = requests.get(url, verify=False)
        
        print(f"✅ Server is running at: {url}")
        print(f"📊 Status Code: {response.status_code}")
        print(f"🔗 Protocol: HTTPS")
        
        # Check for HSTS header
        hsts_header = response.headers.get('Strict-Transport-Security')
        if hsts_header:
            print(f"✅ HSTS Header Found: {hsts_header}")
        else:
            print("❌ HSTS Header NOT Found!")
            
        # Check other security headers
        security_headers = {
            'X-Frame-Options': 'Frame protection',
            'X-Content-Type-Options': 'Content type sniffing protection',
            'X-XSS-Protection': 'XSS protection',
            'Referrer-Policy': 'Referrer policy',
            'Content-Security-Policy': 'CSP (if set)'
        }
        
        print("\n🔍 Security Headers Check:")
        for header, description in security_headers.items():
            value = response.headers.get(header)
            if value:
                print(f"✅ {header}: {value}")
            else:
                print(f"⚠️  {header}: Not set")
                
        print("\n🎯 HSTS Test Instructions:")
        print("1. Visit https://127.0.0.1:8443/hsts-demo/ in your browser")
        print("2. Accept the security warning (self-signed certificate)")
        print("3. Try accessing http://127.0.0.1:8443/hsts-demo/ (note the http://)")
        print("4. Your browser should automatically redirect to HTTPS")
        print("5. This demonstrates HSTS preventing downgrade attacks!")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running:")
        print("   cd /Users/ahmedmoustafa/hsts/Libsys/lms")
        print("   source ../venv/bin/activate")
        print("   python3 secure_server.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_hsts_headers() 