/*
 * app.js — SoundSketch frontend logic
 *
 * Responsibilities:
 *   - Load example prompts from the API.
 *   - Initialise the Magenta.js MusicVAE model in the background.
 *   - On Generate: call the backend for musical parameters + a fallback melody,
 *     then try to produce a richer melody with the in-browser MusicVAE model.
 *     If the model is not ready, fall back to the server-provided melody so the
 *     app always works.
 *   - Play melodies with Tone.js and offer a MIDI download.
 *
 * Phase 3 notes (intentional gaps): no piano-roll visual editing, no tempo/key
 * overrides in the UI, and model warm-up time is not yet optimised.
 */

(function () {
  "use strict";

  const API = ""; // same origin when served by Flask

  // ── DOM references ───────────────────────────────────────────────────────
  const promptInput = document.getElementById("prompt");
  const generateBtn = document.getElementById("generate");
  const charCount = document.getElementById("charcount");
  const modelStatus = document.getElementById("model-status");
  const examplesBox = document.getElementById("examples");
  const errorBox = document.getElementById("error");
  const resultBox = document.getElementById("result");
  const resultParams = document.getElementById("result-params");
  const playBtn = document.getElementById("play");
  const stopBtn = document.getElementById("stop");
  const regenBtn = document.getElementById("regenerate");
  const downloadLink = document.getElementById("download");
  const visualizer = document.getElementById("visualizer");
  const sourceNote = document.getElementById("source-note");

  // ── State ────────────────────────────────────────────────────────────────
  let musicVAE = null;
  let modelReady = false;
  let currentSequence = null; // Magenta NoteSequence currently loaded
  let currentParams = null;
  let synth = null;
  let scheduled = [];

  // ── Model initialisation ──────────────────────────────────────────────────
function initModel() {
    if (typeof music_vae === "undefined" || !music_vae.MusicVAE) {
      modelStatus.textContent = "model: unavailable (using server fallback)";
      return;
    }
    const checkpoint =
      "https://storage.googleapis.com/magentadata/js/checkpoints/music_vae/mel_2bar_small";
    musicVAE = new music_vae.MusicVAE(checkpoint);
    musicVAE
      .initialize()
      .then(() => {
        modelReady = true;
        modelStatus.textContent = "model: ready";
        modelStatus.classList.add("ready");
      })
      .catch(() => {
        modelStatus.textContent = "model: unavailable (using server fallback)";
      });
  }

  // ── Examples ───────────────────────────────────────────────────────────────
  function loadExamples() {
    fetch(API + "/api/examples")
      .then((r) => r.json())
      .then((data) => {
        (data.examples || []).forEach((ex) => {
          const chip = document.createElement("button");
          chip.className = "example-chip";
          chip.textContent = ex;
          chip.addEventListener("click", () => {
            promptInput.value = ex;
            updateCharCount();
            handleGenerate();
          });
          examplesBox.appendChild(chip);
        });
      })
      .catch(() => {
        /* examples are non-critical; ignore failures */
      });
  }

  // ── Helpers ──────────────────────────────────────────────────────────────
  function updateCharCount() {
    charCount.textContent = `${promptInput.value.length} / 200`;
  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  function clearError() {
    errorBox.hidden = true;
  }

  function setLoading(isLoading) {
    generateBtn.disabled = isLoading;
    generateBtn.classList.toggle("loading", isLoading);
  }

  // Convert the server's fallback note list into a Magenta NoteSequence.
  function notesToSequence(notes, qpm) {
    const secondsPerBeat = 60.0 / qpm;
    const seq = {
      notes: notes.map((n) => ({
        pitch: n.pitch,
        startTime: n.start * secondsPerBeat,
        endTime: (n.start + n.duration) * secondsPerBeat,
        velocity: n.velocity,
      })),
      totalTime:
        Math.max(...notes.map((n) => (n.start + n.duration))) *
        secondsPerBeat,
      tempos: [{ time: 0, qpm: qpm }],
    };
    return seq;
  }

  function renderParams(p) {
    resultParams.innerHTML = "";
    const items = [
      ["mood", p.descriptors.length ? p.descriptors.join(", ") : "neutral"],
      ["key", `${p.key} ${p.mode}`],
      ["tempo", `${p.bpm} bpm`],
      ["bars", p.bars],
      ["temp", p.temperature],
    ];
    items.forEach(([label, value]) => {
      const span = document.createElement("span");
      span.className = "param";
      span.innerHTML = `${label}: <strong>${value}</strong>`;
      resultParams.appendChild(span);
    });
  }

  function renderVisualizer(seq) {
    visualizer.innerHTML = "";
    const notes = seq.notes || [];
    const minP = Math.min(...notes.map((n) => n.pitch));
    const maxP = Math.max(...notes.map((n) => n.pitch));
    const range = Math.max(1, maxP - minP);
    notes.forEach((n) => {
      const bar = document.createElement("div");
      bar.className = "bar";
      const h = 10 + ((n.pitch - minP) / range) * 80;
      bar.style.height = h + "%";
      visualizer.appendChild(bar);
    });
  }

  // ── Generation flow ──────────────────────────────────────────────────────
  function handleGenerate() {
    const prompt = promptInput.value.trim();
    clearError();

    if (!prompt) {
      showError("Please describe a mood first.");
      return;
    }

    setLoading(true);

    fetch(API + "/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: prompt }),
    })
      .then((r) => r.json().then((body) => ({ ok: r.ok, body })))
      .then(({ ok, body }) => {
        if (!ok) {
          throw new Error(body.error || "Generation failed.");
        }
        currentParams = body.parameters;
        renderParams(body.parameters);

        // Default to the server fallback melody, always playable.
        const fallbackSeq = notesToSequence(
          body.fallback_notes,
          body.parameters.bpm
        );

        // Prepare the MIDI download from the server endpoint.
        prepareDownload(prompt);

        if (modelReady && musicVAE) {
          // Try to enrich with the in-browser MusicVAE model.
          musicVAE
            .sample(1, body.model_config.temperature)
            .then((samples) => {
              const modelSeq = samples[0];
              // Apply the requested tempo to the model output.
              modelSeq.tempos = [{ time: 0, qpm: body.parameters.bpm }];
              loadSequence(modelSeq, "Generated by the MusicVAE neural model.");
            })
            .catch(() => {
              loadSequence(
                fallbackSeq,
                "Generated by the server fallback composer."
              );
            })
            .finally(() => setLoading(false));
        } else {
          loadSequence(
            fallbackSeq,
            "Generated by the server fallback composer."
          );
          setLoading(false);
        }
      })
      .catch((err) => {
        setLoading(false);
        showError(err.message || "Something went wrong.");
      });
  }

  function loadSequence(seq, note) {
    currentSequence = seq;
    resultBox.hidden = false;
    playBtn.disabled = false;
    stopBtn.disabled = false;
    sourceNote.textContent = note;
    renderVisualizer(seq);
  }

  function prepareDownload(prompt) {
    // Lazily fetch the MIDI blob so Download is instant when clicked.
    downloadLink.onclick = function (e) {
      e.preventDefault();
      fetch(API + "/api/midi", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: prompt }),
      })
        .then((r) => r.blob())
        .then((blob) => {
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = "soundsketch.mid";
          a.click();
          URL.revokeObjectURL(url);
        })
        .catch(() => showError("Could not prepare the MIDI download."));
    };
  }

  // ── Playback (Tone.js) ───────────────────────────────────────────────────
  function ensureSynth() {
    if (!synth) {
      synth = new Tone.PolySynth(Tone.Synth).toDestination();
      synth.volume.value = -8;
    }
  }

  function play() {
    if (!currentSequence) return;
    ensureSynth();
    Tone.start();
    stop(); // clear anything already scheduled

    const now = Tone.now() + 0.1;
    const bars = visualizer.querySelectorAll(".bar");

    currentSequence.notes.forEach((n, i) => {
      const freq = Tone.Frequency(n.pitch, "midi").toFrequency();
      const dur = Math.max(0.1, n.endTime - n.startTime);
      synth.triggerAttackRelease(freq, dur, now + n.startTime);

      // Light up the matching visualizer bar.
      const id = setTimeout(() => {
        if (bars[i]) bars[i].classList.add("active");
      }, n.startTime * 1000);
      scheduled.push(id);
    });
  }

  function stop() {
    if (synth) synth.releaseAll();
    scheduled.forEach(clearTimeout);
    scheduled = [];
    visualizer.querySelectorAll(".bar.active").forEach((b) =>
      b.classList.remove("active")
    );
  }

  // ── Wire up events ───────────────────────────────────────────────────────
  promptInput.addEventListener("input", updateCharCount);
  promptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleGenerate();
  });
  generateBtn.addEventListener("click", handleGenerate);
  regenBtn.addEventListener("click", handleGenerate);
  playBtn.addEventListener("click", play);
  stopBtn.addEventListener("click", stop);

  // ── Boot ─────────────────────────────────────────────────────────────────
  updateCharCount();
  loadExamples();
  initModel();
})();
