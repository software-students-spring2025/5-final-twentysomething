from flask import Flask, render_template
from pymongo import MongoClient
import os

app = Flask(__name__)

# connect to mongodb
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(mongo_uri)
db = client["mydb"]  # default database

@app.route("/")
def home():
    return render_template("landing.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
å