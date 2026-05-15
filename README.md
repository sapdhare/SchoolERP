# School ERP System

Production-ready multi-school ERP SaaS platform built using Flask, SQL Server, Bootstrap and modern admin architecture.

---

# Overview

School ERP System is a centralized multi-school management platform designed to automate and manage complete school administration workflows.

The system supports:

* Multi-school architecture
* Student lifecycle management
* Transfer Certificate generation
* Bonafide certificate generation
* Subscription & SaaS management
* Branding & theme customization
* Backup & restore automation
* Role-based authentication
* Payment integration
* Maintenance & security controls

The project is designed with scalable SaaS architecture and production-level ERP concepts.

---

# Core Features

## Super Admin Panel

### School Management

* Add/Edit/Delete schools
* School branding support
* School activation controls
* School configuration management

### User Management

* Admin & Clerk management
* Role-based authentication
* Password security
* User status controls

### Branding System

* Dynamic ERP color branding
* Button theme customization
* Favicon support
* ERP version control
* Footer branding
* Website URL management

### Backup & Recovery

* Manual SQL backups
* Automatic scheduled backups
* Download backup files
* Restore database backups
* Auto cleanup old backups
* Backup logs & history

### Subscription Management

* Trial period controls
* Grace period management
* SaaS plan controls
* Subscription status tracking

### SMTP & Notifications

* SMTP configuration
* Email integration
* Password reset OTP system

### Security Controls

* CSRF protection
* Session protection
* Password hashing
* Login protection
* Secure database queries

### Maintenance Mode

* Global ERP maintenance switch
* Maintenance message system
* System protection controls

---

# Clerk Panel Features

## Student Management

* Add students
* Edit student details
* Search students
* Filter students
* Student profile management

## Transfer Certificate (TC)

* Generate TCs
* Dynamic TC numbering
* PDF generation
* School-wise TC tracking

## Bonafide Certificates

* Generate bonafide certificates
* Dynamic numbering
* PDF support

## Excel Operations

* Import students via Excel
* Export students via Excel
* Bulk data handling

## PDF Generation

* Professional PDF generation
* School branding support
* Download & print support

---

# SaaS Architecture Features

* Multi-school database architecture
* Dynamic global settings
* School-level isolation
* Subscription lifecycle handling
* Branding engine
* ERP customization layer

---

# Tech Stack

## Backend

* Python
* Flask

## Frontend

* HTML5
* CSS3
* JavaScript
* Bootstrap

## Database

* Microsoft SQL Server

## Libraries & Tools

* PyODBC
* Pandas
* OpenPyXL
* Flask-WTF
* Flask-Bcrypt
* APScheduler
* Razorpay SDK
* PDFKit

---

# Security Features

* CSRF Protection
* Password Hashing
* Secure Session Handling
* SQL Injection Protection
* File Validation
* Secure Admin Routes

---

# Project Structure

```text
STUDENT_ERP_SYSTEM/
│
├── app.py
├── config.py
├── db.py
├── requirements.txt
├── README.md
├── setup.sql
├── .gitignore
├── .env
│
├── templates/
├── static/
├── backups/
├── pdf/
├── history/
```

---

# Installation Guide

## 1. Clone Repository

```bash
git clone <repository_url>
cd STUDENT_ERP_SYSTEM
```

---

## 2. Create Virtual Environment

```bash
python -m venv venv
```

---

## 3. Activate Virtual Environment

### Windows

```bash
venv\Scripts\activate
```

---

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create a `.env` file in project root.

Example:

```env
SECRET_KEY=your_secret_key

DB_SERVER=localhost\SQLEXPRESS
DB_DATABASE=SchoolERP

MAIL_USERNAME=your_email
MAIL_PASSWORD=your_password

RAZORPAY_KEY_ID=your_key
RAZORPAY_KEY_SECRET=your_secret
```

---

# Database Setup

## Option 1 — Using setup.sql

Run:

```sql
setup.sql
```

inside SQL Server Management Studio.

---

# Running Application

Start Flask server:

```bash
python app.py
```

Application URL:

```text
http://127.0.0.1:5000
```

---

# Backup System

The ERP includes enterprise-level backup management.

Features:

* Manual backup creation
* Automatic scheduled backups
* Backup download
* Backup restore
* Backup cleanup automation

Backup files are stored in:

```text
/backups
```

---

# Scheduler System

Automatic scheduler handles:

* Auto backup creation
* Cleanup old backups
* SaaS automation tasks

Powered using:

* APScheduler

---

# Default ERP Modules

## Super Admin

* Dashboard
* Schools
* Users
* Settings
* Branding
* Backup
* Maintenance
* SMTP
* Subscription
* Security

## Clerk

* Students
* Add Student
* TC Management
* Bonafide Management
* Import/Export

---

# Production Notes

Before deployment:

* Configure `.env`
* Configure SQL Server
* Configure SMTP
* Configure Razorpay keys
* Enable HTTPS in production
* Protect admin routes
* Schedule backups properly

---

# Git Ignore Recommendations

The following files/folders should not be uploaded:

```gitignore
venv/
__pycache__/
.history/
backups/
.env
```

---

# Future Scope

* Attendance management
* Fees management
* Parent portal
* Student login
* AI analytics dashboard
* Mobile application
* Cloud deployment
* Multi-tenant SaaS scaling

---

# Author

Developed by:
Prajwal Dahane

ERP SaaS Architecture Project

 
 
