import pytest
import requests
from unittest.mock import patch
from app import app, recommend_drink
from werkzeug.security import generate_password_hash
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def patch_mongo_collections():
    with patch("app.users") as mock_users, patch("app.additional_drinks") as mock_drinks:
        yield mock_users, mock_drinks


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


# test for landing
def test_landing_page(client_fixture):
    response = client_fixture.get("/")
    assert response.status_code == 200
    assert b"COCKTAIL GENERATOR" in response.data


# tests for signup route
def test_signup_get_request(client_fixture):
    response = client_fixture.get("/signup")
    assert response.status_code == 200
    assert b"Sign Up" in response.data


def test_signup_post_missing_fields(client_fixture):
    response = client_fixture.post("/signup", data={"username": ""})
    assert response.status_code == 200
    assert b"Please fill out both username and password." in response.data


def test_signup_post_empty_fields(client_fixture):
    response = client_fixture.post("/signup", data={"username": "", "password": ""})
    assert response.status_code == 200
    assert b"Please fill out both username and password." in response.data


@patch("app.users")
def test_signup_post_new_user(mock_users, client_fixture):
    mock_users.find_one.return_value = None  # simulate no user
    mock_users.insert_one.return_value = None

    response = client_fixture.post("/signup",
                                   data={
                                       "username": "newuser",
                                       "password": "newpass"
                                   },
                                   follow_redirects=True)

    assert response.status_code == 200
    assert b"Login" in response.data or b"Sign Up" in response.data


@patch("app.users")
def test_signup_post_existing_user(mock_users, client_fixture):
    mock_users.find_one.return_value = {"username": "existinguser"}

    response = client_fixture.post("/signup",
                                   data={
                                       "username": "existinguser",
                                       "password": "123"
                                   },
                                   follow_redirects=True)

    assert b"User already exists. Try logging in." in response.data


# tests for login route
def test_login_get_request(client_fixture):
    response = client_fixture.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_login_post_missing_fields(client_fixture):
    response = client_fixture.post("/login", data={"username": ""})
    assert response.status_code == 200
    assert b"Please fill out both username and password." in response.data


def test_login_post_empty_fields(client_fixture):
    response = client_fixture.post("/login", data={"username": "", "password": ""})
    assert response.status_code == 200
    assert b"Please fill out both username and password." in response.data


def test_login_page_when_logged_in(client_fixture):
    session(client_fixture)
    response = client_fixture.get("/login", follow_redirects=True)
    assert response.status_code == 200


@patch("app.users")
def test_login_post_valid_credentials(mock_users, client_fixture):
    mock_users.find_one.return_value = {
        "username": "testuser",
        "password": generate_password_hash("testpass")
    }

    response = client_fixture.post("/login",
                                   data={
                                       "username": "testuser",
                                       "password": "testpass"
                                   },
                                   follow_redirects=True)

    assert response.status_code == 200
    assert b"Dashboard" in response.data or b"COCKTAIL GENERATOR" in response.data  # depending on dashboard.html


@patch("app.users")
def test_login_post_invalid_credentials(mock_users, client_fixture):
    mock_users.find_one.return_value = None  # simulate no user

    response = client_fixture.post("/login",
                                   data={
                                       "username": "wrong",
                                       "password": "wrong"
                                   },
                                   follow_redirects=True)

    assert b"Invalid username or password." in response.data

# test for logout route
def test_logout_clears_session(client_fixture):
    with client_fixture.session_transaction() as sess:
        sess["username"] = "testuser"

    response = client_fixture.get("/logout", follow_redirects=True)

    assert response.status_code == 200
    assert b"Login" in response.data or b"Sign Up" in response.data  


def test_logout_without_login(client_fixture):
    response = client_fixture.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data


# test for dashboard route
def test_dashboard_access_when_logged_in(client_fixture):
    session(client_fixture)
    response = client_fixture.get("/dashboard")
    assert response.status_code == 200
    assert b"Dashboard" in response.data or b"COCKTAIL GENERATOR" in response.data


