import os
from flask import Flask, send_from_directory

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

@app.get("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.css")

@app.get("/<path:path>")
def assets(path):
    return send_from_directory(FRONTEND_DIR, path)
