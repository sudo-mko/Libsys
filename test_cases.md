# Library Management System - Test Case Table

| Test Case | Description | Test Dataset / Input | Expected Output | Actual | Status |
|-----------|-------------|---------------------|-----------------|--------|--------|

## Authentication & User Management

| 1 | Enforce strong passwords | min 8 characters, upper/lowercase, number, special character (e.g., "StrongPass123!") | Accept the password into system | As expected | [pass/fail] |
| 2 | Reject weak passwords | password with only lowercase (e.g., "weakpass") | Reject password with validation error | As expected | [pass/fail] |
| 3 | Account lockout after failed attempts | 5 consecutive failed login attempts for member role | Account locked for 5 minutes | As expected | [pass/fail] |
| 4 | Auto-unlock account after timeout | Wait 5 minutes after account lockout | Account automatically unlocked | As expected | [pass/fail] |
| 5 | Manual account unlock by admin | Admin unlocks locked user account | Account immediately unlocked | As expected | [pass/fail] |
| 6 | Password expiry for admin/manager | Admin user with password older than 6 months | Force password change on login | As expected | [pass/fail] |
| 7 | Phone number validation | Valid phone number format (+1234567890) | Accept phone number | As expected | [pass/fail] |
| 8 | Invalid phone number rejection | Phone number too short (123456) | Reject with validation error | As expected | [pass/fail] |
| 9 | User registration with valid data | Complete form with all required fields | User account created successfully | As expected | [pass/fail] |
| 10 | Duplicate username prevention | Register with existing username | Registration rejected with error | As expected | [pass/fail] |

## Role-Based Access Control

| 11 | Member access restrictions | Member user tries to access admin dashboard | Access denied, redirect to home | As expected | [pass/fail] |
| 12 | Librarian book management access | Librarian user accesses book management | Access granted to book CRUD operations | As expected | [pass/fail] |
| 13 | Manager user management access | Manager user accesses user management | Access granted to user management features | As expected | [pass/fail] |
| 14 | Admin full system access | Admin user accesses all system features | Full access granted to all modules | As expected | [pass/fail] |
| 15 | Invalid role assignment | Assign invalid role to user | Role assignment rejected | As expected | [pass/fail] |

## Book Management

| 16 | Add new book with valid data | Book with title, author, ISBN, category, branch | Book created successfully | As expected | [pass/fail] |
| 17 | Duplicate ISBN prevention | Add book with existing ISBN | Book creation rejected | As expected | [pass/fail] |
| 18 | Book search functionality | Search for book by title/author | Relevant books returned | As expected | [pass/fail] |
| 19 | Update book information | Modify book title and description | Book updated successfully | As expected | [pass/fail] |
| 20 | Delete book with no borrowings | Delete book not currently borrowed | Book deleted successfully | As expected | [pass/fail] |
| 21 | Prevent deletion of borrowed book | Try to delete currently borrowed book | Deletion prevented with error | As expected | [pass/fail] |

## Borrowing System

| 22 | Book borrowing request | Member requests to borrow available book | Borrowing request created with pending status | As expected | [pass/fail] |
| 23 | Borrowing approval by librarian | Librarian approves pending borrowing request | Status changed to approved, pickup code generated | As expected | [pass/fail] |
| 24 | Pickup code validation | Valid 10-character pickup code | Book marked as borrowed | As expected | [pass/fail] |
| 25 | Invalid pickup code rejection | Invalid or expired pickup code | Pickup rejected with error message | As expected | [pass/fail] |
| 26 | Book return process | Return borrowed book | Status changed to returned, return date recorded | As expected | [pass/fail] |
| 27 | Extension request | Request extension for borrowed book | Extension request created | As expected | [pass/fail] |
| 28 | Extension approval | Librarian approves extension request | Due date extended by allowed days | As expected | [pass/fail] |
| 29 | Prevent multiple extensions | Request second extension for same borrowing | Request rejected | As expected | [pass/fail] |
| 30 | Overdue book detection | Book past due date | Status changed to overdue | As expected | [pass/fail] |

