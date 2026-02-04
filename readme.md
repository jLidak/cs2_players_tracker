# CS2 Player Tracker

Aplikacja webowa służąca do zbierania informacji o występach graczy gry Counter Strike 2, by na ich podstawie ułożyć ranking najlepszych graczy. Umożliwia ona:
* Dodawanie i edycja graczy, drużyn, turniejów oraz meczów za pomocą JSON oraz formularzy. Można również załadować wstępną bazę za pomocą jednego przycisku w zakładce "/import-json".
* Dodawanie ocen dla graczy dla danego meczu.
* Dodawanie punktów dla graczy za dany turniej, które odzwierciedlają ich dokonania podczas tego wydarzenia. Punkty te po pomnożeniu przez wagę turnieju, są dodawane do rankingu graczy.

## Technologie

* **Język:** Python 3.12+
* **Framework Webowy:** FastAPI
* **Baza Danych:** SQLite (via SQLAlchemy 2.0)
* **Frontend:** Jinja2 Templates (HTML/CSS)
* **Testy:** Pytest
* **Serwer:** Uvicorn

## Instalacja i Uruchomienie

Upewnij się, że masz zainstalowanego Pythona. Następnie wykonaj w terminalu:

```bash
# Utworzenie środowiska wirtualnego
python -m venv venv

# Aktywacja środowiska 
#   a) Windows
.\venv\Scripts\activate

#   b) (Linux/macOS)
source venv/bin/

# Instalacja zależności
pip install -r requirements.txt

# Uruchomienie serwera
uvicorn main:app --reload

# Uruchomienie testów
pytest
```


## Struktura Projektu

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
├── templates/              # Szablony HTML
├── database.py             # Konfiguracja połączenia z bazą danych
├── main.py                 # Główny punkt wejścia aplikacji
├── models.py               # Modele bazy danych (SQLAlchemy Mapped)
├── schemas.py              # Schematy walidacji danych (Pydantic)
├── test_all.py             # Testy jednostkowe i integracyjne API
└── requirements.txt        # Lista zależności