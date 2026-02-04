# CS2 Player Tracker

Aplikacja webowa typu **Player Tracker** służąca do zarządzania danymi o profesjonalnych graczach, drużynach, turniejach i meczach w grze Counter-Strike 2. System umożliwia obliczanie rankingu graczy na podstawie ich wyników oraz oferuje interfejs webowy i pełne REST API.

## 📋 Opis Projektu

Projekt został zrealizowany w ramach zaliczenia przedmiotu, zgodnie z następującymi wytycznymi:
1. **Backend:** Wykonany w **FastAPI** z wykorzystaniem **SQLAlchemy** (baza SQLite). Obsługuje pełne operacje **CRUD** (Create, Read, Update, Delete).
2. **WebSocket:** Asynchroniczny kanał komunikacji zwracający status serwera oraz aktualny czas w czasie rzeczywistym.
3. **Środowisko:** Projekt przygotowany do uruchomienia w wirtualnym środowisku Python (`venv`), posiada plik `requirements.txt`.
4. **Jakość kodu:** Wszystkie funkcje i klasy posiadają **Type Annotations** (adnotacje typów) oraz **Docstrings** (dokumentację).
5. **Testy:** Zaimplementowane testy jednostkowe z wykorzystaniem pakietu **pytest**.

## 🛠️ Technologie

* **Język:** Python 3.12+
* **Framework Webowy:** FastAPI
* **Baza Danych:** SQLite (via SQLAlchemy 2.0)
* **Walidacja Danych:** Pydantic
* **Frontend:** Jinja2 Templates (HTML/CSS)
* **Testy:** Pytest
* **Serwer:** Uvicorn

## 🚀 Instalacja i Uruchomienie

### 1. Klonowanie i przygotowanie środowiska
Upewnij się, że masz zainstalowanego Pythona. Następnie wykonaj w terminalu:

```bash
# Utworzenie środowiska wirtualnego
python -m venv venv

# Aktywacja środowiska (Windows)
.\venv\Scripts\activate

# Aktywacja środowiska (Linux/macOS)
source venv/bin/

# Uruchomienie serwera
uvicorn main:app --reload
```

## 📂 Struktura Projektu

Struktura plików oparta na podziale na routery i moduły logiczne:

```text
projekt/
├── json_import_files/      # Pliki JSON do wstępnego zasilenia bazy (import)
├── routers/                # Logika endpointów API (podział na moduły)
│   ├── data_ops.py         # Import/Export, operacje masowe
│   ├── matches.py          # Obsługa meczów i ocen
│   ├── players.py          # CRUD graczy, wyszukiwanie
│   ├── ranking.py          # Algorytm obliczania rankingu
│   ├── teams.py            # CRUD drużyn
│   ├── tournaments.py      # CRUD turniejów
│   ├── views.py            # Widoki HTML (Jinja2)
│   └── websocket.py        # Obsługa WebSocket (status serwera)
├── static/                 # Pliki statyczne (CSS, obrazy)
├── templates/              # Szablony HTML (Jinja2)
├── database.py             # Konfiguracja połączenia z bazą danych
├── main.py                 # Główny punkt wejścia aplikacji
├── models.py               # Modele bazy danych (SQLAlchemy Mapped)
├── schemas.py              # Schematy walidacji danych (Pydantic)
├── test_all.py             # Testy jednostkowe i integracyjne API
└── requirements.txt        # Lista zależności