# Final minimal Flask app placeholder
from flask import Flask, request

app = Flask(__name__)

@app.route('/')
def home():
    return "App working"

if __name__ == "__main__":
    app.run()