## Reservation System

| 31 | Regular reservation | Member reserves available book | Regular reservation created | As expected | [pass/fail] |
| 32 | Priority reservation | Premium member makes priority reservation | Priority reservation created | As expected | [pass/fail] |
| 33 | Reservation confirmation | Librarian confirms reservation | Status changed to confirmed | As expected | [pass/fail] |
| 34 | Reservation expiration | Reservation not picked up within timeframe | Status changed to expired | As expected | [pass/fail] |
| 35 | Reservation rejection | Librarian rejects reservation request | Status changed to rejected | As expected | [pass/fail] |

## Fine Management

| 36 | Overdue fine calculation (1-3 days) | Book 2 days overdue | Fine = 4.00 MVR (2 days × 2 MVR) | As expected | [pass/fail] |
| 37 | Overdue fine calculation (4-7 days) | Book 5 days overdue | Fine = 16.00 MVR (3×2 + 2×5) | As expected | [pass/fail] |
| 38 | Overdue fine calculation (8+ days) | Book 10 days overdue | Fine = 46.00 MVR (3×2 + 4×5 + 3×10) | As expected | [pass/fail] |
| 39 | Damaged book fine | Report book as damaged (price: 100 MVR) | Fine = 150.00 MVR (100 + 50 processing) | As expected | [pass/fail] |
| 40 | Fine payment | Pay outstanding fine | Fine marked as paid, payment date recorded | As expected | [pass/fail] |
| 41 | Zero fine for on-time return | Return book on or before due date | No fine generated | As expected | [pass/fail] |

## Membership Management

| 42 | Assign membership to user | Assign Basic membership to member | Membership assigned with benefits applied | As expected | [pass/fail] |
| 43 | Membership upgrade | Upgrade from Basic to Premium | New membership limits applied | As expected | [pass/fail] |
| 44 | Prevent deletion of active membership type | Delete membership type with active users | Deletion prevented | As expected | [pass/fail] |
| 45 | Membership benefits enforcement | Check borrowing limits for membership type | Limits enforced per membership rules | As expected | [pass/fail] |

## Branch & Section Management

| 46 | Create new branch | Add branch with name and location | Branch created successfully | As expected | [pass/fail] |
| 47 | Add section to branch | Create section within existing branch | Section created and linked to branch | As expected | [pass/fail] |
| 48 | Delete empty branch | Delete branch with no books/sections | Branch deleted successfully | As expected | [pass/fail] |
| 49 | Prevent deletion of branch with books | Delete branch containing books | Deletion prevented | As expected | [pass/fail] |

## GDPR & Privacy

| 50 | Privacy consent validation | Register without privacy consent | Registration prevented | As expected | [pass/fail] |
| 51 | Marketing consent tracking | User opts in/out of marketing | Consent properly recorded | As expected | [pass/fail] |
| 52 | Account deletion request | User requests account deletion | Account marked for deletion, data anonymized | As expected | [pass/fail] |

## Security & Audit

| 53 | Audit log creation | User performs login action | Audit log entry created with details | As expected | [pass/fail] |
| 54 | Failed login tracking | Multiple failed login attempts | All attempts logged with IP/timestamp | As expected | [pass/fail] |
| 55 | Session timeout | User inactive beyond role timeout limit | Session expired, user logged out | As expected | [pass/fail] |
| 56 | Password history | Admin changes password to previous one | Password change rejected | As expected | [pass/fail] |

## Admin Dashboard & Reports

| 57 | User statistics report | Generate user statistics | Accurate count and breakdown by role | As expected | [pass/fail] |
| 58 | Library operations report | Generate borrowing/return statistics | Accurate operational metrics | As expected | [pass/fail] |
| 59 | Security report | Generate security events report | Failed logins and threats identified | As expected | [pass/fail] |
| 60 | Activity report | Generate system activity report | User activities properly tracked | As expected | [pass/fail] |

