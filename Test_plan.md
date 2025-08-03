# Test Writing Instructions

## **Goal**

Your task is to write test cases for each app in the LMS project.  
**Do not change or refactor any code outside the test files.**  
All your work should be inside the `tests.py` file of each app.

---

## **Expanded Test Areas (Must Cover)**

Your tests should now also include these new features and logic:

- **Account Lockout Logic**
  - Test locking after too many failed login attempts.
  - Test lock duration, auto-unlock, and manual unlock by manager/admin.
  - Test that only allowed roles are locked.
  - Test reset of failed attempts.
- **Password Expiry & Change Policy**
  - Test password expiry for admin/manager after 6 months.
  - Test forced password change and marking as changed.
- **Membership Management**
  - Test assigning/removing/upgrading memberships.
  - Test that membership types in use cannot be deleted.
  - Test membership stats and distribution.
- **Role-Based Permissions**
  - Test access to management/admin views for allowed/forbidden roles.
- **User CRUD and Validation**
  - Test create, edit, delete (including edge cases, required fields, and forbidden actions).
- **Login/Registration Edge Cases**
  - Test login for locked/expired users and wrong credentials.
  - Test registration with valid/invalid data.
- **Statistics/Reporting**
  - Test accuracy of dashboard/user/membership stats.

## **Step-by-Step Instructions**

### 1. **Understand What to Test**

- Each app (like `users`, `library`, `borrow`, `fines`, `reservations`) has a `tests.py` file.
- Your job is to write tests for the main classes and functions in that app.
- Focus on:
  - Models (e.g., User, Book, BorrowRecord)
  - Forms (e.g., UserCreationForm)
  - Important functions in views

### 2. **Never Edit Main Code**

- **Do NOT** change any code in `models.py`, `views.py`, `forms.py`, or any other file except `tests.py`.
- If you think something in the main code is wrong or missing, make a note, but do not change it.

### 3. **How to Write a Test Case**

- Open the `tests.py` file in the app you are working on.
- Each test is a Python function inside a class that inherits from `django.test.TestCase`.
- Example structure:

  ```python
  from django.test import TestCase
  from .models import User  # Import the class you want to test

  class UserModelTest(TestCase):
      def test_user_creation(self):
          user = User.objects.create(username='testuser')
          self.assertEqual(user.username, 'testuser')
  ```

- Use `assertEqual`, `assertTrue`, `assertFalse`, etc., to check if the result matches what you expect.

### 4. **What Kind of Tests to Write**

- **Positive Test:** Give correct data and check if it works.
- **Negative Test:** Give wrong or bad data and check if the system rejects it.
- **Boundary Test:** Test with minimum/maximum values, empty fields, etc.

#### Example Test Cases:

| #   | Description                | Test Input/Data          | Expected Result               |
| --- | -------------------------- | ------------------------ | ----------------------------- |
| 1   | Strong password enforced   | password="abc123"        | Should NOT allow (too weak)   |
| 2   | No negative fine amount    | fine_amount=-10          | Should raise error/validation |
| 3   | Book borrow date in future | borrow_date="2099-01-01" | Should NOT allow              |

### 5. **How to Run Your Tests**

- Open a terminal in the project folder.
- Run:
  ```
  python manage.py test
  ```
- This will run all test cases in all `tests.py` files.
- Check the output. If your test passes, great! If it fails, check your test code.

### 6. **What to Do If You Find a Problem**

- If a test fails because the main code doesn’t handle bad data, **do not** try to fix the main code.
- Instead, write a comment in your test file about what you found.

### 7. **Keep a Record**

- For each test, write a short comment explaining:
  - What you are testing
  - What input you used
  - What you expected to happen

---

## **Checklist for Each App**

- [ ] Open `tests.py` in the app.
- [ ] List all important classes/functions to test.
- [ ] Write at least one positive, one negative, and one boundary test for each.
- [ ] Run your tests and check results.
- [ ] Do NOT edit any file except `tests.py`.
- [ ] Add comments to explain your tests.

---

## **Example for the `users` App**

```python
from django.test import TestCase
from .models import User
from .forms import UserCreationForm

class UserTests(TestCase):
    def test_strong_password(self):
        """
        Test that weak passwords are rejected.
        """
        form = UserCreationForm(data={
            'username': 'testuser',
            'password1': 'abc123',  # too weak
            'password2': 'abc123',
        })
        self.assertFalse(form.is_valid())
```

---

## **If You Are Stuck**

- Ask your mentor or team lead for help.
- Do NOT guess and change main code files.

---

**Summary:**  
Your job is to add test cases to each app’s `tests.py` file only. Write clear, simple tests. Never change the main app code. Run your tests and record what happens. If you find issues, write a note in the test file.

---
