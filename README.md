SecureNotes Web Application

Description
SecureNotes is a Flask based web application that allows users to register, log in, and securely manage personal notes. Each user can create, view, and manage their own notes stored in a MySQL database. The system focuses on authentication, access control, and secure data handling.

Features
• User registration and login
• Password hashing using Flask Bcrypt
• Session based authentication
• Create and view personal notes
• Notes are isolated per user
• MySQL database backend
• Modular Flask structure using Blueprints
• HTML templates rendered with Jinja2

Tech Stack
• Python
• Flask
• Flask Bcrypt
• MySQL
• HTML
• Git and GitHub

Project Structure
app.py
Main Flask application entry point.

db.py
Database connection logic.

auth/
Authentication module.
Handles login, registration, and logout routes.

notes/
Notes module.
Handles creating, listing, and viewing notes.

templates/
HTML templates for all pages.

venv/
Python virtual environment. Not tracked in Git.

Setup Instructions

Clone repository
git clone https://github.com/YOUR_USERNAME/securenotes-flask.git

Create virtual environment
python -m venv venv

Activate virtual environment
Windows
venv\Scripts\activate

Install dependencies
pip install flask flask-bcrypt mysql-connector-python

Configure database
Create a MySQL database named securenotes.
Create required tables for users and notes.

Run application
python app.py

Open browser
http://127.0.0.1:5000

Security Notes
• Passwords are stored as bcrypt hashes
• Sessions use a secret key
• Users can only access their own notes
• SQL queries use parameterized statements

Academic Context
This project is developed as part of a Final Year Project for a Cyber Security degree. It demonstrates secure web application design, authentication mechanisms, and database access control.