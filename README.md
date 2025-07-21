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
cd library-management-system
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

If you have fixture files or want to create some sample data:

```bash
# Create sample data through Django admin or shell
python manage.py shell
```

## 🏃‍♂️ Running the Project

### 1. Start Tailwind CSS Build Process

In one terminal, navigate to the theme directory and start the CSS build:

```bash
cd lms/theme/static_src
npm run dev
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
library-management-system/
├── lms/                          # Main Django project
│   ├── config/                   # Project settings
│   ├── library/                  # Core library app (books, authors, categories)
│   ├── users/                    # User management and authentication
│   ├── borrow/                   # Book borrowing functionality
│   ├── reservations/             # Book reservation system
│   ├── fines/                    # Fine management
│   ├── branches/                 # Library branch management
│   ├── theme/                    # Tailwind CSS theme and templates
│   │   ├── templates/            # Django templates
│   │   ├── static/               # Compiled CSS
│   │   └── static_src/           # Tailwind source files
│   ├── media/                    # Uploaded files (book covers)
│   ├── manage.py                 # Django management script
│   └── requirements.txt          # Python dependencies
├── venv/                         # Virtual environment
└── README.md                     # This file
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `lms/` directory for environment-specific settings:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Database Configuration

The project uses SQLite by default for development. For production, update the `DATABASES` setting in `config/settings.py` to use PostgreSQL or your preferred database.

## 🎨 Customization

### Styling

The project uses Tailwind CSS for styling. To customize the appearance:

1. Edit files in `lms/theme/static_src/src/`
2. The build process will automatically update the CSS
3. Templates are located in `lms/theme/templates/`

### Adding New Features

1. Create new Django apps using `python manage.py startapp <app_name>`
2. Add the app to `INSTALLED_APPS` in settings
3. Create models, views, and templates as needed
4. Run migrations for any new models

## 🧪 Testing

Run the test suite:

```bash
python manage.py test
```

## 📊 User Roles

The system supports different user roles with varying permissions:

- **Member**: Can browse, borrow, and reserve books
- **Librarian**: Can manage books and process borrowing/returns
- **Manager**: Can manage users and generate reports
- **Admin**: Full system access

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 🆘 Troubleshooting

### Common Issues

1. **CSS not updating**: Make sure the Tailwind build process is running (`npm run dev`)
2. **Database errors**: Run `python manage.py migrate` to ensure all migrations are applied
3. **Permission denied**: Make sure you're in the virtual environment and have proper permissions
4. **Node.js errors**: Ensure Node.js and npm are properly installed

### Getting Help

- Check the Django documentation: https://docs.djangoproject.com/
- Tailwind CSS documentation: https://tailwindcss.com/docs
- Open an issue on GitHub for bug reports or feature requests

## 📞 Support

For support, please open an issue on GitHub or contact the development team.

---

**Happy Library Managing! 📚**


