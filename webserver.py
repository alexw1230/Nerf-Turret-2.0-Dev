from flask import Flask, render_template_string, jsonify
import RPi.GPIO as GPIO
import time

# --------------------
# GPIO setup
# --------------------
INPUT_PIN = 27     # reads state
OUTPUT_PIN = 17    # controlled by button

GPIO.setmode(GPIO.BCM)
GPIO.setup(INPUT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(OUTPUT_PIN, GPIO.OUT)
GPIO.output(OUTPUT_PIN, GPIO.LOW)

# --------------------
# Flask setup
# --------------------
app = Flask(__name__)

# --------------------
# HTML + JS
# --------------------
HTML = """
<!doctype html>
<title>GPIO Control</title>

<style>
body {
    margin: 0;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: Arial, sans-serif;
    background-color: #f2f2f2;
}

.container {
    text-align: center;
    width: 100%;
}

#status-box {
    width: 200px;
    height: 200px;
    background-color: red;
    border: 4px solid black;
    margin: 30px auto;
    border-radius: 12px;
}

#hold-btn {
    width: 90vw;
    max-width: 600px;
    height: 140px;
    font-size: 36px;
    border-radius: 16px;
    border: none;
    background-color: red;
    color: white;
    cursor: pointer;
}

#hold-btn:active {
    background-color: #555;
    transform: scale(0.98);
}

.controls {
    margin-top: 30px;
}

label {
    font-size: 20px;
}

input[type="range"] {
    width: 80%;
}
</style>

<div class="container">
    <h1>Tracking Status</h1>
    <div id="status-box"></div>

    <h1>Manual Fire</h1>
    <button id="hold-btn">FIRE</button>

    <div class="controls">
        <p>
            <label>
                <input type="checkbox" id="autoToggle">
                Automatic Fire
            </label>
        </p>

        <p>
            Track Time Before Firing:
            <span id="sliderVal">1.0</span>s
        </p>
        <input type="range" id="timeSlider"
               min="0.5" max="5" step="0.5" value="1">
    </div>
</div>

<script>
const box = document.getElementById("status-box");
const btn = document.getElementById("hold-btn");
const toggle = document.getElementById("autoToggle");
const slider = document.getElementById("timeSlider");
const sliderVal = document.getElementById("sliderVal");

sliderVal.textContent = slider.value;

let greenStart = null;
let autoHolding = false;

// ----------------------
// Status polling
// ----------------------
function updateStatus() {
    fetch("/status")
        .then(r => r.json())
        .then(data => {
            const isGreen = data.state;

            if (!toggle.checked) {
                // Auto off: normal behavior
                box.style.backgroundColor = isGreen ? "green" : "red";
                greenStart = null;
                return;
            }

            const now = Date.now();

            if (isGreen) {
                if (!greenStart) {
                    greenStart = now;
                }

                const elapsed = (now - greenStart) / 1000;

                if (elapsed >= slider.value && !autoHolding) {
                    fetch("/on", {method: "POST"});
                    autoHolding = true;
                    box.style.backgroundColor = "green"; // auto holding active
                } else if (!autoHolding) {
                    box.style.backgroundColor = "yellow"; // waiting for slider time
                }
            } else {
                greenStart = null;
                if (autoHolding) {
                    fetch("/off", {method: "POST"});
                    autoHolding = false;
                }
                box.style.backgroundColor = "red"; // input off
            }
        });
}

setInterval(updateStatus, 200);

// ----------------------
// Manual hold button
// ----------------------
btn.addEventListener("mousedown", () => {
    if (!toggle.checked) fetch("/on", {method: "POST"});
});
btn.addEventListener("mouseup", () => {
    if (!toggle.checked) fetch("/off", {method: "POST"});
});
btn.addEventListener("mouseleave", () => {
    if (!toggle.checked) fetch("/off", {method: "POST"});
});

// Touch support
btn.addEventListener("touchstart", () => {
    if (!toggle.checked) fetch("/on", {method: "POST"});
});
btn.addEventListener("touchend", () => {
    if (!toggle.checked) fetch("/off", {method: "POST"});
});

// ----------------------
// Toggle + slider logic
// ----------------------
toggle.addEventListener("change", () => {
    slider.disabled = toggle.checked;
    greenStart = null;

    if (!toggle.checked && autoHolding) {
        fetch("/off", {method: "POST"});
        autoHolding = false;
    }
});

slider.addEventListener("input", () => {
    sliderVal.textContent = slider.value;
});
</script>
"""

# --------------------
# Routes
# --------------------
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/status")
def status():
    state = GPIO.input(INPUT_PIN)
    return jsonify({"state": bool(state)})

@app.route("/on", methods=["POST"])
def on():
    GPIO.output(OUTPUT_PIN, GPIO.HIGH)
    return ("", 204)

@app.route("/off", methods=["POST"])
def off():
    GPIO.output(OUTPUT_PIN, GPIO.LOW)
    return ("", 204)

# --------------------
# Run
# --------------------
if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000)
    finally:
        GPIO.cleanup()

