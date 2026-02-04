"""
Testy jednostkowe dla aplikacji CS2 Player Tracker.
Zgodne z metodologią pytest ze skryptu laboratoryjnego.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from main import app
import models

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# ==================== TEAMS TESTS ====================

def test_create_team():
    """Test tworzenia nowej drużyny."""
    response = client.post(
        "/api/teams/",
        json={"name": "Team Liquid", "logo_url": "https://example.com/liquid.png"}
    )
    # Dodano komunikaty po przecinku, zgodnie ze stylem w skrypcie lab.
    assert response.status_code == 200, f"Oczekiwano statusu 200, otrzymano {response.status_code}"
    data = response.json()
    assert data["name"] == "Team Liquid", "Nazwa drużyny nie zgadza się z przesłaną"
    assert "id" in data, "Odpowiedź powinna zawierać ID"

def test_get_teams():
    """Test pobierania listy drużyn."""
    client.post("/api/teams/", json={"name": "Navi"})
    client.post("/api/teams/", json={"name": "Vitality"})

    response = client.get("/api/teams/")
    assert response.status_code == 200, "Błąd pobierania listy drużyn"
    data = response.json()
    assert len(data) == 2, f"Oczekiwano 2 drużyn, otrzymano {len(data)}"

def test_delete_team():
    """Test usuwania drużyny."""
    create_response = client.post("/api/teams/", json={"name": "FaZe"})
    team_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/teams/{team_id}")
    assert delete_response.status_code == 200, "Błąd podczas usuwania drużyny"

    get_response = client.get(f"/api/teams/{team_id}")
    assert get_response.status_code == 404, "Usunięta drużyna nadal istnieje (powinno być 404)"

# ==================== PLAYERS TESTS ====================

def test_create_player():
    """Test tworzenia nowego gracza."""
    team_response = client.post("/api/teams/", json={"name": "FaZe"})
    team_id = team_response.json()["id"]

    response = client.post(
        "/api/players/",
        json={
            "nickname": "s1mple",
            "photo_url": "https://example.com/s1mple.jpg",
            "team_id": team_id
        }
    )
    assert response.status_code == 200, "Nie udało się utworzyć gracza"
    data = response.json()
    assert data["nickname"] == "s1mple", "Błędny nick gracza"
    assert data["team_id"] == team_id, "Gracz przypisany do złej drużyny"

def test_get_players():
    """Test pobierania listy graczy."""
    client.post("/api/players/", json={"nickname": "ZywOo"})
    client.post("/api/players/", json={"nickname": "donk"})

    response = client.get("/api/players/")
    assert response.status_code == 200, "Błąd pobierania graczy"
    data = response.json()
    assert len(data) == 2, "Oczekiwano 2 graczy"

# ==================== TOURNAMENTS TESTS ====================

def test_create_tournament():
    """Test tworzenia nowego turnieju."""
    response = client.post(
        "/api/tournaments/",
        json={"name": "IEM Katowice 2024", "weight": 2.0}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "IEM Katowice 2024"
    assert data["weight"] == 2.0

def test_get_tournaments():
    """Test pobierania listy turniejów."""
    client.post("/api/tournaments/", json={"name": "Major", "weight": 2.5})
    client.post("/api/tournaments/", json={"name": "Minor", "weight": 0.5})

    response = client.get("/api/tournaments/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

# ==================== MATCHES TESTS ====================

def test_create_match():
    """Test tworzenia nowego meczu."""
    team1 = client.post("/api/teams/", json={"name": "Navi"}).json()
    team2 = client.post("/api/teams/", json={"name": "Vitality"}).json()
    tournament = client.post("/api/tournaments/", json={"name": "Major", "weight": 2.0}).json()

    response = client.post(
        "/api/matches/",
        json={
            "tournament_id": tournament["id"],
            "phase": "Final",
            "date": "2024-01-15",
            "format": "BO5",
            "team1_id": team1["id"],
            "team2_id": team2["id"],
            "result": "3:2"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "Final"
    assert data["result"] == "3:2"

def test_get_matches():
    """Test pobierania listy meczów."""
    team1 = client.post("/api/teams/", json={"name": "Navi"}).json()
    team2 = client.post("/api/teams/", json={"name": "Vitality"}).json()
    tournament = client.post("/api/tournaments/", json={"name": "Major", "weight": 2.0}).json()

    client.post(
        "/api/matches/",
        json={
            "tournament_id": tournament["id"],
            "phase": "Group",
            "date": "2024-01-10",
            "format": "BO3",
            "team1_id": team1["id"],
            "team2_id": team2["id"]
        }
    )

    response = client.get("/api/matches/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "tournament" in data[0]

# ==================== RANKING TEST ====================

def test_ranking_calculation():
    """Test obliczania rankingu graczy."""
    player = client.post("/api/players/", json={"nickname": "jL"}).json()
    tournament1 = client.post("/api/tournaments/", json={"name": "Major", "weight": 1.0}).json()
    tournament2 = client.post("/api/tournaments/", json={"name": "PGL", "weight": 0.5}).json()

    # Bezpośrednie dodanie do bazy (setup testowy)
    db = next(override_get_db())
    db.add(models.PlayerRankingPoint(
        player_id=player["id"],
        tournament_id=tournament1["id"],
        points=100.0
    ))
    db.add(models.PlayerRankingPoint(
        player_id=player["id"],
        tournament_id=tournament2["id"],
        points=50.0
    ))
    db.commit()

    response = client.get("/api/ranking/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["total_points"] == 125.0, "Błędne obliczenie punktów rankingu"

# ==================== EXPORT/IMPORT TESTS ====================

def test_export_database():
    """Test eksportu bazy danych."""
    client.post("/api/teams/", json={"name": "Navi"})
    client.post("/api/players/", json={"nickname": "s1mple"})

    response = client.get("/api/export/")
    assert response.status_code == 200
    data = response.json()
    assert "teams" in data
    assert "players" in data
    assert len(data["teams"]) == 1

# ==================== HTML VIEWS TESTS ====================

def test_index_page():
    """Test strony głównej."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"CS2 Player Tracker" in response.content

def test_ranking_page():
    """Test strony rankingu."""
    response = client.get("/ranking")
    assert response.status_code == 200

def test_player_profile_page():
    """Test strony profilu gracza."""
    player = client.post("/api/players/", json={"nickname": "jL"}).json()

    response = client.get(f"/player/{player['id']}")
    assert response.status_code == 200