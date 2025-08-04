# Role-Based User Creation Security Fix

## Problem Fixed
Previously, library managers could create admin users, which is a serious security vulnerability since admins have higher privileges than managers.

## Solution Implemented

### 1. **Form-Level Restrictions** (`AdminUserCreationForm`)
- Modified form to accept `current_user` parameter
- Dynamically filters role choices based on current user's role:
  - **Admins**: Can create any role (member, librarian, manager, admin)
  - **Managers**: Can only create member and librarian accounts
  - **Others**: Can only create members (shouldn't happen due to view restrictions)

### 2. **Server-Side Validation**
- Added `clean_role()` method to prevent bypassing frontend restrictions
- Validates role selection against user permissions on form submission
- Provides clear error messages when invalid roles are selected

### 3. **View Updates**
- Updated `create_user` view to pass `current_user` to form
- Updated `edit_user` view in admin dashboard to restrict role changes
- Added permission checks when editing existing user roles

### 4. **Template-Level Protection**
- Role dropdown in templates now only shows allowed options
- No UI elements for unauthorized actions

## Security Hierarchy

```
Admin (highest)
  ├── Can create: Admin, Manager, Librarian, Member
  └── Can edit roles to: Any role

Manager
  ├── Can create: Librarian, Member only
  └── Can edit roles to: Librarian, Member only

Librarian/Member (lowest)
  ├── Cannot access user creation
  └── Cannot edit user roles
```

## Code Changes

### 1. Form Modifications (`users/forms.py`)
```python
def __init__(self, *args, **kwargs):
    current_user = kwargs.pop('current_user', None)
    super().__init__(*args, **kwargs)
    
    if current_user:
        self.fields['role'].choices = self.get_allowed_role_choices(current_user)

def get_allowed_role_choices(self, current_user):
    if current_user.role == 'admin':
        return User.ROLE_CHOICES
    elif current_user.role == 'manager':
        return [
            ('member', 'Library Member'),
            ('librarian', 'Librarian'),
        ]
    else:
        return [('member', 'Library Member')]
```

### 2. View Updates (`users/views.py`)
```python
# Pass current user to form
form = AdminUserCreationForm(request.POST, current_user=request.user)
form = AdminUserCreationForm(current_user=request.user)
```

### 3. Admin Dashboard Protection (`admin_dashboard/views.py`)
```python
# Restrict role changes in edit_user view
if request.user.role == 'admin':
    allowed_roles = User.ROLE_CHOICES
elif request.user.role == 'manager':
    allowed_roles = [
        ('member', 'Library Member'),
        ('librarian', 'Librarian'),
    ]
```

## Security Benefits

### ✅ **Prevents Privilege Escalation**
- Managers cannot create accounts with higher privileges
- Users cannot bypass restrictions through form manipulation

### ✅ **Defense in Depth**
- Frontend restrictions (UI level)
- Form validation (application level)  
- View-level checks (server level)

### ✅ **Clear User Feedback**
- Appropriate error messages when restrictions are violated
- UI only shows valid options to prevent confusion

### ✅ **Maintains Flexibility**
- Admins retain full user management capabilities
- Managers can still perform their legitimate duties
- Easy to extend for future role additions

## Testing

### Manual Testing Steps:
1. **Login as Manager**: Try to create admin user → Should only see Member/Librarian options
2. **Login as Admin**: Try to create admin user → Should see all role options
3. **Form Manipulation**: Try to POST admin role as manager → Should get validation error
4. **Edit User**: Manager tries to change user to admin → Should get permission error

### Expected Behavior:
- **Managers**: Can create/edit Members and Librarians only
- **Admins**: Can create/edit any role
- **Security**: No privilege escalation possible through any method

## Backward Compatibility
- ✅ Existing admin functionality unchanged
- ✅ No breaking changes to templates or URLs
- ✅ Graceful fallbacks if user context missing
- ✅ All existing user creation flows continue to work

This fix ensures proper role-based access control while maintaining the system's usability and flexibility.