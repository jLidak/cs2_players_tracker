# 🎯 CS2 Player Tracker

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=flat&logo=sqlite)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)
![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)

**Live Demo:** [Link to your deployed app here - e.g., Render/PythonAnywhere]

**CS2 Player Tracker** is a comprehensive, full-stack web application designed to collect, process, and analyze Counter-Strike 2 player performances across custom tournaments. It features a sophisticated, dynamic ranking algorithm that evaluates players based on their match ratings, tournament prestige, and bracket progression.

## ✨ Key Features

* **🏆 Dynamic Global Ranking:** Calculates player standings using a custom mathematical model (combining HLTV 2.0 ratings, phase bonuses, rounds multipliers, and individual tournament weights).
* **🧪 Custom Ranking Simulator:** An interactive sandbox allowing users to tweak core algorithm variables (rating damping, rounds root, base multipliers) and instantly see the simulated impact on the global leaderboard.
* **⚙️ Tournament Management:** Complete administrative control over tournament creation, supporting varying bracket types (8-team, 6-team, 16-team), phase weights, and third-place matches.
* **👥 Player & Team Database:** Full CRUD (Create, Read, Update, Delete) capabilities for teams and players, including detailed statistical drill-downs per participant[cite: 1].
* **🔄 Data Portability:** Built-in JSON import/export functionality for complete database backups, restores, and initial data seeding[cite: 1].
* **🔌 Real-Time Status:** WebSocket integration for live server status and latency monitoring[cite: 1].

## 📸 Screenshots

*(A visual overview of the application's core modules)*

### Global Player Ranking
![Global Player Ranking](assets/ranking_screen.png)

### Custom Ranking Creator (Algorithm Sandbox)
![Custom Ranking Creator](assets/custom_ranking.png)

### Tournament Management & Results Input
![Tournament Details](assets/tournament_details.png)

### Tournament Configuration
![Tournament Creation](assets/tournaments_screen.png)

### Player Points Drill-Down
![Ranking Details](assets/ranking_details_screen.png)

### Database Management
![Import and Export](assets/database_import_and_export.png)

## 🛠️ Technology Stack

* **Backend:** Python 3.12+, FastAPI[cite: 1]
* **Database:** SQLite, SQLAlchemy 2.0 (ORM)[cite: 1]
* **Data Validation:** Pydantic[cite: 1]
* **Frontend:** HTML5, CSS3, Vanilla JavaScript, Jinja2 Templates[cite: 1]
* **Testing:** Pytest (Unit & Integration tests)[cite: 1]
* **Server:** Uvicorn[cite: 1]
* **Code Quality:** Black (Formatter)

## 🚀 Installation & Setup

Ensure you have Python 3.12+ installed on your machine.

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/cs2-player-tracker.git](https://github.com/yourusername/cs2-player-tracker.git)
   cd cs2-player-tracker