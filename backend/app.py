
from flask import Flask, jsonify
import os
app = Flask(__name__)
@app.route("/")
def root():
    return jsonify(service="backend", status="ok", version=os.getenv("APP_VERSION","v0.1.0"))
@app.route("/healthz")
def healthz():
    return "ok", 200
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
