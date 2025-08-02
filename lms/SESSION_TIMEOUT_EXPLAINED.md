# 🕐 Session Timeout System - How It Works

## 📋 Overview

The session timeout system automatically logs out inactive users to enhance security. Here's exactly how user inactivity is determined and managed.

## 🔍 How Inactivity is Detected

### 1. **Activity Tracking**
```python
# Every request updates last activity timestamp
request.session['last_activity'] = timezone.now().isoformat()
```

### 2. **Inactivity Calculation**
```python
# On each request, check time since last activity
now = timezone.now()
last_activity = timezone.datetime.fromisoformat(request.session.get('last_activity'))
inactive_time = now - last_activity

# Compare with user's timeout setting
if inactive_time > timedelta(minutes=timeout_minutes):
    # User is considered inactive - logout
```

### 3. **Timeout Configuration**
```python
# Default timeouts by role (in minutes)
SESSION_TIMEOUT_BY_ROLE = {
    'member': 15,        # 15 minutes for regular members
    'librarian': 15,     # 15 minutes for librarians  
    'manager': 30,       # 30 minutes for managers
    'admin': 30,         # 30 minutes for admins
}
```

## ⚙️ How the System Works

### **Step-by-Step Process:**

1. **User Makes Request** → Middleware intercepts
2. **Check Authentication** → Only for logged-in users
3. **Get Last Activity** → From session data
4. **Calculate Inactive Time** → Current time - Last activity
5. **Check Timeout Rule** → Compare with user's timeout setting
6. **Action Decision:**
   - ✅ **Still Active**: Update activity timestamp, continue
   - ❌ **Timed Out**: Log out, redirect to login, show message

### **Code Flow:**
```python
# admin_dashboard/middleware.py - SessionTimeoutMiddleware
def __call__(self, request):
    if request.user.is_authenticated:
        timeout_minutes = self._get_user_timeout(request)
        now = timezone.now()
        last_activity = request.session.get('last_activity')
        
        if last_activity:
            last_activity = timezone.datetime.fromisoformat(last_activity)
            if now - last_activity > timedelta(minutes=timeout_minutes):
                # TIMEOUT - User is inactive
                self._log_session_timeout(request)
                logout(request)
                messages.warning(request, 
                    f"Your session expired due to {timeout_minutes} minutes of inactivity")
                return redirect('users:login')
        
        # Update activity for next check
        request.session['last_activity'] = now.isoformat()
```

## 🎯 Customizable Timeout Settings

### **Per-User Configuration:**
- Each user can have individual timeout settings
- Stored in `UserSession.timeout_minutes`
- Overrides role-based defaults

### **Role-Based Defaults:**
- **Members**: 15 minutes (security priority)
- **Librarians**: 15 minutes (frequent public access)
- **Managers**: 30 minutes (more authority, longer sessions)
- **Admins**: 30 minutes (system access, longer tasks)

## 🧪 Testing the System

### **1. Manual Test Commands:**
```bash
# Test with 1-minute timeout
python manage.py test_session_timeout --timeout-minutes 1

# Test specific user
python manage.py test_session_timeout --username mario --timeout-minutes 2

# Monitor all sessions in real-time
python manage.py monitor_sessions --watch --interval 10
```

### **2. Test Results Example:**
```
Testing session timeout for user: mk
User role: member
Simulated timeout: 1 minutes
Created test session: test_session_1754128267.942494
Last activity: 2025-08-02 09:49:07+00:00
Current time: 2025-08-02 09:51:07+00:00
Inactive for: 2.0 minutes
❌ Session SHOULD be timed out (inactive > 1 min)
✅ Session marked as inactive and logged
```

## 📊 Monitoring & Verification

### **Real-Time Session Status:**
```
🔍 Session Timeout Monitor
============================================================
🟢 ACTIVE   mk1 (Admin)          Inactive: 1.9m / 30m (Last: 09:49:16)
🟡 WARNING  mario (Member)       Inactive: 13.8m / 15m (Last: 09:37:25)
🔴 EXPIRED  john (Librarian)     Inactive: 16.2m / 15m (Last: 09:34:52)
============================================================
📈 Summary: 1 expired | 1 expiring soon | 1 active
```

### **Status Indicators:**
- 🟢 **ACTIVE**: Session is valid, user can continue
- 🟡 **WARNING**: Close to timeout (within 2 minutes)
- 🔴 **EXPIRED**: Should be logged out on next request

## 🔒 Security Features

### **1. Automatic Logout:**
- No user intervention required
- Happens on next page request
- Cannot be bypassed by staying on same page

### **2. Audit Logging:**
```python
AuditLog.objects.create(
    user=request.user,
    action='SESSION_TIMEOUT',
    details="Session automatically timed out due to inactivity"
)
```

### **3. Session Cleanup:**
- UserSession records marked inactive
- Django sessions deleted
- Database cleaned automatically

## 🎛️ Admin Management

### **Session Management Dashboard:**
- View all active sessions
- See timeout settings per user
- Modify individual user timeouts
- Monitor security events

### **Configurable Settings:**
```python
# In admin dashboard - session management
user.timeout_minutes = 45  # Custom timeout for specific user
user.save()

# Role-based defaults in settings.py
SESSION_TIMEOUT_BY_ROLE = {
    'member': 10,     # Shorter for security
    'admin': 60,      # Longer for complex tasks
}
```

## ✅ Verification Methods

### **1. Check Session Database:**
```sql
SELECT user_id, username, is_active, last_activity, timeout_minutes 
FROM admin_dashboard_usersession 
WHERE is_active = true;
```

### **2. Check Audit Logs:**
```sql
SELECT user_id, action, details, timestamp 
FROM admin_dashboard_auditlog 
WHERE action = 'SESSION_TIMEOUT' 
ORDER BY timestamp DESC;
```

### **3. Live Testing:**
1. Login as test user
2. Wait for timeout period + 1 minute
3. Make any request (click link, refresh page)
4. Should be redirected to login with timeout message

## 🚀 How to Ensure It Works

### **Testing Checklist:**

✅ **Basic Functionality:**
- [ ] User logs in successfully
- [ ] Session activity updates on each request
- [ ] Timeout occurs after configured period
- [ ] User redirected to login with message
- [ ] Audit log entry created

✅ **Role-Based Testing:**
- [ ] Member times out after 15 minutes
- [ ] Admin times out after 30 minutes
- [ ] Custom timeout overrides role default

✅ **Security Validation:**
- [ ] Cannot access protected pages after timeout
- [ ] Session data cleared completely
- [ ] Multiple sessions handled correctly

✅ **Admin Features:**
- [ ] Can view active sessions
- [ ] Can modify user timeout settings
- [ ] Can monitor session activity

### **Production Monitoring:**
```bash
# Daily session health check
python manage.py monitor_sessions > session_report.txt

# Check for suspicious session patterns
python manage.py audit_logs --action SESSION_TIMEOUT --date-from today
```

The session timeout system is **fully functional** and provides enterprise-level security with comprehensive monitoring and customization capabilities.