## Input Validation & Edge Cases

| 61 | SQL injection prevention | Input with SQL injection attempt | Input sanitized, no DB compromise | As expected | [pass/fail] |
| 62 | XSS prevention | Input with script tags | Content escaped, no script execution | As expected | [pass/fail] |
| 63 | File upload validation | Upload non-image file as book cover | Upload rejected with error | As expected | [pass/fail] |
| 64 | Large file upload | Upload image larger than size limit | Upload rejected with size error | As expected | [pass/fail] |
| 65 | Special characters in search | Search with special characters | Search handles characters safely | As expected | [pass/fail] |

## Performance & Load Testing

| 66 | Concurrent user access | 50 users access system simultaneously | System remains responsive | As expected | [pass/fail] |
| 67 | Large dataset handling | System with 10,000+ books | Search and browsing remain fast | As expected | [pass/fail] |
| 68 | Database query optimization | Complex queries with joins | Queries execute within time limits | As expected | [pass/fail] |

## Integration Testing

| 69 | End-to-end borrowing flow | Complete flow from request to return | All steps work together seamlessly | As expected | [pass/fail] |
| 70 | User creation to book access | New user registration to borrowing | Complete user journey successful | As expected | [pass/fail] |
| 71 | Fine calculation to payment | Overdue book generates fine to payment | Complete fine lifecycle works | As expected | [pass/fail] |

## Error Handling

| 72 | Database connection failure | Simulate DB connection loss | Graceful error handling, user notification | As expected | [pass/fail] |
| 73 | Invalid date input | Enter invalid date format | Proper validation error displayed | As expected | [pass/fail] |
| 74 | Network timeout | Simulate slow network conditions | Appropriate timeout handling | As expected | [pass/fail] |

## Mobile Responsiveness

| 75 | Mobile book search | Search books on mobile device | Interface responsive and functional | As expected | [pass/fail] |
| 76 | Mobile user registration | Complete registration on mobile | Form fields accessible and usable | As expected | [pass/fail] |
| 77 | Mobile admin dashboard | Access admin features on mobile | Dashboard elements properly displayed | As expected | [pass/fail] |

## Backup & Recovery

| 78 | Data backup verification | Create system data backup | All critical data included in backup | As expected | [pass/fail] |
| 79 | Database recovery | Restore from backup after data loss | System restored to previous state | As expected | [pass/fail] |

## Compliance & Standards

| 80 | Accessibility compliance | Test with screen reader | Interface accessible to disabled users | As expected | [pass/fail] |
| 81 | WCAG 2.1 compliance | Check color contrast and navigation | Meets accessibility guidelines | As expected | [pass/fail] |

---

**Total Test Cases: 81**

**Test Categories:**
- Authentication & User Management: 10 cases
- Role-Based Access Control: 5 cases  
- Book Management: 6 cases
- Borrowing System: 9 cases
- Reservation System: 5 cases
- Fine Management: 6 cases
- Membership Management: 4 cases
- Branch & Section Management: 4 cases
- GDPR & Privacy: 3 cases
- Security & Audit: 4 cases
- Admin Dashboard & Reports: 4 cases
- Input Validation & Edge Cases: 5 cases
- Performance & Load Testing: 3 cases
- Integration Testing: 3 cases
- Error Handling: 3 cases
- Mobile Responsiveness: 3 cases
- Backup & Recovery: 2 cases
- Compliance & Standards: 2 cases

**Instructions for Testing:**
1. Execute each test case with the specified input data
2. Record the actual output in the "Actual" column
3. Mark "pass" if expected output matches actual output, "fail" otherwise
4. For failed tests, document the specific issue and steps to reproduce
5. Retest after fixes are implemented
6. Maintain test data consistency across related test cases
