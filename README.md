# SoundSketch

**AI-powered mood-based melody generator.** Describe a mood in plain language
(for example, *"dreamy and romantic"*) and SoundSketch generates a short,
playable MIDI melody you can preview in the browser and download.

This repository is an academic portfolio project for the IU course
*Project: Software Engineering (DLMCSPSE01)*. It is the final (Phase 3) submission:
the application works end to end, is covered by automated tests, and is deployed
as a public web application.

---

## How it works

SoundSketch combines a small Python backend with an in-browser neural model:

1. The user enters a mood prompt in the web interface.
2. The **Flask backend** maps the prompt to musical parameters (key, mode,
   tempo, note density, length) using a transparent keyword lexicon.
3. The browser runs Google's **MusicVAE** model (via Magenta.js) to sample a
   melody, conditioned by those parameters.
4. If the neural model is unavailable, the backend's **fallback composer**
   produces a valid melody so the app always works.
5. The melody plays through **Tone.js** and can be downloaded as a `.mid` file.

See `docs/` for the full architecture documentation.

---

## Project structure

```
soundsketch/
├── backend/
│   ├── app.py                 # Flask REST API + static file serving
│   ├── prompt_mapper.py       # Mood prompt -> musical parameters
│   ├── generation_engine.py   # Parameters -> model config + fallback melody
│   ├── midi_encoder.py        # Note list -> standard MIDI file
│   ├── requirements.txt
│   └── tests/                 # pytest unit + integration tests
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js                 # Magenta.js + Tone.js client logic
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Running locally (macOS)

You need **Python 3.10+**. Check with `python3 --version`.

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd soundsketch/backend

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python3 app.py
```

Then open **http://localhost:5000** in your browser. Enter a mood and press
**Generate**. The first generation may take a few seconds while the neural
model downloads in the background; the app uses the fallback composer until it
is ready.

---

## Running the tests

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
python3 -m pytest tests/ -v
```

---

## Running with Docker

```bash
docker compose up --build
```

The app will be available at **http://localhost:5000**.

---

## Future work / known technical debt

- Expand the mood lexicon and add graceful handling of unknown words.
- Add chordal accompaniment to the MIDI export.
- Broaden automated test coverage and add measured performance tests.
- Add a piano-roll visual and in-UI tempo/key overrides.

---

## Third-party libraries

| Library | Purpose | License |
|---------|---------|---------|
| [Flask](https://flask.palletsprojects.com/) | Web framework / REST API | BSD-3 |
| [flask-cors](https://flask-cors.readthedocs.io/) | CORS handling | MIT |
| [Magenta.js](https://magenta.tensorflow.org/js) | In-browser MusicVAE model | Apache-2.0 |
| [Tone.js](https://tonejs.github.io/) | Web Audio playback | MIT |
| [pytest](https://docs.pytest.org/) | Testing | MIT |
| [gunicorn](https://gunicorn.org/) | Production WSGI server | MIT |

The MIDI file encoder is implemented from scratch in `midi_encoder.py`.
