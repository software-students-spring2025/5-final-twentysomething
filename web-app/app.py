import os
from flask import Flask, render_template
from pymongo import MongoClient
from dotenv import load_dotenv

app = Flask(__name__, static_folder='static', template_folder='templates')

# Load environment variables from the .env file
load_dotenv()

# connect to mongodb
client = MongoClient(os.getenv("MONGO_URI"))
db = client["mydb"]  # default database
users = db["users"]


@app.route("/")
def home():
    return render_template("landing.html")

@app.route("/login")
def login():
    return render_template("login.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
