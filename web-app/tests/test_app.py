import pytest
import requests
from unittest.mock import patch
from app import app, recommend_drink

@pytest.fixture
def client_fixture():
    """
    Create a test client for the Flask application.
    """
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "testing"

    with app.test_client() as client:
        yield client


def session(client_fixture):
    """
    Create a test session user to login the app (use if needed for tests)
    """
    with client_fixture.session_transaction() as sess:
        sess["username"] = "testing_user"


# tests for spin route
def test_spin_get_request_no_login(client_fixture):
    response = client_fixture.get("/spin")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_spin_get_request_with_login(client_fixture):
    session(client_fixture)
    response = client_fixture.get("/spin")

    assert response.status_code == 200
    assert b"Spin the Wheel" in response.data


# tests for recommend_drinks function
def test_recommend_drink_successful():
    event = "chill"
    location = "house"
    attendees = "close-friends-families"

    drink = recommend_drink(event, location, attendees)

    assert isinstance(drink["strDrink"], str)
    assert isinstance(drink["strInstructions"], str)
    assert len(drink) == 51


@patch("requests.get")
def test_recommend_drink_failure(mock_requests, client_fixture):
    event = "chill"
    location = "house"
    attendees = "close-friends-families"

    mock_requests.side_effect = requests.exceptions.RequestException
    drink = recommend_drink(event, location, attendees)

    assert drink == None


# tests for questionnaire route
def test_questionnaire_get_request_no_login(client_fixture):
    response = client_fixture.get("/questionnaire")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_questionnaire_get_request_with_login(client_fixture):
    session(client_fixture)
    response = client_fixture.get("/questionnaire")

    assert response.status_code == 200
    assert b"Questionnaire" in response.data

@patch("app.recommend_drink")
def test_questionnaire_post_request_successful(mock_recommend_drink, client_fixture):
    session(client_fixture)
    response = client_fixture.post(
        "/questionnaire", data={"event": "business", "location": "corporation", "attendees": "large-group"}
    )

    mock_recommend_drink.assert_called_once()
    assert response.status_code == 200
    assert b"Questionnaire" in response.data

def test_questionnaire_post_request_failure(client_fixture):
    session(client_fixture)
    response = client_fixture.post(
        "/questionnaire", data={"event": "business", "location": "corporation", "attendees": ""}
    )

    assert response.status_code == 200
    assert b"Please fill out all 3 questions to receive a recommendation." in response.data