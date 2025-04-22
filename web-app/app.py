import os
import requests
import random
from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static', template_folder='templates')

# Load environment variables
load_dotenv()
app.secret_key = os.getenv("SECRET_KEY")  # make sure this exists in .env file

# connect to MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client["mydb"]
users = db["users"]
additional_drinks = db["additional_drinks"]


@app.route("/")
def home():
    return render_template("landing.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if users.find_one({"username": username}):
            return "User already exists. Try logging in."

        hashed_pw = generate_password_hash(password)
        users.insert_one({"username": username, "password": hashed_pw})
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = users.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            return "Invalid username or password."

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", username=session["username"])


@app.route("/saved")
def saved():
    if "username" not in session:
        return redirect(url_for("login"))

    user = users.find_one({"username": session["username"]})

    if not user or "saved_drinks" not in user:
        saved_drinks = []
    else:
        saved_drinks = user["saved_drinks"]

    return render_template("saved.html", saved=saved_drinks)


@app.route('/search', methods=["GET"])
def search():
    query = request.args.get('query', '')
    recommended = []

    mongo_drinks = additional_drinks.find({"strDrink": {"$regex": query, "$options": "i"}})
    for drink in mongo_drinks:
        recommended.append({
            "id": drink["idDrink"],
            "name": drink["strDrink"],
            "image": drink.get("strDrinkThumb", "")
        })

    if query:
        try:
            response = requests.get(
                f"https://www.thecocktaildb.com/api/json/v1/1/search.php?s={query}"
            )
            response.raise_for_status()
            data = response.json()
            drinks = data.get('drinks')

            if drinks:
                for drink in drinks:
                    recommended.append({
                        "id": drink["idDrink"],
                        "name": drink["strDrink"],
                        "image": drink["strDrinkThumb"]
                    })
            else:
                recommended = []
        except requests.exceptions.RequestException as e:
            print("API Error:", e)
            recommended = []

    else:
        recommended = [{
            "id":
            "11000",
            "name":
            "Mojito",
            "image":
            "https://www.thecocktaildb.com/images/media/drink/metwgh1606770327.jpg"
        }, {
            "id":
            "11001",
            "name":
            "Old Fashioned",
            "image":
            "https://www.thecocktaildb.com/images/media/drink/vrwquq1478252802.jpg"
        }, {
            "id":
            "11002",
            "name":
            "Margarita",
            "image":
            "https://www.thecocktaildb.com/images/media/drink/wpxpvu1439905379.jpg"
        }, {
            "id":
            "11003",
            "name":
            "Daiquiri",
            "image":
            "https://www.thecocktaildb.com/images/media/drink/mrz9091589574515.jpg"
        }] 
    
    return render_template('search.html', recommended=recommended)


@app.route('/browse/<letter>')
def browse_by_letter(letter):
    try:
        response = requests.get(
            f"https://www.thecocktaildb.com/api/json/v1/1/search.php?f={letter}"
        )
        response.raise_for_status()
        data = response.json()
        drinks = data.get('drinks')

        recommended = []
        if drinks:
            for drink in drinks:
                recommended.append({
                    "id": drink["idDrink"],
                    "name": drink["strDrink"],
                    "image": drink["strDrinkThumb"]
                })

        return render_template('search.html', recommended=recommended)

    except requests.exceptions.RequestException as e:
        print("API Error:", e)
        return render_template('search.html', recommended=[])


@app.route("/recipe/<recipe_id>", methods=["GET", "POST"])
def recipe(recipe_id):
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "GET":
        cocktail = additional_drinks.find_one({"idDrink": recipe_id})
        if cocktail:
            ingredients = []
            image = cocktail.get("strDrinkThumb", "")

            for i in range(1, 16):
                ing = cocktail.get(f"strIngredient{i}")
                meas = cocktail.get(f"strMeasure{i}")
                if ing:
                    ingredients.append(f"{meas or ''} {ing}".strip())

            user = users.find_one({"username": session["username"]})
            saved = any(drink["id"] == recipe_id
                        for drink in user.get("saved_drinks", []))

            return render_template("recipe.html",
                                   cocktail=cocktail,
                                   ingredients=ingredients,
                                   image=image,
                                   saved=saved)

        try:
            response = requests.get(
                f'http://www.thecocktaildb.com/api/json/v1/1/lookup.php?i={recipe_id}'
            )
            response.raise_for_status()

            data = response.json()
            drinks = data.get("drinks")
            if not drinks:
                return "Recipe not found."

            cocktail = drinks[0]
            ingredients = []
            image = cocktail['strDrinkThumb']

            for i in range(1, 16):
                ing = cocktail.get(f"strIngredient{i}")
                meas = cocktail.get(f"strMeasure{i}")
                if ing:
                    ingredients.append(f"{meas or ''} {ing}".strip())

            user = users.find_one({"username": session["username"]})
            saved = any(drink["id"] == recipe_id
                        for drink in user.get("saved_drinks", []))

            return render_template("recipe.html",
                                   cocktail=cocktail,
                                   ingredients=ingredients,
                                   image=image,
                                   saved=saved)

        except requests.exceptions.RequestException as e:
            print("API Error:", e)
            return "Recipe not found."

    return redirect(url_for("saved"))


@app.route('/save_and_redirect/<recipe_id>', methods=["POST"])
def save_and_redirect(recipe_id):
    if "username" not in session:
        return redirect(url_for("login"))

    user = users.find_one({"username": session["username"]})
    if user:
        try:
            response = requests.get(
                f"https://www.thecocktaildb.com/api/json/v1/1/lookup.php?i={recipe_id}"
            )
            response.raise_for_status()
            data = response.json()
            cocktail = data['drinks'][0]

            users.update_one({"_id": user["_id"]}, {
                "$addToSet": {
                    "saved_drinks": {
                        "id": cocktail['idDrink'],
                        "name": cocktail['strDrink'],
                        "image": cocktail['strDrinkThumb']
                    }
                }
            })
        except requests.exceptions.RequestException as e:
            print("Error fetching cocktail data:", e)

    return redirect(url_for('saved'))


@app.route('/unsave/<recipe_id>', methods=["POST"])
def unsave_drink(recipe_id):
    if "username" not in session:
        return redirect(url_for("login"))

    user = users.find_one({"username": session["username"]})
    if user:
        users.update_one({"_id": user["_id"]},
                         {"$pull": {
                             "saved_drinks": {
                                 "id": recipe_id
                             }
                         }})

    return redirect(url_for('saved'))


@app.route("/spin")
def spin():
    return render_template("spin.html")

def recommend_drink(event, location, attendees):
    category = ""
   
    if event == "business" and location == "corporation" and (attendees == "large-group" or attendees == "unknown"): 
        category = "Cocktail"
    elif event == "business" and (location == "house" or location == "outdoors") and attendees:
        category = "Soft_Drink"
    elif event == "business" and location == "restaurant-venue" and attendees:
        category = "Beer"
    elif event == "pregame" and (location == "corporation" or location == "outdoors" or location == "restaurant-venue") and (attendees == "close-friends-families" or attendees == "large-group"): 
        category = "Beer"
    elif event == "pregame" and location == "house" and attendees == "close-friends-families":
        category = "Shot"
    elif event == "chill" and (location == "corporation" or location == "house" or location == "outdoors" or location == "restaurant-venue") and attendees:
        category = "Soft_Drink"
    elif event == "dinner" and (location == "corporation" or location == "outdoors" or location == "restaurant-venue") and attendees:
        category = "Cocktail"
    elif event == "dinner" and location == "house" and (attendees == "close-friends-families" or attendees == "unknown"):
        category = "Ordinary_Drink"
    elif event == "party" and (location == "corporation" or location == "restaurant-venue") and (attendees == "large-group" or attendees == "unknown"):
        category = "Cocktail"
    elif event == "party" and (location == "house" or location == "outdoors") and (attendees == "close-friends-families" or attendees == "large-group"):
        category = "Homemade_Liqueur"
    else: 
        category = "Cocktail"

    try: 
        response = requests.get(f"https://www.thecocktaildb.com/api/json/v1/1/filter.php?c={category}")
        response.raise_for_status()

        data = response.json()
        drinks = data.get("drinks")

        if drinks:
            recommended_drink = random.choice(drinks)
            drink_data = requests.get(f"https://www.thecocktaildb.com/api/json/v1/1/lookup.php?i={recommended_drink['idDrink']}")
            response.raise_for_status()
            found_drink = drink_data.json()
            drink = found_drink.get("drinks")[0]

            return drink

    except requests.exceptions.RequestException as e:
            print("Error fetching recommended drink data:", e)


@app.route("/questionnaire", methods=["GET", "POST"])
def questionnaire():
    if request.method == "POST":
        event = request.form.get("event")
        location = request.form.get("location")
        attendees = request.form.get("attendees")

        if event and location and attendees:
            recommended = recommend_drink(event, location, attendees)
            print(recommended)
            return render_template("questionnaire.html", recommended=recommended)
        else:
            return render_template("questionnaire.html", error="Please fill out all 3 questions to receive a recommendation.")

    return render_template("questionnaire.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
