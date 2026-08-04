"""
Unit tests for the CS2 Player Tracker application.
Matches the current logic of dynamic ranking calculations and API structures.
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
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
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
    """Test creating a new team."""
    response = client.post(
        "/api/teams/",
        json={"name": "Team Liquid", "logo_url": "https://example.com/liquid.png"},
    )
    assert (
        response.status_code == 200
    ), f"Expected status 200, got {response.status_code}"
    data = response.json()
    assert data["name"] == "Team Liquid", "Team name does not match the input"
    assert "id" in data, "Response should contain an ID"


def test_get_teams():
    """Test fetching the list of teams."""
    client.post("/api/teams/", json={"name": "Navi"})
    client.post("/api/teams/", json={"name": "Vitality"})

    response = client.get("/api/teams/")
    assert response.status_code == 200, "Error fetching the list of teams"
    data = response.json()
    assert len(data) == 2, f"Expected 2 teams, got {len(data)}"


def test_delete_team():
    """Test deleting a team."""
    create_response = client.post("/api/teams/", json={"name": "FaZe"})
    team_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/teams/{team_id}")
    assert delete_response.status_code == 200, "Error while deleting the team"

    get_response = client.get(f"/api/teams/{team_id}")
    assert (
        get_response.status_code == 404
    ), "Deleted team still exists (should return 404)"


def test_update_team():
    """Test editing a team's name."""
    create_response = client.post("/api/teams/", json={"name": "Astralis Old"})
    team_id = create_response.json()["id"]

    update_response = client.put(f"/api/teams/{team_id}", json={"name": "Astralis New"})
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Astralis New"


# ==================== PLAYERS TESTS ====================


def test_create_player():
    """Test creating a new player."""
    team_response = client.post("/api/teams/", json={"name": "FaZe"})
    team_id = team_response.json()["id"]

    response = client.post(
        "/api/players/",
        json={
            "nickname": "s1mple",
            "photo_url": "https://example.com/s1mple.jpg",
            "team_id": team_id,
        },
    )
    assert response.status_code == 200, "Failed to create player"
    data = response.json()
    assert data["nickname"] == "s1mple", "Incorrect player nickname"
    assert data["team_id"] == team_id, "Player assigned to wrong team ID"


def test_get_players():
    """Test fetching the list of players."""
    client.post("/api/players/", json={"nickname": "ZywOo"})
    client.post("/api/players/", json={"nickname": "donk"})

    response = client.get("/api/players/")
    assert response.status_code == 200, "Error fetching players"
    data = response.json()
    assert len(data) == 2, "Expected 2 players"


def test_search_players():
    """Test the player search functionality (Regex)."""
    client.post("/api/players/", json={"nickname": "m0NESY"})
    client.post("/api/players/", json={"nickname": "NiKo"})

    response = client.get("/api/search/players/?query=m0")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nickname"] == "m0NESY"


# ==================== TOURNAMENTS TESTS ====================


def test_create_tournament():
    """Test creating a new tournament."""
    response = client.post(
        "/api/tournaments/", json={"name": "IEM Katowice 2024", "weight": 2.0}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "IEM Katowice 2024"
    assert data["weight"] == 2.0


def test_get_tournaments():
    """Test fetching the list of tournaments."""
    client.post("/api/tournaments/", json={"name": "Major", "weight": 2.5})
    client.post("/api/tournaments/", json={"name": "Minor", "weight": 0.5})

    response = client.get("/api/tournaments/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_tournament_weight_validation():
    """Test if the app rejects a tournament when the sum of phase weights != 1.0."""
    response = client.post(
        "/api/tournaments/",
        json={
            "name": "Bad Tournament",
            "weight": 1.0,
            "weight_group": 0.5,
            "weight_quarters": 0.5,
            "weight_semis": 0.5,  # Sum is 1.5 instead of 1.0
            "weight_final": 0.0,
        },
    )
    assert response.status_code == 400, "The application should reject invalid weights"
    # Note: Checking for the Polish string because the backend API still returns this specific error message
    assert "Suma standardowych wag" in response.json()["detail"]


# ==================== MATCHES TESTS ====================


def test_create_match():
    """Test creating a new match."""
    team1 = client.post("/api/teams/", json={"name": "Navi"}).json()
    team2 = client.post("/api/teams/", json={"name": "Vitality"}).json()
    tournament = client.post(
        "/api/tournaments/", json={"name": "Major", "weight": 2.0}
    ).json()

    response = client.post(
        "/api/matches/",
        json={
            "tournament_id": tournament["id"],
            "phase": "Final",
            "date": "2024-01-15",
            "format": "BO5",
            "team1_id": team1["id"],
            "team2_id": team2["id"],
            "result": "3:2",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "Final"
    assert data["result"] == "3:2"


def test_get_matches():
    """Test fetching the list of matches."""
    team1 = client.post("/api/teams/", json={"name": "Navi"}).json()
    team2 = client.post("/api/teams/", json={"name": "Vitality"}).json()
    tournament = client.post(
        "/api/tournaments/", json={"name": "Major", "weight": 2.0}
    ).json()

    client.post(
        "/api/matches/",
        json={
            "tournament_id": tournament["id"],
            "phase": "Group",
            "date": "2024-01-10",
            "format": "BO3",
            "team1_id": team1["id"],
            "team2_id": team2["id"],
        },
    )

    response = client.get("/api/matches/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "tournament" in data[0]


# ==================== RANKING TEST ====================


def test_ranking_calculation():
    """Test the dynamic ranking calculation based on performances and rounds."""
    # 1. Create team
    team = client.post("/api/teams/", json={"name": "Navi"}).json()

    # 2. Create player
    player = client.post(
        "/api/players/", json={"nickname": "jL", "team_id": team["id"]}
    ).json()

    # 3. Create tournament
    tour = client.post(
        "/api/tournaments/", json={"name": "Major 2024", "weight": 1.0}
    ).json()

    # 4. Add team to tournament and specify played rounds
    client.post(
        f"/api/tournaments/{tour['id']}/add_team",
        json={
            "team_id": team["id"],
            "starts_in_semis": False,
            "in_group": True,
            "rounds_group": 150,
        },
    )

    # 5. Set player's rating performance
    client.post(
        "/api/performances/",
        json={
            "player_id": player["id"],
            "tournament_id": tour["id"],
            "rating_group": 1.45,
        },
    )

    # 6. Fetch ranking and verify
    response = client.get("/api/ranking/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert (
        data[0]["total_points"] > 0
    ), "Ranking points calculation failed, expected > 0"


# ==================== EXPORT/IMPORT TESTS ====================


def test_export_database():
    """Test exporting the database."""
    client.post("/api/teams/", json={"name": "Navi"})
    client.post("/api/players/", json={"nickname": "s1mple"})

    # Fixed errors with the trailing "/" in the API endpoint
    response = client.get("/api/export")
    assert response.status_code == 200
    data = response.json()
    assert "teams" in data
    assert "players" in data
    assert len(data["teams"]) == 1


# ==================== HTML VIEWS TESTS ====================


def test_index_page():
    """Test the index page rendering."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"CS2 Player Tracker" in response.content


def test_ranking_page():
    """Test the main ranking page rendering."""
    response = client.get("/ranking")
    assert response.status_code == 200


def test_player_profile_page():
    """Test the player profile page rendering."""
    player = client.post("/api/players/", json={"nickname": "jL"}).json()

    response = client.get(f"/player/{player['id']}")
    assert response.status_code == 200


def test_players_page():
    """Test the main players list page."""
    response = client.get("/players")
    assert response.status_code == 200
