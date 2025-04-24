import os
import requests
import random
import openai
import base64
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')

# load environment variables
load_dotenv()
app.secret_key = os.getenv("SECRET_KEY")  # make sure this exists in .env file

# connect to OpenRouter
openai.api_base = "https://openrouter.ai/api/v1"
openai.api_key = os.getenv(
    "OPENROUTER_API_KEY")  # make sure this exists in .env file
openai_request_headers = {
    "Authorization": f"Bearer {openai.api_key}",
    "HTTP-Referer":
    "http://localhost:5001",  # replace with deployed URL if needed
    "X-Title": "CocktailChatApp"
}
OPENROUTER_SYSTEM_PROMPT = (
    "You are a cocktail recommendation assistant. Given a mood or event, return the name of an existing cocktail "
    "on the first line, followed by a one-sentence explanation on the next line. Be concise, and do not invent new drinks. "
    "Format it exactly like this:\n<drink name>\n<one-sentence explanation>")

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
            error = "User already exists. Try logging in."
            return render_template("signup.html", error=error)

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
            error = "Invalid username or password."
            return render_template("login.html", error=error)

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", username=session["username"])


@app.route("/chat", methods=["POST"])
def chat():
    if "username" not in session:
        return redirect(url_for("login"))

    user_input = request.form.get("user_input", "")
    response_text = "Something went wrong. Try again."

    if user_input:
        try:
            client = openai.OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"),
                                   base_url="https://openrouter.ai/api/v1")

            completion = client.chat.completions.create(
                model="openai/gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": OPENROUTER_SYSTEM_PROMPT
                }, {
                    "role": "user",
                    "content": user_input
                }],
                extra_headers={
                    "HTTP-Referer": "http://localhost:5001",
                    "X-Title": "CocktailChatApp"
                })

            ai_response = completion.choices[0].message.content.strip()
            lines = ai_response.split("\n", 1)

            drink_name = lines[0].strip()
            explanation = lines[1].strip() if len(lines) > 1 else ""

            cocktail = additional_drinks.find_one(
                {"strDrink": {
                    "$regex": f"^{drink_name}$",
                    "$options": "i"
                }})

            if not cocktail:
                api_resp = requests.get(
                    f"https://www.thecocktaildb.com/api/json/v1/1/search.php?s={drink_name}"
                )
                api_resp.raise_for_status()
                data = api_resp.json()
                cocktail = data.get("drinks",
                                    [])[0] if data.get("drinks") else None

            if cocktail:
                response_text = (
                    f"<strong>I recommend...</strong><br><br><strong>{drink_name}</strong> - {explanation}<br><br>"
                    "Click the <strong>Search Recipes</strong> button to see full ingredients and instructions."
                )
            else:
                response_text = (
                    f"<strong>I recommend...</strong><br><br><strong>{drink_name}</strong> - {explanation}<br><br>"
                    "Unfortunately, we don't have a recipe for this drink at the moment."
                )

        except Exception as e:
            response_text = f"<span style='color:red;'>Error: {str(e)}</span>"

    return f'<div class="ai-response">{response_text}</div>'


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
    query = request.args.get('query', '').lower().strip()
    recommended = []

    if query:
        try:
            response = requests.get(
                f"https://www.thecocktaildb.com/api/json/v1/1/search.php?s={query}"
            )
            response.raise_for_status()
            data = response.json()
            drinks = data.get('drinks', [])

            if drinks:
                for drink in drinks:
                    recommended.append({
                        "id":
                        drink.get("idDrink"),
                        "strDrink":
                        drink.get("strDrink"),
                        "strDrinkThumb":
                        drink.get("strDrinkThumb", "")
                    })

            user = users.find_one({"username": session["username"]})
            saved_drinks = user.get("saved_drinks", []) if user else []

            for drink in saved_drinks:
                if query in drink.get("strDrink", "").lower():
                    recommended.append({
                        "id":
                        drink.get("id"),
                        "strDrink":
                        drink.get("strDrink"),
                        "strDrinkThumb":
                        drink.get("strDrinkThumb", "")
                    })
        except requests.exceptions.RequestException as e:
            print("API Error:", e)

    if not query and not recommended:
        recommended = [{
            "id":
            "11000",
            "strDrink":
            "Mojito",
            "strDrinkThumb":
            "https://www.thecocktaildb.com/images/media/drink/metwgh1606770327.jpg"
        }, {
            "id":
            "11001",
            "strDrink":
            "Old Fashioned",
            "strDrinkThumb":
            "https://www.thecocktaildb.com/images/media/drink/vrwquq1478252802.jpg"
        }, {
            "id":
            "11002",
            "strDrink":
            "Margarita",
            "strDrinkThumb":
            "https://www.thecocktaildb.com/images/media/drink/wpxpvu1439905379.jpg"
        }, {
            "id":
            "11006",
            "strDrink":
            "Daiquiri",
            "strDrinkThumb":
            "https://www.thecocktaildb.com/images/media/drink/mrz9091589574515.jpg"
        }]

    return render_template('search.html', recommended=recommended)


