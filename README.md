# 🏎️ F1 Live Dashboard

## 📌 Project Overview
F1 Live Dashboard is an advanced **Formula 1 data visualization tool** built using **Streamlit, SQLite, and FastAPI**. It enables **race analysis, telemetry tracking, lap time comparisons, weather impact assessments**, and much more! This dashboard does not provide live updates but instead offers analytics of past events, which are updated with each new race.

---

## 🚀 Features
- 📊 **Race Results & Performance Analysis**
- ⏱️ **Lap Time Comparisons & Stint Analysis**
- 🏁 **Track-Specific Insights**
- 🔄 **Strategy & Pit Stop Evaluations**
- 🔧 **Fuel Load & Tire Degradation Models**
- 📍 **Track Position Evolution**

---

## ⚙️ Installation & Setup
### **1️⃣ Prerequisites**
- **Python 3.8+**
- **Docker & Docker Compose** (optional for containerized setup)
- **SQLite Database** (preloaded with F1 data)

### **2️⃣ Clone the Repository**
```sh
git clone https://github.com/yourusername/f1-live-dashboard.git
cd f1-live-dashboard
```

### **3️⃣ Setup Virtual Environment & Install Dependencies**
```sh
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

### **4️⃣ Configure Environment Variables**
Create a `.env` file in the root directory and add the following:
```ini
SQLITE_DB_PATH=database/f1data.db
FASTF1_CACHE_DIR=cache/
LOG_LEVEL=INFO
LOG_FILE=f1dashboard.log
```

---

## 🏁 Running the Application
### **Start Backend (FastAPI Server)**
```sh
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
Access API docs at: [http://localhost:8000/docs](http://localhost:8000/docs)

### **Start Frontend (Streamlit Dashboard)**
```sh
streamlit run frontend/app.py
```

---

## 🐳 Docker Deployment
For running the project in **Docker**, use the following:
```sh
docker-compose up --build
```
This will launch **both backend (FastAPI) and frontend (Streamlit)**.

---

## 🔥 Usage Guide
### **📊 Viewing Race Results**
Navigate to the **Race Results** section to analyze historical race data.

### **🏎️ Strategy Comparison**
Use the **Strategy & Pit Stop Analysis** to evaluate the effectiveness of different race strategies.

### **📍 Track Position Evolution**
Analyze how drivers performed across different sections of the track in **Track Position Evolution**.

---

## 🛠️ Development & Contribution
1. Fork the repository
2. Create a new branch (`git checkout -b feature-name`)
3. Make your changes and commit (`git commit -m "Added feature XYZ"`)
4. Push to your fork (`git push origin feature-name`)
5. Open a pull request

---

## 📜 License
At this time, this project is not open for public sharing. However, in the future, it will be licensed under a model that allows copying and usage **with attribution to the author**.

---

## 📢 Notice
This repo is **unofficial** and are not associated in any way with the **Formula 1 companies**. **F1, FORMULA ONE, FORMULA 1, FIA FORMULA ONE WORLD CHAMPIONSHIP, GRAND PRIX** and related marks are **trademarks of Formula One Licensing B.V.**

### **Data Source**
This dashboard relies on **FastF1** for historical Formula 1 data. Special thanks to [FastF1](https://github.com/theOehrly/Fast-F1) for their open-source contribution to F1 data analysis.

---

## ✉️ Contact
For questions or support, open an issue or reach out via email: **juliya.legkaya@gmail.com**

Happy Racing! 🏁🚗💨