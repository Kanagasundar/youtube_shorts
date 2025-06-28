
from flask import Flask, request
from main import main
import os

app = Flask(__name__)

@app.route("/")
def index():
    key = request.args.get("key")
    if key != os.getenv("SECRET_KEY"):
        return "Unauthorized", 403
    main()
    return "Script executed successfully!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
