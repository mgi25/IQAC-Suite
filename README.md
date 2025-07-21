# IQAC-Suite

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Contributors](https://img.shields.io/github/contributors/CHRISTInfotech/IQAC-Suite)
![License](https://img.shields.io/github/license/CHRISTInfotech/IQAC-Suite)
![Last Commit](https://img.shields.io/github/last-commit/CHRISTInfotech/IQAC-Suite)

**IQAC-Suite** is a comprehensive web-based application built using Django to streamline Internal Quality Assurance Cell (IQAC) processes within academic institutions. It digitizes workflows like event proposals, report generation, and media/content requests (CDL), aligning with NAAC/NBA quality benchmarks. Alongside, it also helps in keeping track of the student performance data in order to generate a graduate transcript during graduation. 

---

## Table of Contents

- [Key Features](#key-features)
- [System Overview](#system-overview)
- [Technology Stack](#technology-stack)
- [Installation Guide](#installation-guide)
- [Modules](#modules)
- [Usage Flow](#usage-flow)
- [Visual Overview](#visual-overview)
- [UI and Animation](#ui-and-animation)
- [Security](#security)
- [Roadmap](#roadmap)
- [Contribution](#contribution)
- [License](#license)
- [Contact](#contact)

---

## Key Features

- Role-based login system (Admin, Faculty, Coordinator)
- Multi-page event proposal form with attachments
- IQAC report generation with word limit validation
- Status tracking and reviewer comments
- CDL (Content Development Lab) request module
- Graduate Attribute Script
- Notification panel with visual indicators
- Dashboard with statistics and filters
- Fully responsive and mobile-optimized

---

## System Overview

```
Browser (HTML/CSS/JS)
        ↓
   Django Views & Templates
        ↓
     Django Models & ORM
        ↓
Database (SQLite / PostgreSQL)
```

---

## Technology Stack

### Backend  
![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2.3-green?logo=django&logoColor=white)

### Frontend  
![HTML5](https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black)

### Database  
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)

### Tools  
![Git](https://img.shields.io/badge/Git-F05032?logo=git&logoColor=white)
![Virtualenv](https://img.shields.io/badge/Virtualenv-20C997?logo=python&logoColor=white)
![WeasyPrint](https://img.shields.io/badge/WeasyPrint-F23030?logo=python&logoColor=white)
![Crispy Forms](https://img.shields.io/badge/Django--Crispy--Forms-FF9900?logo=django&logoColor=white)
![Dotenv](https://img.shields.io/badge/Python--Dotenv-FFD43B?logo=python&logoColor=black)

---

## Installation Guide

### 1. Prerequisites

- Python 3.10+
- pip, git, virtualenv
- PostgreSQL (optional for production)

### 2. Clone and Set Up

```bash
git clone https://github.com/CHRISTInfotech/IQAC-Suite.git
cd IQAC-Suite
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the root directory:

```
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=127.0.0.1,localhost
```

### 4. Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser

```bash
python manage.py createsuperuser
```

### 6. Collect Static Files

```bash
python manage.py collectstatic
```

### 7. Run the Development Server

```bash
python manage.py runserver
```

Access at: `http://127.0.0.1:8000/`

---

## Modules

| App/Module  | Description                                                |
|-------------|------------------------------------------------------------|
| `emt`       | Event Management and Tracking                              |
| `cdl`       | Content Development Lab (media requests)                   |
| `accounts`  | Authentication and user profile management                 |
| `core-admin`| Admin views for overseeing reports and submissions         |
| `templates` | HTML files with base layouts and includes                  |
| `static`    | CSS, JavaScript, and image assets                          |

---

## User Functionalities

IQAC-Suite follows a **role-based access control model**, ensuring each user only sees relevant features for their role. Below is a detailed breakdown of functionalities for each type of user in the system.

---

### Faculty / Event Coordinator

> Primary users responsible for creating and managing event proposals.

- Submit new **Event Proposals** via a multi-step form
- Upload necessary documents:
  - Event Invitation
  - Brochure
  - Attendance Sheet
  - Event Report
- View and track proposal status:
  - Pending → Under Review → Approved/Rejected
- Respond to reviewer feedback and edit submissions
- Generate and export **IQAC Reports** for completed events
- Submit **CDL (Media)** requests for banners, posters, or content
- Receive real-time notifications via the dashboard

---

### Head of Department (HOD) / Reviewer

> Departmental reviewer responsible for evaluating submissions.

- View proposals submitted by faculty under the department
- Provide review feedback, approve, or reject proposals
- Forward approved proposals to IQAC Admin
- Monitor department events and proposal statuses
- Access archive of past events and reports

---

### IQAC Admin

> Core admin responsible for quality control and documentation.

- Access and manage all submitted proposals across departments
- Review, approve, or reject proposals at final stage
- Leave reviewer feedback visible to submitters
- Generate consolidated **IQAC reports** (PDF & HTML)
- Manage deadlines and reporting periods
- Access analytics dashboard and proposal statistics
- Moderate CDL submissions and feedback

---

### CDL Coordinator / Media Team

> Content team responsible for design/media creation and tracking.

- Access all **media/content requests** via CDL module
- Change status of requests: Submitted → In Progress → Completed
- Upload final assets (banners, posters, videos, etc.)
- Provide clarifications or request additional input
- Maintain task history and approval trail

---

### System Administrator (Superuser)

> Full backend access with administrative privileges.

- Access Django Admin Panel
- Add, modify, or deactivate users and roles
- Configure platform-wide settings and deadlines
- Manage static files and uploaded media
- Monitor database and logs
- Enable or disable modules/features as needed

---

Each role has been designed to ensure:
- **Clarity of workflow**
- **Security and data integrity**
- **Seamless collaboration** between academic and media teams

To test multiple roles locally, create accounts and assign roles via the Django Admin Panel (`/admin`).

---

## Usage Flow

1. User logs in based on role.
2. Faculty submits an event proposal via a dynamic multi-page form.
3. Proposal is reviewed by Coordinator, HOD, and IQAC Admin.
4. Documents are uploaded (invitation, report, attendance, etc.).
5. After approval, user generates an IQAC report.
6. CDL requests (media/content) are submitted and reviewed.
7. Admins manage all records, filter submissions, and track pending items.

---

## Visual Overview

### Project Stats Table

| Module                | Total Submissions | Approved | Rejected |
|-----------------------|-------------------|----------|----------|
| Event Proposals       | 128               | 102      | 12       |
| IQAC Reports          | 64                | 64       | 0        |
| CDL Requests          | 45                | 32       | 3        |

### Dashboard Sample (Chart Placeholder)

To display charts on the live dashboard, use Chart.js or static images.

```
[Pie chart / Bar chart]
 - Submitted vs Approved Events
 - Report completion status
 - Request distribution by department
```

---

## UI and Animation

- **Page Transitions**: Smooth fade-in using keyframes (`fadeSlideUp`)
- **Button Effects**: Hover transitions and click scaling
- **Notification Bell**: Pulse animation for unread status
- **Responsive Grid**: Flexbox layout for cards and containers
- **Glassmorphism**: Translucent panels using blur + semi-opacity

Animations are CSS-based and performance-friendly. Compatible with all major browsers.

---

## Security

- CSRF protection enabled on all forms
- File upload type and size restrictions
- Role-based access using decorators and middleware
- User session timeout and logout functionality
- Environment isolation using `.env` file

---

## Roadmap

```
[x] Multi-page Event Proposal Form
[x] IQAC Report Export as PDF
[x] Media/CDL Request Workflow
[ ] Audit Trail Logging
[ ] NAAC/NBA Auto-Format Compliance
[ ] Mobile App Integration via API
[ ] Admin Analytics Dashboard (interactive charts)
```

---

## Contribution

Contributions are welcome from the open-source and academic community.

1. Fork the repository
2. Create a new branch (`feature/your-feature`)
3. Commit and push your changes
4. Submit a pull request

Please follow coding conventions and include test data or UI screenshots where applicable.

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](./LICENSE) file for more details.

---

## Contact

**CHRIST (Deemed to be University)**  
Pune Lavasa Campus – Infotech R&D Team  
Email: infotech.lavasa@christuniversity.in  
GitHub: [CHRISTInfotech](https://github.com/CHRISTInfotech)  
Website: https://christuniversity.in/lavasa

---

## Disclaimer

This software is intended for educational and institutional use within CHRIST University. Distribution, modification, or deployment outside this scope should be authorized by the R&D administrators.