# Library Management System (LibSys)

A comprehensive web-based Library Management System built with Django and Tailwind CSS. This system allows libraries to manage their books, users, borrowing processes, reservations, and fines efficiently.

## 🚀 Features

### Core Functionality
- **Book Management**: Add, edit, delete, and search books with cover images
- **User Management**: Different user roles (Member, Librarian, Manager, Admin)
- **Borrowing System**: Track book loans with due dates and extensions
- **Reservation System**: Allow users to reserve books (Regular and Priority reservations)
- **Fine Management**: Automatic calculation and tracking of overdue fines
- **Branch Management**: Multi-branch library support
- **Category & Author Management**: Organize books by categories and authors

### User Features
- User authentication and registration
- Book search and browsing
- Borrowing history
- Reservation management
- Profile management

### Admin Features
- Dashboard with system overview
- User role management
- Book inventory management
- Borrowing and reservation oversight
- Fine collection and management

## 🛠️ Tech Stack

- **Backend**: Django 5.2.4 (Python)
- **Frontend**: HTML, Tailwind CSS, HTMX
- **Database**: SQLite (Development), PostgreSQL ready
- **Styling**: Tailwind CSS with custom theme
- **Authentication**: Django's built-in authentication with custom User model
- **File Uploads**: Django's file handling for book covers
- **Build Tools**: Node.js, npm for Tailwind CSS compilation

## 📋 Prerequisites

Before running this project, make sure you have the following installed:

- Python 3.8 or higher
- Node.js and npm (for Tailwind CSS)
- Git

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Libsys
```

### 2. Set Up Python Virtual Environment

#### On Windows:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate
```

#### On macOS/Linux:
```bash
# Create virtual environment (use python3 if python points to Python 2.x)
python3 -m venv venv
# or
python -m venv venv

# Activate virtual environment
source venv/bin/activate
```

#### Alternative Linux methods:
```bash
# Using virtualenv (if installed)
sudo apt-get install python3-venv  # Ubuntu/Debian
virtualenv venv
source venv/bin/activate

# Or using conda (if Anaconda/Miniconda is installed)
conda create -n library-management python=3.8
conda activate library-management
```

### 3. Install Python Dependencies

```bash
cd lms
pip install -r requirements.txt
```

### 4. Set Up Tailwind CSS

```bash
cd theme/static_src
npm install
```

### 5. Database Setup

```bash
# Navigate back to the main Django directory
cd ..

# Run migrations to set up the database
python manage.py makemigrations
python manage.py migrate

# Create a superuser account
python manage.py createsuperuser
```

### 6. Load Initial Data (Optional)


```bash
# Load initial data
python manage.py loaddata initial_data.json
```

## 🏃‍♂️ Running the Project

### 1. Start Tailwind CSS Build Process

In one terminal, navigate to root project directory and start the CSS build:

```bash
python mangae.py tailwind start
```

This will watch for changes and rebuild your CSS automatically.

### 2. Start Django Development Server

In another terminal, run the Django server:

```bash
cd lms
python manage.py runserver
```

The application will be available at: `http://127.0.0.1:8000/`

### 3. Access Admin Panel

Visit `http://127.0.0.1:8000/admin/` and log in with the superuser credentials you created.

## 📁 Project Structure

```
Libsys/
├── lms/                          # Main Django project
│   ├── admin_dashboard/          # Admin dashboard app
│   ├── borrow/                   # Book borrowing functionality
│   ├── branches/                 # Library branch management
│   ├── config/                   # Project settings
│   ├── fines/                    # Fine management
│   ├── library/                  # Core library app (books, authors, categories)
│   │   ├── fixtures/             # Initial data fixtures
│   │   └── templates/            # Library templates
│   ├── media/                    # Uploaded files (book covers, etc.)
│   ├── reservations/             # Book reservation system
│   ├── theme/                    # Tailwind CSS theme and templates
│   │   ├── static/               # Compiled CSS
│   │   ├── static_src/           # Tailwind source files
│   │   └── templates/            # Theme templates
│   ├── users/                    # User management and authentication
│   ├── manage.py                 # Django management script
│   └── requirements.txt          # Python dependencies
├── venv/                         # Virtual environment
├── .gitignore                    # Git ignore rules
├── README.md                     # Project documentation
```

## 🔧 Configuration



### Database Configuration

The project uses SQLite by default for development. For production, update the `DATABASES` setting in `config/settings.py` to use PostgreSQL or your preferred database.

## 🎨 Customization

### Styling

The project uses Tailwind CSS for styling. To customize the appearance:

1. Edit files in `lms/theme/static_src/src/`
2. The build process will automatically update the CSS
3. Templates are located in `lms/theme/templates/`



## 🧪 Testing

Run the test suite:

```bash
python manage.py test
```

### Test User Credentials

After loading the initial data (`python manage.py loaddata initial_data.json`), you can use these pre-configured test accounts:

| Username      | Email                    | Password | Role      | Description                                    |
|---------------|--------------------------|----------|-----------|------------------------------------------------|
| admin         | admin@test.com           | password | admin     | Super admin with full system access           |
| manager       | manager@test.com         | password | manager   | Library manager - user management & reports   |
| librarian     | librarian@test.com       | password | librarian | Librarian - book management & borrowing       |
| member        | member@test.com          | password | member    | Basic member with Basic membership            |
| john_doe      | john.doe@test.com        | password | member    | Premium member (John Doe)                     |
| sarah_student | sarah.student@test.com   | password | member    | Student member (Sarah Student)                |

**Note:** All test users use the password `password` for easy testing. Remember to change these credentials in production!

## 📊 User Roles

The system supports different user roles with varying permissions:

- **Member**: Can browse, borrow, and reserve books
- **Librarian**: Can manage books and process borrowing/returns
- **Manager**: Can manage users and generate reports
- **Admin**: Full system access



## 🆘 Troubleshooting

### Common Issues

1. **CSS not updating**: Make sure the Tailwind build process is running (`npm run dev`)
2. **Database errors**: Run `python manage.py migrate` to ensure all migrations are applied
3. **Permission denied**: Make sure you're in the virtual environment and have proper permissions
4. **Node.js errors**: Ensure Node.js and npm are properly installed
5. **Npm path error**: You may need to adjust the NPM path in settings depending on the operating system you have, the path is different for windows and mac/linux

## 👥 Made By

This Library Management System was developed by:

- **Abdul Shameeu** - 23081531
- **Shaif Abdul Raheem** - 24019751  
- **Mohamed Wildhan Waheed** - 24019747
- **Ahmed Moustafa** - 24033404

---