def test_dashboard_redirects_if_not_logged_in(client_fixture):
    response = client_fixture.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


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
def test_questionnaire_post_request_successful(mock_recommend_drink,
                                               client_fixture):
    session(client_fixture)
    response = client_fixture.post("/questionnaire",
                                   data={
                                       "event": "business",
                                       "location": "corporation",
                                       "attendees": "large-group"
                                   })

    mock_recommend_drink.assert_called_once()
    assert response.status_code == 200
    assert b"Questionnaire" in response.data

def test_questionnaire_post_request_failure(client_fixture):
    session(client_fixture)
    response = client_fixture.post("/questionnaire",
                                   data={
                                       "event": "business",
                                       "location": "corporation",
                                       "attendees": ""
                                   })

    assert response.status_code == 200
    assert b"Please fill out all 3 questions to receive a recommendation." in response.data


@patch("app.users")
def test_show_empty_saved_when_no_user_found(mock_users, client_fixture):
    with client_fixture.session_transaction() as sess:
        sess["username"] = "nonexistent_user"

    mock_users.find_one.return_value = None

    response = client_fixture.get("/saved")

    assert response.status_code == 200
    assert b"saved" in response.data

@patch("app.users")
def test_show_saved_drinks(mock_users, client_fixture):
    session(client_fixture)

    mock_users["testuser"] = {"username": "testuser"}

    response = client_fixture.get("/saved")

    assert response.status_code == 200

