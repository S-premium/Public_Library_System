# Public Library Management System (LMS) - Core Application

This contains the core web application for our capstone project: Preventing Data Breaches and Record Inaccuracies in Public Libraries Through a Cybersecurity-Enhanced Management System.

This focuses strictly on the system architecture, application features, backend logic, and frontend interface.

## System Overview & Purpose:
Many of the local public libraries still rely on manual logbooks or outdated, unmaintained systems. This leads to misplaced book tracking, data entry errors, and open vulnerabilities where user information can be leaked or modified.

Our system bridges this gap by creating a secure, automated web application. It handles everyday library tasks—like cataloging books, checking availability, and processing loans, while embedding security checks directly into the code. The goal is to move the pilot library in Iloilo away from vulnerable paper processes into a secure, digital workflow.

## Key System Features:

We structured the application around the CIA Triad to balance smooth library operations with strong defense mechanisms:

### User Access & Defense (Confidentiality)
*Role-Based Dashboards: Custom views and permissions depending on who logs in (Admin, Librarian, or Borrower).

*Bot Protection: Built-in CAPTCHA validation on the login form to stop automated brute-force attacks.

*Two-Factor Checks: Multi-Factor Authentication (MFA) via a email One-Time Password (OTP) for high-level staff actions.

*Session Control: Active session tracking that automatically logs users out after inactivity to prevent unauthorized physical terminal access.

## Operational Automation (Integrity)

*Input Sanitation: Every text field runs through validation rules to block malicious SQL Injection payloads.
	
*Real-Time Status Tracking: Dynamic status updates for books (Available, Borrowed, Reserved, Room-Use-Only, Lost, or Damaged).

*Policy Automation: The backend automatically calculates due dates, tracks overdue penalties, and blocks non-circulating, government-purchased books from leaving the library without staff intervention.

## Logging & Visibility (Availability):

*Live Audit Trail: A read-only logger that captures every major system event (e.g., who approved a loan, when a status changed) to ensure internal accountability.

## Language & Tech Stack:

*Backend Logic: Python 3.x using the Flask web framework (chosen for its lightweight routing and quick database integration).

*Frontend Interface: HTML5, CSS3, and JavaScript, styled with the Bootstrap framework for a clean, responsive UI.

*Libraries used: Packages for password cryptography (hashing handles), secure session creation, and handling mail functions for OTP delivery.


## How to Set Up and Run the Application:

### Prerequisites:
*Make sure you have Python (version 3.8 or higher) installed
*You need XAMPP to run the host of the local base server (SQL database configuration file is handled in our separate database repository)

### Installation Steps:

##Clone the application repository:##
   git clone [https://github.com/S-premium/Public_Library_System.git](https://github.com/S-premium/Public_Library_System.git)
   cd Public_Library_System

##Set up a Python virtual environment (recommended):
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate

##Install the application dependencies:
pip install -r requirements.txt

##Connect the Environment Settings:
*Look for the system configuration file (like config.py or a .env template).

*Ensure the database URI points correctly to your local XAMPP MySQL setup (typically localhost with your custom DB name).

##Run the Flask Server:
flask run

##Interact with the System:
*Open your web browser and go to: http://127.0.0.1:5000/
*You can now test the interface using the default login credentials provided in our testing documentation (or create a new student/borrower account directly from the signup page).

