# 🏥 SmartCare – Hospital OP Token Management System

## 📌 Project Overview

SmartCare is a web-based Hospital OP Token Management System developed to simplify patient appointment booking and reduce waiting time in hospital queues.

Patients can book appointments, receive OP tokens, track their queue status, and cancel appointments. Administrators can manage patient queues and monitor appointments through an admin dashboard.

## 🎯 Problem Statement

Patients often spend a lot of time waiting in hospital queues to get OP appointments. Manual token management can create confusion, delays, and inconvenience.

SmartCare aims to make this process easier through a digital token management system.

## ✨ Key Features

### Patient Features
- Online appointment booking
- Automatic OP token generation
- QR code generation
- Patient queue tracking
- Estimated waiting time
- Appointment cancellation

### Admin Features
- Secure admin login and logout
- Admin dashboard
- Patient search
- Call next patient
- Complete appointments
- Cancel appointments
- Department-wise queue management
- CSV appointment report download

## 🛠️ Technologies Used

- Python
- Flask
- HTML
- CSS
- JavaScript
- SQLite
- QR Code Generation

## 📂 Project Structure

```text
Smart-Hospital-OP-System/
│
├── app.py
├── database.py
├── requirements.txt
├── README.md
│
├── templates/
│   ├── index.html
│   ├── booking.html
│   ├── dashboard.html
│   ├── admin.html
│   ├── login.html
│   └── track.html
│
└── static/
    ├── style.css
    ├── script.js
    └── qr_codes/
```

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

### 2. Open the project folder

```bash
cd Smart-Hospital-OP-System
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python app.py
```

### 5. Open in your browser

```text
http://127.0.0.1:5001
```

## 🚀 Future Improvements

- Online hospital deployment
- Mobile-friendly interface improvements
- SMS appointment notifications
- Multiple hospital support
- Enhanced security and authentication

## 👩‍💻 Developer

**Jaishree D**

B.Tech – Artificial Intelligence and Data Science

## 📌 Disclaimer

This project is developed for educational and portfolio purposes. It is a prototype and is not currently intended for real hospital operations or handling real patient information.
## 📸 Project Screenshots

## 📸 Project Screenshots

### Home Page
![Home Page](screenshots/home.png)

### Appointment Booking
![Booking Page](screenshots/booking.png)

### Admin Dashboard
![Admin Dashboard](screenshots/admin.png)

### Patient Tracking
![Patient Tracking](screenshots/tracking.png)