# tests for saved route
def test_saved_redirect_if_not_logged_in(client_fixture):
    response = client_fixture.get("/saved", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    

# tests for recipe route
def test_recipe_redirect_if_not_logged_in(client_fixture):
    response = client_fixture.get("/recipe/12345", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


@patch("app.users.find_one")
@patch("app.additional_drinks.find_one")
def test_recipe_found_in_db(mock_find_drinks, mock_find_user, client_fixture):
    recipe_id = "12345"

    mock_find_drinks.return_value = {
        "idDrink": recipe_id,
        "strDrinkThumb": "http://example.com/image.jpg",
        "strIngredient1": "Rum",
        "strMeasure1": "50ml"
    }

    mock_find_user.return_value = {"username": "testuser", "saved_drinks": []}

    session(client_fixture)

    response = client_fixture.get(f"/recipe/{recipe_id}")

    assert response.status_code == 200
    assert b"Rum" in response.data
    assert b"50ml" in response.data
    assert b"http://example.com/image.jpg" in response.data

@patch("app.users.find_one")
@patch("app.additional_drinks.find_one")
def test_recipe_not_found_in_db(mock_find_drinks, mock_find_user,
                                client_fixture):
    recipe_id = "12345"

    mock_find_drinks.return_value = None
    mock_find_user.return_value = {"username": "testuser", "saved_drinks": []}

    with client_fixture.session_transaction() as sess:
        sess["username"] = "testuser"

    response = client_fixture.get(f"/recipe/{recipe_id}")

    assert response.status_code == 200
    assert b"Recipe not found" in response.data

@patch("app.users.find_one")
@patch("app.additional_drinks.find_one")
def test_recipe_saved_flag(mock_find_drinks, mock_find_user, client_fixture):
    recipe_id = "12345"

    mock_find_drinks.return_value = {
        "idDrink": recipe_id,
        "strDrinkThumb": "http://example.com/image.jpg",
        "strIngredient1": "Rum",
        "strMeasure1": "50ml"
    }

    mock_find_user.return_value = {
        "username": "testuser",
        "saved_drinks": [{
            "id": recipe_id
        }]
    }

    session(client_fixture)

    response = client_fixture.get(f"/recipe/{recipe_id}")

    assert response.status_code == 200
    assert b"saved" in response.data

@patch("app.users.find_one")
@patch("app.additional_drinks.find_one")
def test_post_save_recipe(mock_find_drinks, mock_find_user, client_fixture):
    recipe_id = "12345"

    mock_find_drinks.return_value = {
        "idDrink": recipe_id,
        "strDrinkThumb": "http://example.com/image.jpg",
        "strIngredient1": "Rum",
        "strMeasure1": "50ml"
    }

    mock_find_user.return_value = {"username": "testuser", "saved_drinks": []}

    with client_fixture.session_transaction() as sess:
        sess["username"] = "testuser"

    response = client_fixture.post(f"/recipe/{recipe_id}",
                                   follow_redirects=True)

    assert response.status_code == 200
    assert b"saved" in response.data


# tests for custom drink route
def test_custom_redirect_if_not_logged_in_get(client_fixture):
    """
    Test that /custom redirects to login page if not logged in (GET).
    """
    response = client_fixture.get("/custom", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_custom_redirect_if_not_logged_in_post(client_fixture):
    """
    Test that /custom redirects to login page if not logged in (POST).
    """
    response = client_fixture.post("/custom", data={}, follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_custom_page_loads_logged_in(client_fixture):
    """
    Test that /custom page loads properly when logged in (GET).
    """
    session(client_fixture)
    response = client_fixture.get("/custom")
    assert response.status_code == 200
    assert b"Drink Name" in response.data
    assert b"Save Recipe" in response.data

@patch("app.users")
def test_custom_post_create_new_drink_first_time(mock_users, client_fixture):
    """
    Test POSTing a custom drink when user has NO previous saved drinks.
    """
    session(client_fixture)

    mock_users.find_one.return_value = {"username": "testing_user", "saved_drinks": []}
    mock_users.update_one.return_value = None  # simulate successful update

    form_data = {
        "strDrink": "MyCustomDrink",
        "strGlass": "Highball glass",
        "strInstructions": "Mix well.",
        "strDrinkThumb": "http://example.com/image.jpg",
        "strMeasure1": "1 oz",
        "strIngredient1": "Vodka"
    }

    for i in range(2, 16):
        form_data[f"strMeasure{i}"] = ""
        form_data[f"strIngredient{i}"] = ""

    response = client_fixture.post("/custom", data=form_data, follow_redirects=True)

    assert response.status_code == 200
    assert b"saved" in response.data or b"Saved" in response.data
    mock_users.update_one.assert_called_once()


@patch("app.users")
def test_custom_post_create_new_drink_with_existing_ids(mock_users, client_fixture):
    """
    Test POSTing a custom drink when user already has previous saved drinks.
    """
    session(client_fixture)

    # simulate user already having saved drinks
    mock_users.find_one.return_value = {
        "username": "testing_user",
        "saved_drinks": [
            {"id": "17841", "strDrink": "TestDrink1"},
            {"id": "17845", "strDrink": "TestDrink2"},
        ]
    }
    mock_users.update_one.return_value = None  # simulate successful update

    form_data = {
        "strDrink": "AnotherCustomDrink",
        "strGlass": "Martini glass",
        "strInstructions": "Shake well.",
        "strDrinkThumb": "http://example.com/martini.jpg",
        "strMeasure1": "2 oz",
        "strIngredient1": "Gin"
    }
    for i in range(2, 16):
        form_data[f"strMeasure{i}"] = ""
        form_data[f"strIngredient{i}"] = ""

    response = client_fixture.post("/custom", data=form_data, follow_redirects=True)

    assert response.status_code == 200
    assert b"saved" in response.data or b"Saved" in response.data
    mock_users.update_one.assert_called_once()


# tests for save_and_redirect and unsave_and_redirect routes
def test_redirect_if_not_logged_in(client_fixture):
    response = client_fixture.post("/save_and_redirect/12345",
                                   follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    response = client_fixture.post("/unsave/12345", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

@patch("requests.get")
@patch("app.users.find_one")
def test_save_drink_from_api_error(mock_find_user, mock_requests,
                                   client_fixture):
    recipe_id = "12345"
    mock_find_user.return_value = {
        "username": "testuser",
        "_id": 1,
        "saved_drinks": []
    }

    mock_requests.side_effect = requests.exceptions.RequestException(
        "API Error")

    session(client_fixture)

    response = client_fixture.post(f"/save_and_redirect/{recipe_id}",
                                   follow_redirects=True)

    assert response.status_code == 200


@patch("app.users.find_one")
@patch("app.users.update_one")
def test_unsave_drink(mock_update, mock_find_user, client_fixture):
    recipe_id = "12345"
    mock_find_user.return_value = {
        "username":
        "testuser",
        "_id":
        1,
        "saved_drinks": [{
            "id": recipe_id,
            "strDrink": "Mojito",
            "strDrinkThumb": "http://example.com/mojito.jpg"
        }]
    }

    mock_update.return_value = None  

    session(client_fixture)

    response = client_fixture.post(f"/unsave/{recipe_id}",
                                   follow_redirects=True)

    assert response.status_code == 200
    mock_update.assert_called_once_with(
        {"_id": 1}, {"$pull": {
            "saved_drinks": {
                "id": recipe_id
            }
        }})

# --- tests for /search route ---

def test_search_page_load(client_fixture):
    """
    Test that the search page loads successfully without a query.
    """
    session(client_fixture)
    response = client_fixture.get("/search")
    assert response.status_code == 200
    assert b"Recommended Cocktails" in response.data

def test_search_with_query(client_fixture):
    """
    Test searching with a query.
    """
    session(client_fixture)
    response = client_fixture.get("/search?query=Mojito")
    assert response.status_code == 200
    assert b"Recommended Cocktails" in response.data  # could also check "Mojito" but depends on your mock DB


@patch("app.users.find_one")
def test_search_with_saved_drinks_matching(mock_find_user, client_fixture):
    """
    Test searching where a saved drink matches the query.
    """
    session(client_fixture)

    mock_find_user.return_value = {
        "username": "testuser",
        "saved_drinks": [{
            "id": "99999",
            "strDrink": "Mojito",
            "strDrinkThumb": "http://example.com/mojito.jpg"
        }]
    }

    response = client_fixture.get("/search?query=mojito")
    assert response.status_code == 200
    assert b"Mojito" in response.data


@patch("app.users.find_one")
def test_search_with_saved_drinks_no_match(mock_find_user, client_fixture):
    """
    Test searching where no saved drink matches the query.
    """
    session(client_fixture)

    mock_find_user.return_value = {
        "username": "testuser",
        "saved_drinks": [{
            "id": "99999",
            "strDrink": "Gin Tonic",
            "strDrinkThumb": "http://example.com/gin.jpg"
        }]
    }

    response = client_fixture.get("/search?query=mojito")
    assert response.status_code == 200
    assert b"Recommended Cocktails" in response.data


@patch("requests.get")
@patch("app.users.find_one")
def test_search_api_failure(mock_find_user, mock_requests_get, client_fixture):
    """
    Test search when external API fails.
    """
    session(client_fixture)

    mock_find_user.return_value = {
        "username": "testuser",
        "saved_drinks": []
    }

    mock_requests_get.side_effect = requests.exceptions.RequestException

    response = client_fixture.get("/search?query=mojito")
    assert response.status_code == 200
    assert b"Recommended Cocktails" in response.data

# tests for /browse/<letter> route 
@patch("app.additional_drinks.find")
@patch("requests.get")
@patch("app.users.find_one")
def test_browse_by_letter_success(mock_find_user, mock_requests_get, mock_mongo_find, client_fixture):
    session(client_fixture)

    mock_mongo_find.return_value = [{
        "idDrink": "12345",
        "strDrink": "Apple Martini",
        "strDrinkThumb": "http://example.com/apple.jpg"
    }]

    mock_find_user.return_value = {
        "username": "testuser",
        "saved_drinks": [{
            "id": "67890",
            "strDrink": "Apricot Sour",
            "strDrinkThumb": "http://example.com/apricot.jpg"
        }]
    }

    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = {
        "drinks": [
            {
                "idDrink": "54321",
                "strDrink": "Amaretto Sour",
                "strDrinkThumb": "http://example.com/amaretto.jpg"
            }
        ]
    }

    response = client_fixture.get("/browse/a")
    assert response.status_code == 200
    assert b"Apple Martini" in response.data
    assert b"Apricot Sour" in response.data
    assert b"Amaretto Sour" in response.data


@patch("app.additional_drinks.find")
@patch("requests.get")
@patch("app.users.find_one")
def test_browse_by_letter_no_mongo_drinks(mock_find_user, mock_requests_get, mock_mongo_find, client_fixture):
    session(client_fixture)

    mock_mongo_find.return_value = []  # no mongo drinks

    mock_find_user.return_value = {"username": "testuser", "saved_drinks": []}

    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = {
        "drinks": [
            {
                "idDrink": "54321",
                "strDrink": "Amaretto Sour",
                "strDrinkThumb": "http://example.com/amaretto.jpg"
            }
        ]
    }

    response = client_fixture.get("/browse/a")
    assert response.status_code == 200
    assert b"Amaretto Sour" in response.data


@patch("app.additional_drinks.find")
@patch("requests.get")
@patch("app.users.find_one")
def test_browse_by_letter_api_error(mock_find_user, mock_requests_get, mock_mongo_find, client_fixture):
    session(client_fixture)

    mock_mongo_find.return_value = []  # no mongo drinks
    mock_find_user.return_value = {"username": "testuser", "saved_drinks": []}

    mock_requests_get.side_effect = requests.exceptions.RequestException

    response = client_fixture.get("/browse/a")
    assert response.status_code == 200
    assert b"Recommended Cocktails" in response.data  # page loads empty list


# tests for /recipe/<recipe_id> route
@patch("app.additional_drinks.find_one")
@patch("app.users.find_one")
def test_recipe_found_in_mongo(mock_find_user, mock_find_drink, client_fixture):
    session(client_fixture)
    recipe_id = "12345"

    mock_find_drink.return_value = {
        "idDrink": recipe_id,
        "strDrinkThumb": "http://example.com/image.jpg",
        "strIngredient1": "Vodka",
        "strMeasure1": "2 oz"
    }
    mock_find_user.return_value = {"username": "testuser", "saved_drinks": []}

    response = client_fixture.get(f"/recipe/{recipe_id}")
    assert response.status_code == 200
    assert b"Vodka" in response.data
    assert b"2 oz" in response.data
    assert b"image.jpg" in response.data


@patch("app.additional_drinks.find_one")
@patch("app.users.find_one")
def test_recipe_found_in_custom_saved(mock_find_user, mock_find_drink, client_fixture):
    session(client_fixture)
    recipe_id = "17841"  # custom drink ID

    mock_find_drink.return_value = None
    mock_find_user.return_value = {
        "username": "testuser",
        "saved_drinks": [{
            "id": "17841",
            "strDrinkThumb": "http://example.com/custom.jpg",
            "strIngredient1": "Tequila",
            "strMeasure1": "1 oz"
        }]
    }

    response = client_fixture.get(f"/recipe/{recipe_id}")
    assert response.status_code == 200
    assert b"Tequila" in response.data
    assert b"custom.jpg" in response.data


@patch("app.additional_drinks.find_one")
@patch("app.users.find_one")
@patch("requests.get")
def test_recipe_found_in_api(mock_requests_get, mock_find_user, mock_find_drink, client_fixture):
    session(client_fixture)
    recipe_id = "11000"

    mock_find_drink.return_value = None
    mock_find_user.return_value = {"username": "testuser", "saved_drinks": []}

    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = {
        "drinks": [{
            "idDrink": "11000",
            "strDrinkThumb": "http://example.com/api_drink.jpg",
            "strIngredient1": "Gin",
            "strMeasure1": "50ml"
        }]
    }

    response = client_fixture.get(f"/recipe/{recipe_id}")
    assert response.status_code == 200
    assert b"Gin" in response.data
    assert b"50ml" in response.data
    assert b"api_drink.jpg" in response.data


@patch("app.additional_drinks.find_one")
@patch("app.users.find_one")
@patch("requests.get")
def test_recipe_not_found_api(mock_requests_get, mock_find_user, mock_find_drink, client_fixture):
    session(client_fixture)
    recipe_id = "11000"

    mock_find_drink.return_value = None
    mock_find_user.return_value = {"username": "testuser", "saved_drinks": []}

    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = {
        "drinks": None  # simulate drink not found
    }

    response = client_fixture.get(f"/recipe/{recipe_id}")
    assert response.status_code == 200
    assert b"Recipe not found" in response.data


@patch("app.additional_drinks.find_one")
@patch("app.users.find_one")
@patch("requests.get")
def test_recipe_api_error(mock_requests_get, mock_find_user, mock_find_drink, client_fixture):
    session(client_fixture)
    recipe_id = "11000"

    mock_find_drink.return_value = None
    mock_find_user.return_value = {"username": "testuser", "saved_drinks": []}
    mock_requests_get.side_effect = requests.exceptions.RequestException

    response = client_fixture.get(f"/recipe/{recipe_id}")
    assert response.status_code == 200
    assert b"Recipe not found" in response.data

# --- tests for /save_and_redirect and /unsave routes ---

def test_save_and_redirect_requires_login(client_fixture):
    """
    Ensure save_and_redirect redirects if not logged in.
    """
    response = client_fixture.post("/save_and_redirect/12345", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_unsave_requires_login(client_fixture):
    """
    Ensure unsave redirects if not logged in.
    """
    response = client_fixture.post("/unsave/12345", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


@patch("app.users.find_one")
@patch("app.additional_drinks.find_one")
def test_save_and_redirect_saved_from_mongo(mock_find_drink, mock_find_user, client_fixture):
    """
    Test saving a custom drink from MongoDB (id > 17840).
    """
    session(client_fixture)
    recipe_id = "17841"  # custom drink

    mock_find_user.return_value = {"_id": 1, "username": "testuser"}
    mock_find_drink.return_value = {
        "idDrink": recipe_id,
        "strDrink": "Custom Cocktail",
        "strDrinkThumb": "http://example.com/custom.jpg"
    }

    response = client_fixture.post(f"/save_and_redirect/{recipe_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"saved" in response.data or b"Saved" in response.data


@patch("app.users.find_one")
@patch("requests.get")
def test_save_and_redirect_saved_from_api(mock_requests_get, mock_find_user, client_fixture):
    """
    Test saving a drink fetched from CocktailDB (id <= 17840).
    """
    session(client_fixture)
    recipe_id = "11000"

    mock_find_user.return_value = {"_id": 1, "username": "testuser"}
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = {
        "drinks": [{
            "idDrink": recipe_id,
            "strDrink": "Mojito",
            "strDrinkThumb": "http://example.com/mojito.jpg"
        }]
    }

    response = client_fixture.post(f"/save_and_redirect/{recipe_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"saved" in response.data or b"Saved" in response.data


@patch("app.users.find_one")
@patch("requests.get")
def test_save_and_redirect_api_error(mock_requests_get, mock_find_user, client_fixture):
    """
    Test API failure during save_and_redirect.
    """
    session(client_fixture)
    recipe_id = "11000"

    mock_find_user.return_value = {"_id": 1, "username": "testuser"}
    mock_requests_get.side_effect = requests.exceptions.RequestException

    response = client_fixture.post(f"/save_and_redirect/{recipe_id}", follow_redirects=True)
    assert response.status_code == 200


@patch("app.users.find_one")
@patch("app.users.update_one")
def test_unsave_drink_success(mock_update_one, mock_find_user, client_fixture):
    """
    Test successfully unsaving a drink.
    """
    session(client_fixture)
    recipe_id = "12345"

    mock_find_user.return_value = {
        "_id": 1,
        "username": "testuser",
        "saved_drinks": [{
            "id": "12345",
            "strDrink": "Gin Tonic",
            "strDrinkThumb": "http://example.com/gin.jpg"
        }]
    }
    mock_update_one.return_value = None

    response = client_fixture.post(f"/unsave/{recipe_id}", follow_redirects=True)
    assert response.status_code == 200
    mock_update_one.assert_called_once_with(
        {"_id": 1},
        {"$pull": {"saved_drinks": {"id": recipe_id}}}
    )


# --- tests for /journal route ---

def test_journal_no_entries(client_fixture):
    """
    Test the journal page when there are no journal entries.
    """
    session(client_fixture)
    response = client_fixture.get("/journal")
    assert response.status_code == 200
    assert b"Gallery of Your Memory" in response.data

def test_journal_with_entries(client_fixture):
    """
    Test journal page with pre-existing journal entries in session.
    """
    with client_fixture.session_transaction() as sess:
        sess["username"] = "testuser"
        sess["journal_entries"] = [{
            "image_url": "/static/uploads/sample.png",
            "date": "04/25/2025",
            "caption": "Fun night!"
        }]

    response = client_fixture.get("/journal")
    assert response.status_code == 200
    assert b"Gallery of Your Memory" in response.data
    assert b"Fun night!" in response.data  



# --- tests for /takepicture route ---

def test_takepicture_requires_login(client_fixture):
    """
    Test that /takepicture redirects if not logged in.
    """
    response = client_fixture.get("/takepicture")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_takepicture_loads_logged_in(client_fixture):
    """
    Test that /takepicture loads successfully if logged in.
    """
    session(client_fixture)
    response = client_fixture.get("/takepicture")
    assert response.status_code == 200
    assert b"PhotoBooth" in response.data


# --- tests for /upload_image route ---

def test_upload_image_success(client_fixture):
    """
    Test uploading an image to the gallery.
    """
    session(client_fixture)
    sample_base64 = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAUA"
        "AAAFCAYAAACNbyblAAAAHElEQVQI12P4"
        "//8/w38GIAXDIBKE0DHxgljNBAAO"
        "9TXL0Y4OHwAAAABJRU5ErkJggg=="
    )

    response = client_fixture.post("/upload_image",
                                    json={"image": sample_base64, "caption": "My event"},
                                    follow_redirects=True)

    assert response.status_code == 200
    assert response.is_json
    assert response.get_json()["status"] == "success"


def test_upload_image_error_case(client_fixture):
    """
    Test uploading invalid image data returns error.
    """
    session(client_fixture)
    
    response = client_fixture.post("/upload_image",
                                   json={"image": "INVALID_DATA", "caption": "Bad upload"},
                                   follow_redirects=True)

    assert response.status_code == 200
    assert response.is_json
    assert response.get_json()["status"] == "error"


def test_upload_image_redirect_if_not_logged_in(client_fixture):
    """
    Test that /upload_image redirects to login page if not logged in.
    """
    response = client_fixture.post("/upload_image", json={"image": "fake"}, follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# test for /chat route
@patch("app.openai.OpenAI")
def test_chat_completion_success(mock_openai, client_fixture):
    session(client_fixture)

    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content="Mojito\nA refreshing rum cocktail."))]

    mock_client.chat.completions.create.return_value = mock_completion
    mock_openai.return_value = mock_client

    response = client_fixture.post("/chat", data={"user_input": "I want something refreshing"})

    assert response.status_code == 200
    assert b"I recommend..." in response.data
    assert b"Mojito" in response.data


@patch("app.openai.OpenAI")
def test_chat_post_empty_input(mock_openai, client_fixture):
    session(client_fixture)

    response = client_fixture.post("/chat", data={"user_input": ""})
    
    assert response.status_code == 200
    assert b"Something went wrong" in response.data


@patch("app.openai.OpenAI")
def test_chat_api_error(mock_openai, client_fixture):
    session(client_fixture)

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API Failure")
    mock_openai.return_value = mock_client

    response = client_fixture.post("/chat", data={"user_input": "I want a drink"})
    assert response.status_code == 200
    assert b"Error" in response.data


@patch("app.openai.OpenAI")
def test_chat_no_user_input(mock_openai, client_fixture):
    session(client_fixture)
    response = client_fixture.post("/chat", data={"user_input": ""})
    assert response.status_code == 200
    assert b"Something went wrong" in response.data


def test_chat_redirects_if_not_logged_in(client_fixture):
    response = client_fixture.post("/chat", data={"user_input": "test"}, follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


@patch("app.openai.OpenAI")
@patch("app.additional_drinks.find_one")
@patch("requests.get")
def test_chat_no_cocktail_found(mock_requests_get, mock_find_one, mock_openai, client_fixture):
    session(client_fixture)

    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content="NonexistentDrink\nA rare drink."))]
    mock_client.chat.completions.create.return_value = mock_completion
    mock_openai.return_value = mock_client

    mock_find_one.return_value = None

    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = {"drinks": None}

    response = client_fixture.post("/chat", data={"user_input": "Give me a rare drink"})
    assert response.status_code == 200
    assert b"Unfortunately, we don't have a recipe for this drink at the moment." in response.data