@app.route('/browse/<letter>')
def browse_by_letter(letter):
    letter = letter.lower()
    recommended = []

    try:
        response = requests.get(
            f"https://www.thecocktaildb.com/api/json/v1/1/search.php?f={letter}"
        )
        response.raise_for_status()
        data = response.json()
        api_drinks = data.get('drinks', [])
    except requests.exceptions.RequestException as e:
        print("API Error:", e)
        return render_template('search.html', recommended=[])

    user = users.find_one({"username": session["username"]})
    saved_drinks = user.get("saved_drinks", []) if user else []

    for drink in saved_drinks:
        if drink.get("strDrink", "").lower().startswith(letter):
            recommended.append({
                "id": drink.get("id"),
                "strDrink": drink.get("strDrink"),
                "strDrinkThumb": drink.get("strDrinkThumb", "")
            })

    if api_drinks:
        for drink in api_drinks:
            recommended.append({
                "id": drink.get("idDrink"),
                "strDrink": drink.get("strDrink"),
                "strDrinkThumb": drink.get("strDrinkThumb", "")
            })

    return render_template('search.html', recommended=recommended)


@app.route("/recipe/<recipe_id>", methods=["GET", "POST"])
def recipe(recipe_id):
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "GET":
        if int(recipe_id) > 17840:
            user = users.find_one({"username": session["username"]})

            if not user:
                print("User not found.")

            cocktail = next((drink for drink in user.get("saved_drinks", [])
                             if str(drink.get("id")) == recipe_id), None)
            if not cocktail:
                print("Drink not found")

            ingredients = []
            image = cocktail.get("strDrinkThumb", "")

            for i in range(1, 16):
                ingredient = cocktail.get(f"strIngredient{i}")
                measure = cocktail.get(f"strMeasure{i}")

                if ingredient and ingredient.strip():
                    # Combine measure and ingredient into one string
                    combined = f"{measure.strip()} {ingredient.strip()}" if measure else ingredient.strip(
                    )

                    ingredients.append(combined)

            saved = any(drink["id"] == recipe_id
                        for drink in user.get("saved_drinks", []))

            return render_template("recipe.html",
                                   cocktail=cocktail,
                                   ingredients=ingredients,
                                   image=image,
                                   saved=saved,
                                   drinkId=recipe_id)

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

            saved = any(
                str(drink["id"]["$numberInt"]) == str(recipe_id) if isinstance(
                    drink["id"], dict) else str(drink["id"]) == str(recipe_id)
                for drink in user.get("saved_drinks", []))

            return render_template("recipe.html",
                                   cocktail=cocktail,
                                   ingredients=ingredients,
                                   image=image,
                                   saved=saved,
                                   drinkId=recipe_id)

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
            if int(recipe_id) <= 17840:
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
                            "strDrink": cocktail['strDrink'],
                            "strDrinkThumb": cocktail['strDrinkThumb']
                        }
                    }
                })
            else:
                user = users.find_one({"username": session["username"]})

                saved = any(
                    str(drink["id"]["$numberInt"]) == recipe_id if isinstance(
                        drink["id"], dict) else str(drink["id"]) == recipe_id
                    for drink in user.get("saved_drinks", []))

                if not saved:
                    if cocktail:
                        users.update_one({"_id": user["_id"]}, {
                            "$push": {
                                "saved_drinks": {
                                    "id": cocktail['id'],
                                    "strDrink": cocktail.get('strDrink'),
                                    "strDrinkThumb":
                                    cocktail.get('strDrinkThumb')
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
    if "username" not in session:
        return redirect(url_for("login"))

    return render_template("spin.html")


def recommend_drink(event, location, attendees):
    category = ""

    if event == "business" and location == "corporation" and (
            attendees == "large-group" or attendees == "unknown"):
        category = "Cocktail"
    elif event == "business" and (location == "house"
                                  or location == "outdoors") and attendees:
        category = "Soft_Drink"
    elif event == "business" and location == "restaurant-venue" and attendees:
        category = "Beer"
    elif event == "pregame" and (
            location == "corporation" or location == "outdoors" or location
            == "restaurant-venue") and (attendees == "close-friends-families"
                                        or attendees == "large-group"):
        category = "Beer"
    elif event == "pregame" and location == "house" and attendees == "close-friends-families":
        category = "Shot"
    elif event == "chill" and (location == "corporation" or location == "house"
                               or location == "outdoors" or location
                               == "restaurant-venue") and attendees:
        category = "Soft_Drink"
    elif event == "dinner" and (location == "corporation"
                                or location == "outdoors" or location
                                == "restaurant-venue") and attendees:
        category = "Cocktail"
    elif event == "dinner" and location == "house" and (
            attendees == "close-friends-families" or attendees == "unknown"):
        category = "Ordinary_Drink"
    elif event == "party" and (location == "corporation"
                               or location == "restaurant-venue") and (
                                   attendees == "large-group"
                                   or attendees == "unknown"):
        category = "Cocktail"
    elif event == "party" and (location == "house" or location == "outdoors"
                               ) and (attendees == "close-friends-families"
                                      or attendees == "large-group"):
        category = "Homemade_Liqueur"
    else:
        category = "Cocktail"

    try:
        response = requests.get(
            f"https://www.thecocktaildb.com/api/json/v1/1/filter.php?c={category}"
        )
        response.raise_for_status()

        data = response.json()
        drinks = data.get("drinks")

        if drinks:
            recommended_drink = random.choice(drinks)
            drink_data = requests.get(
                f"https://www.thecocktaildb.com/api/json/v1/1/lookup.php?i={recommended_drink['idDrink']}"
            )
            response.raise_for_status()
            found_drink = drink_data.json()
            drink = found_drink.get("drinks")[0]

            return drink

    except requests.exceptions.RequestException as e:
        print("Error fetching recommended drink data:", e)
        return None


@app.route("/questionnaire", methods=["GET", "POST"])
def questionnaire():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        event = request.form.get("event")
        location = request.form.get("location")
        attendees = request.form.get("attendees")

        if event and location and attendees:
            recommended = recommend_drink(event, location, attendees)

            if recommended:
                return render_template("questionnaire.html",
                                       recommended=recommended)
        else:
            return render_template(
                "questionnaire.html",
                error=
                "Please fill out all 3 questions to receive a recommendation.")

    return render_template("questionnaire.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/takepicture")
def take_picture():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("takepicture.html")


@app.route("/journal")
def journal():
    journal_entries = session.get("journal_entries", [])
    return render_template("journal.html", journal_entries=journal_entries)


@app.route("/custom", methods=['GET', 'POST'])
def custom():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        strDrink = request.form["strDrink"]
        strGlass = request.form["strGlass"]
        strInstructions = request.form["strInstructions"]
        strDrinkThumb = request.form["strDrinkThumb"]

        ingredient_fields = {}
        for i in range(1, 16):
            measure_key = f"strMeasure{i}"
            ingredient_key = f"strIngredient{i}"
            ingredient_fields[measure_key] = request.form.get(
                measure_key) or None
            ingredient_fields[ingredient_key] = request.form.get(
                ingredient_key) or None

        user = users.find_one({"username": session["username"]})

        # Initialize saved_drinks if not found
        if not user or "saved_drinks" not in user:
            saved_drinks = []
        else:
            saved_drinks = user["saved_drinks"]

        drink_ids = []

        for drink in saved_drinks:
            drink_ids.append(int(drink["id"]))

        if drink_ids:
            if max(drink_ids) < 17841:
                new_id = 17841
            else:
                new_id = max(drink_ids) + 1
        else:
            new_id = 17841

        new_drink = {
            "id": str(new_id),
            "strDrink": strDrink,
            "strGlass": strGlass,
            "strDrinkThumb": strDrinkThumb,
            "strInstructions": strInstructions,
            **ingredient_fields
        }

        users.update_one({"username": session["username"]},
                         {"$addToSet": {
                             "saved_drinks": new_drink
                         }})

        return redirect(url_for("saved"))

    return render_template("custom.html")


@app.route("/upload_image", methods=["POST"])
def upload_image():
    if "username" not in session:
        return redirect(url_for("login"))

    data = request.get_json()
    image_data = data.get("image")
    caption = data.get("caption", "")
    date_str = datetime.now().strftime("%m/%d/%Y")

    if image_data and image_data.startswith("data:image/png;base64,"):
        image_data = image_data.replace("data:image/png;base64,", "")
        image_bytes = base64.b64decode(image_data)

        filename = f"journal_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        save_path = os.path.join("static", "uploads")
        os.makedirs("static/uploads", exist_ok=True)
        file_path = os.path.join(save_path, filename)

        with open(file_path, "wb") as f:
            f.write(image_bytes)

        # Store journal entry (example using session, ideally store in DB)
        new_entry = {
            "image_url": f"/static/uploads/{filename}",
            "date": date_str,
            "caption": caption
        }

        journal_entries = session.get("journal_entries", [])
        journal_entries.append(new_entry)
        session["journal_entries"] = journal_entries

        return jsonify({"status": "success"})

    return jsonify({"status": "error"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
