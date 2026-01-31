const statusEl = document.getElementById("status");
const statusPill = document.getElementById("status-pill");
const transcriptEl = document.getElementById("transcript");
const eventsEl = document.getElementById("events");
const startBtn = document.getElementById("start");
const stopBtn = document.getElementById("stop");
const sessionStateEl = document.getElementById("session-state");
const eventCountEl = document.getElementById("event-count");
const transcriptCountEl = document.getElementById("transcript-count");
const clearTranscriptBtn = document.getElementById("clear-transcript");
const clearEventsBtn = document.getElementById("clear-events");

let transcriptLines = 0;
let eventLines = 0;

const ws = new WebSocket(`ws://${window.location.host}/ws`);

function append(el, text) {
  el.textContent = `${el.textContent}${text}\n`;
}

function setStatus(value) {
  statusEl.textContent = value;
  if (statusPill) {
    statusPill.classList.toggle("connected", value !== "disconnected");
  }
}

function appendTranscript(text) {
  append(transcriptEl, text);
  transcriptLines += 1;
  transcriptCountEl.textContent = transcriptLines;
}

function appendEvent(text) {
  append(eventsEl, text);
  eventLines += 1;
  eventCountEl.textContent = eventLines;
}

ws.addEventListener("open", () => {
  setStatus("connected");
  sessionStateEl.textContent = "Ready";
});

ws.addEventListener("close", () => {
  setStatus("disconnected");
  sessionStateEl.textContent = "Idle";
});

ws.addEventListener("message", (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "text") {
    appendTranscript(`Assistant: ${data.payload}`);
  } else if (data.type === "status") {
    appendEvent(`status: ${data.payload}`);
    setStatus(data.payload);
    sessionStateEl.textContent = data.payload;
  } else if (data.type === "error") {
    appendEvent(`error: ${data.payload}`);
  } else if (data.type === "turn_complete") {
    appendEvent("turn complete");
  } else {
    appendEvent(JSON.stringify(data));
  }
});

startBtn.addEventListener("click", () => {
  ws.send(JSON.stringify({ action: "start" }));
});

stopBtn.addEventListener("click", () => {
  ws.send(JSON.stringify({ action: "stop" }));
});

clearTranscriptBtn.addEventListener("click", () => {
  transcriptEl.textContent = "";
  transcriptLines = 0;
  transcriptCountEl.textContent = transcriptLines;
});

clearEventsBtn.addEventListener("click", () => {
  eventsEl.textContent = "";
  eventLines = 0;
  eventCountEl.textContent = eventLines;
});
