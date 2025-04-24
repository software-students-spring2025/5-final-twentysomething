import pytest
import requests
from unittest.mock import patch
from app import app, recommend_drink
from werkzeug.security import generate_password_hash


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


# tests for signup route 
def test_signup_get_request(client_fixture):
    response = client_fixture.get("/signup")
    assert response.status_code == 200
    assert b"Sign Up" in response.data


@patch("app.users")
def test_signup_post_new_user(mock_users, client_fixture):
    mock_users.find_one.return_value = None # simulate no user
    mock_users.insert_one.return_value = None

    response = client_fixture.post(
        "/signup", data={"username": "newuser", "password": "newpass"}, follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Login" in response.data or b"Sign Up" in response.data 


@patch("app.users")
def test_signup_post_existing_user(mock_users, client_fixture):
    mock_users.find_one.return_value = {"username": "existinguser"}

    response = client_fixture.post(
        "/signup", data={"username": "existinguser", "password": "123"}, follow_redirects=True
    )

    assert b"User already exists. Try logging in." in response.data


# tests for login route
def test_login_get_request(client_fixture):
    response = client_fixture.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data

@patch("app.users")
def test_login_post_valid_credentials(mock_users, client_fixture):
    mock_users.find_one.return_value = {
        "username": "testuser",
        "password": generate_password_hash("testpass")
    }

    response = client_fixture.post(
        "/login", data={"username": "testuser", "password": "testpass"}, follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Dashboard" in response.data or b"COCKTAIL GENERATOR" in response.data  # depending on dashboard.html


@patch("app.users")
def test_login_post_invalid_credentials(mock_users, client_fixture):
    mock_users.find_one.return_value = None  # simulate no user

    response = client_fixture.post(
        "/login", data={"username": "wrong", "password": "wrong"}, follow_redirects=True
    )

    assert b"Invalid username or password." in response.data


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