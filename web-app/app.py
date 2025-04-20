import os
import requests
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
    # if "username" not in session:
    #     return redirect(url_for("login"))
    return render_template("saved.html")


@app.route("/recipe/<recipe_id>")
def recipe(recipe_id):
    try:
        response = requests.get(
            f'http://www.thecocktaildb.com/api/json/v1/1/lookup.php?i={recipe_id}'
        )
        response.raise_for_status()

        data = response.json()

        # Check if recipe exists
        drinks = data.get("drinks")
        if not drinks:
            return "Recipe not found."

        # Get ingredients
        cocktail = drinks[0]
        ingredients = []

        for i in range(1, 16):
            ing = cocktail.get(f"strIngredient{i}")
            meas = cocktail.get(f"strMeasure{i}")
            if ing:
                ingredients.append(f"{meas or ''} {ing}".strip())

        return render_template("recipe.html",
                               cocktail=cocktail,
                               ingredients=ingredients)
    except requests.exceptions.RequestException as e:
        print("Error:", e)
        return "Recipe not found."


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
