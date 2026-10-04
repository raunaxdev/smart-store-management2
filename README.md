# 🏪 Raunak's Kirana - Smart Store & Inventory Management System

An AI-powered full-stack inventory management, demand forecasting, and POS billing web application. Designed for retail store operations with real-time cloud sync, automated reorder alerts, and thermal receipt printing.

---

## 🌐 Live Application & Links
* **Live Web Application (Frontend):** [https://raunaxdev.github.io/smart-store-management2/](https://raunaxdev.github.io/smart-store-management2/)
* **Backend REST API Endpoint:** [https://smart-store-management.onrender.com/api](https://smart-store-management.onrender.com/api)
* **API Health Check Status:** [https://smart-store-management.onrender.com/api/health](https://smart-store-management.onrender.com/api/health)
* **📄 Complete Project Documentation (PDF):** [Download Documentation PDF](./Smart_Store_Management_Complete_Documentation.pdf)

---

## ✨ Key Features & Capabilities

1. **🤖 Machine Learning Demand Forecasting:**
   * Calculates 30-day demand projections using **Linear Regression** on historical sales logs (`scikit-learn`).
   * Automatically generates **Critical Reorder** and **Reorder Needed** status badges for low-stock items.

2. **🧾 Quick Sale (POS) & Thermal Bill Generator:**
   * Rapid billing counter interface with instant inventory deduction in PostgreSQL database.
   * Generates a printable thermal receipt modal with billing date, product name, quantity, and total bill calculations.

3. **📖 Customer Udhaar Khata (Credit Register):**
   * Digital ledger to maintain pending customer debts and notes.
   * Real-time calculation and display of total pending debts on the KPI dashboard.

4. **💬 One-Click Supplier Order (WhatsApp Integration):**
   * Pre-fills order details and supplier message via WhatsApp API for items marked under stock deficit.

5. **⚡ Serverless Cloud Synchronization:**
   * Connected to **Neon Cloud PostgreSQL** with connection pooling (`SimpleConnectionPool`) for high-concurrency access.
   * Hosted backend on **Render WSGI (Waitress)** and frontend on **GitHub Pages**.

---

## 🛠️ Tech Stack & Technologies

* **Frontend:** HTML5, Tailwind CSS, Chart.js, FontAwesome, JavaScript (ES6 Asynchronous Fetch)
* **Backend:** Python 3.10+, Flask, Waitress WSGI, Scikit-Learn, Pandas, NumPy
* **Database:** Neon PostgreSQL (Serverless Cloud Database with Connection Pool)
* **Hosting & Deployment:** GitHub Pages (Frontend), Render Web Service (Backend)

---

## 📁 Repository Directory Structure

```text
SmartInventoryAI/
├── index.html                                 # Main Dashboard Interface
├── style.css                                  # Custom Styling & Glassmorphism Tables
├── script.js                                  # Async Fetch & API Event Handlers
├── config.js                                  # Store Branding & UPI Configurations
├── app.py                                     # Flask REST API & ML Forecast Engine
├── requirements.txt                           # Python Dependencies
├── test_extreme.py                            # Automated Load & Stress Testing Suite
├── Smart_Store_Management_Complete_Documentation.pdf # Complete PDF Documentation
├── .gitignore                                 # Git Ignore Rules
└── README.md                                  # Repository Documentation
