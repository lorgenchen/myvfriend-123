from flask import Flask
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Flask app starting")

@app.route("/", methods=['GET'])
def home():
    logger.debug("Handling / request")
    return "Welcome to myvfriend-123!", 200

@app.route("/test", methods=['GET'])
def test():
    logger.debug("Handling /test request")
    return "Hello, test!", 200

@app.route("/callback", methods=['POST'])
def callback():
    logger.debug("Handling /callback request")
    return 'OK', 200

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    logger.debug(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port)