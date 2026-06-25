"""
Flask app for SoundSketch.

It serves the frontend and provides a small API:
  GET  /api/health    - check the server is up
  GET  /api/examples  - example prompts for the page
  POST /api/generate  - prompt in, parameters + fallback melody out (JSON)
  POST /api/midi      - prompt in, downloadable .mid file out

The actual music logic lives in the other modules; this file just deals with
the web side (routes, checking input, sending responses).
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import io
import os

from prompt_mapper import map_prompt, PromptError
from generation_engine import generate
from midi_encoder import encode


FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=None)
CORS(app)


EXAMPLE_PROMPTS = [
    "dreamy and romantic",
    "dark and mysterious",
    "upbeat and playful",
    "sad and melancholy",
    "tense and glitchy",
]


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/examples")
def examples():
    return jsonify({"examples": EXAMPLE_PROMPTS})


def _get_prompt():
    """Read the 'prompt' field from the JSON body."""
    data = request.get_json(silent=True)
    if data is None or "prompt" not in data:
        raise PromptError("Request must be JSON with a 'prompt' field.")
    return data["prompt"]


@app.post("/api/generate")
def api_generate():
    try:
        params = map_prompt(_get_prompt())
    except PromptError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(generate(params).to_dict())


@app.post("/api/midi")
def api_midi():
    try:
        params = map_prompt(_get_prompt())
    except PromptError as exc:
        return jsonify({"error": str(exc)}), 400

    result = generate(params)
    midi_bytes = encode(result.fallback_notes, params.bpm)
    return send_file(
        io.BytesIO(midi_bytes),
        mimetype="audio/midi",
        as_attachment=True,
        download_name="soundsketch.mid",
    )


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
