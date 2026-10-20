/* ============================================================
   CrimeVision AI — Frontend Application
   Backend: Flask
   API: http://127.0.0.1:5000/api
   ============================================================ */

"use strict";

/* -------------------- CONFIGURATION -------------------- */

const API_BASE_URL = window.location.protocol === "file:"
    ? "http://127.0.0.1:5000/api"
    : `${window.location.origin}/api`;

const $ = (id) => document.getElementById(id);

const CONFIG = {
    image: {
        label: "Image",
        title: "Image Evidence Analysis",
        uploadTitle: "Upload Image",
        uploadSubtitle: "Photos for evidence review",
        accept: "image/*"
    },

    audio: {
        label: "Audio",
        title: "Audio Evidence Analysis",
        uploadTitle: "Upload Audio",
        uploadSubtitle:
            "Speech transcription, multilingual analysis, and event extraction",
        accept: "audio/*,.mp3,.wav,.m4a,.ogg,.flac"
    },

    video: {
        label: "Video",
        title: "Video Evidence Analysis",
        uploadTitle: "Upload Video",
        uploadSubtitle:
            "Video evidence and chronological event review",
        accept: "video/*,.mp4,.mov,.avi,.mkv,.webm"
    }
};

let currentMode = "image";
let selectedFile = null;
let previewURL = null;
let currentResult = {};
let currentSessionId = null;
let isProcessing = false;


/* -------------------- UTILITY FUNCTIONS -------------------- */

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => {
        const entities = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        };

        return entities[character];
    });
}


function getValue(object, paths, fallback = "—") {
    for (const path of paths) {
        let value = object;

        for (const part of path.split(".")) {
            value = value?.[part];
        }

        if (
            value !== undefined &&
            value !== null &&
            value !== ""
        ) {
            return value;
        }
    }

    return fallback;
}


function toArray(value) {
    if (Array.isArray(value)) {
        return value;
    }

    if (typeof value === "string" && value.trim()) {
        return value
            .split(/[,;\n]/)
            .map((item) => item.trim())
            .filter(Boolean);
    }

    if (value && typeof value === "object") {
        return Object.values(value);
    }

    return [];
}


function showNotice(message, type = "") {
    const noticeElement = $("notice");

    if (!noticeElement) {
        console.log(message);
        return;
    }

    noticeElement.textContent = message;
    noticeElement.className = `notice ${type}`;
}


function setText(id, value, fallback = "—") {
    const element = $(id);

    if (!element) {
        return;
    }

    element.textContent =
        value === undefined ||
        value === null ||
        value === ""
            ? fallback
            : String(value);
}


function displayConnectionStatus(connected) {
    const element = $("conn");

    if (element) {
        element.textContent = connected
            ? "Backend connected (Online)"
            : "Backend disconnected (Offline)";
        const dot = element.parentElement ? element.parentElement.querySelector("i") : null;
        if (dot) {
            dot.style.background = connected ? "var(--green)" : "#ef4444";
        }
    }
}


function formatTimestamp(value) {
    if (value === undefined || value === null || value === "") {
        return "—";
    }

    // Support timestamps already formatted as HH:MM:SS.
    if (typeof value === "string" && value.includes(":")) {
        return value;
    }

    const seconds = Number(value);

    if (!Number.isFinite(seconds)) {
        return String(value);
    }

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = Math.floor(seconds % 60);

    if (hours > 0) {
        return [
            String(hours).padStart(2, "0"),
            String(minutes).padStart(2, "0"),
            String(remainingSeconds).padStart(2, "0")
        ].join(":");
    }

    return [
        String(minutes).padStart(2, "0"),
        String(remainingSeconds).padStart(2, "0")
    ].join(":");
}


/* -------------------- API REQUEST HANDLER -------------------- */

async function apiRequest(url, options = {}) {
    let response;

    try {
        response = await fetch(url, options);
    } catch (error) {
        displayConnectionStatus(false);

        throw new Error(
            "Cannot connect to the Flask backend. " +
            "Make sure backend/app.py is running on port 5000."
        );
    }

    const responseText = await response.text();

    let data = {};

    try {
        data = responseText
            ? JSON.parse(responseText)
            : {};
    } catch {
        data = {
            raw: responseText
        };
    }

    if (response.ok) {
        displayConnectionStatus(true);
    }

    if (!response.ok) {
        throw new Error(
            data.error ||
            data.message ||
            `HTTP ${response.status}: ${response.statusText}`
        );
    }

    if (data.success === false) {
        throw new Error(
            data.error ||
            data.message ||
            "The backend reported that analysis failed."
        );
    }

    // Support common Flask response structures.
    if (
        data.result !== undefined &&
        data.result !== null
    ) {
        return data.result;
    }

    if (
        data.data !== undefined &&
        data.data !== null
    ) {
        return data.data;
    }

    return data;
}


/* -------------------- MODE SWITCHING -------------------- */

function setMode(mode) {
    if (!CONFIG[mode]) {
        return;
    }

    currentMode = mode;

    document.querySelectorAll(".nav").forEach((button) => {
        button.classList.toggle(
            "active",
            button.dataset.mode === mode
        );
    });

    document.querySelectorAll(".view").forEach((view) => {
        view.classList.add("hidden");
    });

    const activeView = $(`${mode}View`);

    if (activeView) {
        activeView.classList.remove("hidden");
    }

    setText("kind", CONFIG[mode].label);
    setText("title", CONFIG[mode].title);
    setText("upTitle", CONFIG[mode].uploadTitle);
    setText("upSub", CONFIG[mode].uploadSubtitle);

    const fileInput = $("file");

    if (fileInput) {
        fileInput.accept = CONFIG[mode].accept;
        fileInput.value = "";
    }

    selectedFile = null;

    setText("filename", "No file selected");

    const processButton = $("process");

    if (processButton) {
        processButton.disabled = true;
    }

    if (previewURL) {
        URL.revokeObjectURL(previewURL);
        previewURL = null;
    }

    clearPreview();

    currentResult = {};
    currentSessionId = null;

    showNotice(
        `Ready for ${CONFIG[mode].label.toLowerCase()} evidence.`
    );

    clearChat();
}


function clearPreview() {
    const imageStage = $("imageStage");
    const videoStage = $("videoStage");

    if (imageStage) {
        imageStage.className = "stage";
        imageStage.innerHTML =
            '<div class="muted">Upload an image to preview evidence.</div>';
    }

    if (videoStage) {
        videoStage.className = "stage";
        videoStage.innerHTML =
            '<div class="muted">Upload a video to preview evidence.</div>';
    }

    setText("imageMeta", "No image loaded");
    setText("videoMeta", "No video loaded");

    setText("imageSummary", "Waiting for image analysis...");
    setText("videoSummary", "Waiting for video analysis...");
    setText("audioSummary", "Waiting for audio analysis...");

    setText("transcript", "Waiting for audio input...");
    setText("translation", "Waiting for transcription...");

    setText("objects", "—");
    setText("people", "—");
    setText("weapons", "—");
    setText("location", "—");

    setText("vObjects", "—");
    setText("vPeople", "—");
    setText("vLocation", "—");
    setText("vAction", "—");

    setText("eventType", "Unclassified");
    setText("audioLocation", "Not established");

    const player = $("audioPlayer");
    const playerContainer = $("audioPlayerContainer");
    if (player) {
        player.pause();
        player.removeAttribute("src");
    }
    if (playerContainer) {
        playerContainer.classList.add("hidden");
    }
}


function clearChat() {
    const messages = $("messages");

    if (messages) {
        messages.innerHTML = "";
    }
}


/* -------------------- NAVIGATION -------------------- */

document.querySelectorAll(".nav").forEach((button) => {
    button.addEventListener("click", () => {
        setMode(button.dataset.mode);
    });
});


/* -------------------- FILE UPLOAD AND PREVIEW -------------------- */

const fileInput = $("file");

if (fileInput) {
    fileInput.addEventListener("change", (event) => {
        const uploadedFile = event.target.files?.[0];

        if (!uploadedFile) {
            selectedFile = null;

            if ($("process")) {
                $("process").disabled = true;
            }

            setText("filename", "No file selected");

            return;
        }

        selectedFile = uploadedFile;

        setText("filename", uploadedFile.name);

        if ($("process")) {
            $("process").disabled = isProcessing;
        }

        if (previewURL) {
            URL.revokeObjectURL(previewURL);
        }

        previewURL = URL.createObjectURL(uploadedFile);

        if (currentMode === "image") {
            const stage = $("imageStage");

            if (stage) {
                stage.className = "stage";

                stage.innerHTML = `
                    <img
                        src="${escapeHTML(previewURL)}"
                        alt="Uploaded evidence preview"
                    >
                `;
            }

            setText("imageMeta", uploadedFile.name);
        }

        if (currentMode === "video") {
            const stage = $("videoStage");

            if (stage) {
                stage.className = "stage";

                stage.innerHTML = `
                    <video
                        controls
                        preload="metadata"
                        src="${escapeHTML(previewURL)}"
                    ></video>
                `;
            }

            setText("videoMeta", uploadedFile.name);
        }

        if (currentMode === "audio") {
            const player = $("audioPlayer");
            const playerContainer = $("audioPlayerContainer");
            if (player) {
                player.src = previewURL;
            }
            if (playerContainer) {
                playerContainer.classList.remove("hidden");
            }

            setText(
                "transcript",
                `Selected audio: ${uploadedFile.name}\n` +
                "Click Start Processing to transcribe this recording."
            );

            setText("audioSummary", "Audio is loaded and ready for AI transcription.");
        }

        showNotice(
            `${uploadedFile.name} selected. Ready to process.`
        );
    });
}


/* -------------------- EVIDENCE DISPLAY HELPERS -------------------- */

function renderChips(elementId, value) {
    const element = $(elementId);

    if (!element) {
        return;
    }

    const items = toArray(value);

    element.className = "chips";

    if (!items.length) {
        element.innerHTML =
            '<span class="muted">No data returned.</span>';

        return;
    }

    element.innerHTML = items.map((item) => {
        let label;

        if (typeof item === "object" && item !== null) {
            label =
                item.name ||
                item.label ||
                item.text ||
                item.description ||
                JSON.stringify(item);
        } else {
            label = item;
        }

        return `
            <span class="fact">
                ${escapeHTML(label)}
            </span>
        `;
    }).join("");
}


function renderFacts(elementId, value) {
    if (
        value &&
        typeof value === "object" &&
        !Array.isArray(value)
    ) {
        const flattened = Object.entries(value).flatMap(
            ([key, itemValue]) => {
                const values = Array.isArray(itemValue)
                    ? itemValue
                    : [itemValue];

                return values.map((item) => {
                    const readableKey = key.replaceAll("_", " ");

                    const readableValue =
                        typeof item === "object" &&
                        item !== null
                            ? JSON.stringify(item)
                            : item;

                    return `${readableKey}: ${readableValue}`;
                });
            }
        );

        renderChips(elementId, flattened);

        return;
    }

    renderChips(elementId, value);
}


/* -------------------- EVENT TIMELINE -------------------- */

function renderTimeline(elementId, events) {
    const element = $(elementId);

    if (!element) {
        return;
    }

    const eventList = toArray(events).filter(
        (event) => event && typeof event === "object"
    );

    if (!eventList.length) {
        element.className = "timeline muted";
        element.textContent = "No timeline events returned.";

        return;
    }

    eventList.sort((first, second) => {
        const firstTime = Number(
            first.start_raw ??
            first.start ??
            first.timestamp ??
            0
        );

        const secondTime = Number(
            second.start_raw ??
            second.start ??
            second.timestamp ??
            0
        );

        return firstTime - secondTime;
    });

    element.className = "timeline";

    element.innerHTML = eventList.map((event) => {
        const rawTime =
            event.start_raw ??
            event.start ??
            event.timestamp ??
            event.time;

        const time = formatTimestamp(rawTime);

        const category =
            event.category ||
            event.type ||
            event.event_type ||
            "Event";

        const description =
            event.description ||
            event.text ||
            event.event ||
            event.action ||
            "Event details not provided.";

        const evidence =
            event.evidence_quote ||
            event.evidence ||
            event.transcript ||
            "Review against the original evidence.";

        const numericTime = Number(rawTime ?? 0);
        return `
            <div class="event" data-time="${numericTime}" title="Click to seek media to ${escapeHTML(time)}">
                <div class="time">
                    ${escapeHTML(time)}
                </div>

                <div>
                    <span class="category">
                        ${escapeHTML(category)}
                    </span>

                    <b>
                        ${escapeHTML(description)}
                    </b>

                    <small>
                        ${escapeHTML(evidence)}
                    </small>
                </div>
            </div>
        `;
    }).join("");

    element.querySelectorAll(".event").forEach((eventEl) => {
        eventEl.addEventListener("click", () => {
            const time = parseFloat(eventEl.dataset.time);
            if (!Number.isFinite(time)) return;
            if (currentMode === "video") {
                const video = document.querySelector("#videoStage video");
                if (video) {
                    video.currentTime = time;
                    video.play().catch(() => {});
                    showNotice(`Media offset seeked to ${formatTimestamp(time)}`, "success");
                }
            } else if (currentMode === "audio") {
                const audio = $("audioPlayer");
                if (audio) {
                    audio.currentTime = time;
                    audio.play().catch(() => {});
                    showNotice(`Audio offset seeked to ${formatTimestamp(time)}`, "success");
                }
            }
        });
    });
}


/* -------------------- IMAGE ANALYSIS RENDERING -------------------- */

function renderImageResults(data) {
    const stage = $("imageStage");
    const rawObjects = getValue(data, ["objects", "detected_objects", "detections"], []);
    const objectsList = toArray(rawObjects);

    if (stage && previewURL) {
        const objectsWithBox = objectsList.filter(item => item && item.box && typeof item.box === "object" && item.box.xmin !== undefined);
        stage.className = "stage";
        stage.innerHTML = `
            <div class="bbox-wrapper" id="bboxWrapper">
                <img id="bboxImg" src="${escapeHTML(previewURL)}" alt="Visual Evidence">
                <div class="bbox-overlay" id="bboxOverlay"></div>
            </div>
        `;
        const img = $("bboxImg");
        const overlay = $("bboxOverlay");
        if (img && overlay && objectsWithBox.length) {
            const drawBoxes = () => {
                const nw = img.naturalWidth || img.width;
                const nh = img.naturalHeight || img.height;
                if (!nw || !nh) return;
                overlay.innerHTML = objectsWithBox.map(item => {
                    const b = item.box;
                    const left = Math.max(0, (b.xmin / nw) * 100);
                    const top = Math.max(0, (b.ymin / nh) * 100);
                    const width = Math.min(100 - left, ((b.xmax - b.xmin) / nw) * 100);
                    const height = Math.min(100 - top, ((b.ymax - b.ymin) / nh) * 100);
                    const label = item.label || "object";
                    const isWeapon = /knife|gun|weapon|firearm|pistol/i.test(label);
                    const conf = item.score ? ` ${(item.score * 100).toFixed(0)}%` : "";
                    return `
                        <div class="bbox-box ${isWeapon ? 'weapon' : ''}" style="left:${left.toFixed(2)}%;top:${top.toFixed(2)}%;width:${width.toFixed(2)}%;height:${height.toFixed(2)}%;">
                            <span class="bbox-label">${escapeHTML(label)}${conf}</span>
                        </div>
                    `;
                }).join("");
            };
            if (img.complete) {
                drawBoxes();
            } else {
                img.onload = drawBoxes;
            }
        }
    }
    const summary = getValue(data, [
        "visual_summary",
        "summary",
        "scene_summary",
        "caption",
        "analysis.summary",
        "forensic_analysis.summary"
    ], "Analysis completed; no summary was returned.");

    setText("imageSummary", summary);

    const objects = toArray(
        getValue(data, [
            "objects",
            "detected_objects",
            "detections",
            "evidence_facts.objects"
        ], [])
    );

    setText(
        "objects",
        getValue(data, ["object_count", "objects_count"], objects.length)
    );

    setText(
        "people",
        getValue(data, ["people_count", "person_count"], "—")
    );

    const weaponCount = objects.filter((item) => {
        const text = typeof item === "string"
            ? item
            : JSON.stringify(item);

        return /knife|gun|weapon|firearm/i.test(text);
    }).length;

    setText(
        "weapons",
        getValue(data, ["weapon_count"], weaponCount)
    );

    setText(
        "location",
        getValue(data, [
            "location",
            "scene_location",
            "detected_location"
        ], "Not established")
    );

    renderChips(
        "actions",
        getValue(data, [
            "actions",
            "actions_detected",
            "detected_actions"
        ], [])
    );

    renderFacts(
        "facts",
        getValue(data, [
            "evidence_facts",
            "facts",
            "objects",
            "detected_objects"
        ], objects)
    );

    const scenarios = toArray(
        getValue(data, [
            "hypotheses",
            "scenarios",
            "application_scenarios",
            "hypothesis_analysis.hypotheses"
        ], [])
    );

    const scenarioElement = $("scenarios");

    if (scenarioElement) {
        scenarioElement.className = "scenarios";

        if (!scenarios.length) {
            scenarioElement.textContent = "No scenarios returned.";
        } else {
            scenarioElement.innerHTML = scenarios.map(
                (scenario, index) => {
                    const title =
                        scenario.title ||
                        scenario.name ||
                        `Scenario ${index + 1}`;

                    const description =
                        scenario.description ||
                        scenario.hypothesis ||
                        scenario.summary ||
                        (typeof scenario === "string"
                            ? scenario
                            : JSON.stringify(scenario));

                    return `
                        <div class="scenario">
                            <b>${escapeHTML(title)}</b>
                            <p>${escapeHTML(description)}</p>
                        </div>
                    `;
                }
            ).join("");
        }
    }
}


/* -------------------- AUDIO ANALYSIS RENDERING -------------------- */

function renderAudioResults(data) {
    const transcript = getValue(data, [
        "transcript",
        "text",
        "full_transcript"
    ], "No transcript returned.");

    setText("transcript", transcript);
    setText("translation", transcript);

    const segments = toArray(
        getValue(data, ["segments", "chunks"], [])
    );

    const language = getValue(data, [
        "language",
        "detected_language"
    ], "not specified");

    setText(
        "audioMeta",
        `${segments.length} timestamped segments · Language: ${language}`
    );

    const facts = getValue(data, [
        "forensic_analysis",
        "forensic_facts",
        "facts",
        "analysis"
    ], {});

    setText(
        "audioSummary",
        getValue(data, [
            "summary",
            "ai_summary",
            "forensic_analysis.summary",
            "forensic_analysis.scene_type"
        ], "Audio analysis completed.")
    );

    setText(
        "eventType",
        getValue(facts, [
            "event_type",
            "scene_type",
            "incident_type",
            "facts.scene_type"
        ], "Unclassified")
    );

    setText(
        "audioLocation",
        getValue(facts, [
            "location",
            "scene_location",
            "facts.location"
        ], "Not established")
    );

    renderFacts("audioFacts", facts);

    renderTimeline(
        "audioTimeline",
        getValue(data, [
            "timeline",
            "anchor_events",
            "events"
        ], [])
    );
}


/* -------------------- VIDEO ANALYSIS RENDERING -------------------- */

function renderVideoResults(data) {
    setText(
        "videoSummary",
        getValue(data, [
            "visual_summary",
            "summary",
            "video_summary",
            "analysis.summary"
        ], "Video analysis completed.")
    );

    const objects = toArray(
        getValue(data, [
            "objects",
            "detected_objects",
            "object_summary"
        ], [])
    );

    setText(
        "vObjects",
        objects.length
            ? objects.map((item) => {
                if (typeof item === "object" && item !== null) {
                    return item.name || item.label || JSON.stringify(item);
                }

                return item;
            }).join(", ")
            : getValue(data, ["object_count"], "—")
    );

    setText(
        "vPeople",
        getValue(data, ["people_count", "person_count"], "—")
    );

    setText(
        "vLocation",
        getValue(data, ["location", "scene_location"], "—")
    );

    const actions = toArray(
        getValue(data, [
            "actions",
            "actions_detected"
        ], [])
    );

    setText(
        "vAction",
        actions.length
            ? actions.join(", ")
            : "—"
    );

    renderTimeline(
        "videoTimeline",
        getValue(data, [
            "timeline",
            "timeline_results",
            "events"
        ], [])
    );
}


/* -------------------- RENDER ANALYSIS RESULTS -------------------- */

function renderResults(mode, data) {
    currentResult = data;
    currentSessionId = data.session_id || null;

    if (mode === "image") {
        renderImageResults(data);
    }

    if (mode === "audio") {
        renderAudioResults(data);
    }

    if (mode === "video") {
        renderVideoResults(data);
    }
}


/* -------------------- START ANALYSIS -------------------- */

const processButton = $("process");

if (processButton) {
    processButton.addEventListener("click", async () => {
        if (!selectedFile || isProcessing) {
            return;
        }

        const endpoints = {
            image: "/image/analyze",
            audio: "/audio/analyze",
            video: "/video/analyze"
        };

        const endpoint = endpoints[currentMode];

        if (!endpoint) {
            showNotice("Invalid analysis mode.", "error");
            return;
        }

        isProcessing = true;
        processButton.disabled = true;

        showNotice(
            "Uploading evidence and waiting for AI analysis..."
        );

        try {
            const formData = new FormData();

            formData.append("file", selectedFile);

            const data = await apiRequest(
                API_BASE_URL + endpoint,
                {
                    method: "POST",
                    body: formData
                }
            );

            renderResults(currentMode, data);

            showNotice(
                "Analysis completed. Verify generated findings against the original evidence.",
                "success"
            );

        } catch (error) {
            console.error("Analysis failed:", error);

            showNotice(
                `Analysis failed: ${error.message}`,
                "error"
            );

        } finally {
            isProcessing = false;

            processButton.disabled = !selectedFile;
        }
    });
}


/* -------------------- AI CHAT -------------------- */

const chatForm = $("chat");

if (chatForm) {
    chatForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const questionInput = $("question");

        if (!questionInput) {
            return;
        }

        const question = questionInput.value.trim();

        if (!question) {
            return;
        }

        if (!currentSessionId) {
            showNotice("Analyze evidence before asking questions.", "error");
            return;
        }

        questionInput.value = "";

        const messages = $("messages");

        if (messages) {
            messages.insertAdjacentHTML(
                "beforeend",
                `<div class="bubble user">${escapeHTML(question)}</div>`
            );
        }

        try {
            const data = await apiRequest(
                `${API_BASE_URL}/chat/${currentMode}`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        session_id: currentSessionId,
                        question: question,
                        context: currentResult
                    })
                }
            );

            const answer = getValue(data, [
                "answer",
                "response",
                "message"
            ], JSON.stringify(data));

            if (messages) {
                messages.insertAdjacentHTML(
                    "beforeend",
                    `<div class="bubble">${escapeHTML(answer)}</div>`
                );
            }

        } catch (error) {
            console.error("Chat request failed:", error);

            if (messages) {
                messages.insertAdjacentHTML(
                    "beforeend",
                    `<div class="bubble">Chat error: ${escapeHTML(error.message)}</div>`
                );
            }
        }

        if (messages) {
            messages.scrollTop = messages.scrollHeight;
        }
    });
}


/* -------------------- REPORT DOWNLOADS -------------------- */

function downloadFile(filename, content, contentType) {
    const blob = new Blob(
        [content],
        { type: contentType }
    );

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");

    anchor.href = url;
    anchor.download = filename;

    document.body.appendChild(anchor);

    anchor.click();
    anchor.remove();

    setTimeout(() => {
        URL.revokeObjectURL(url);
    }, 1000);
}


const jsonButton = $("json");

if (jsonButton) {
    jsonButton.addEventListener("click", () => {
        const report = {
            case_id: "CV-LOCAL-001",
            mode: currentMode,
            generated_at: new Date().toISOString(),
            analysis: currentResult,
            disclaimer:
                "AI-generated findings are provisional and require independent verification."
        };

        downloadFile(
            "crimevision-report.json",
            JSON.stringify(report, null, 2),
            "application/json"
        );
    });
}


const textButton = $("txt");

if (textButton) {
    textButton.addEventListener("click", () => {
        const report = [
            "CrimeVision AI — Evidence Review",
            "Case: CV-LOCAL-001",
            `Mode: ${currentMode}`,
            `Generated: ${new Date().toLocaleString()}`,
            "",
            "ANALYSIS RESULTS",
            JSON.stringify(currentResult, null, 2),
            "",
            "DISCLAIMER",
            "AI-generated findings are provisional and require independent verification."
        ].join("\n");

        downloadFile(
            "crimevision-summary.txt",
            report,
            "text/plain;charset=utf-8"
        );
    });
}


/* -------------------- BACKEND HEALTH CHECK -------------------- */

async function checkBackend() {
    try {
        await apiRequest(
            `${API_BASE_URL}/health`,
            {
                method: "GET"
            }
        );

        displayConnectionStatus(true);

    } catch (error) {
        displayConnectionStatus(false);

        console.error(
            "Backend health check failed:",
            error.message
        );
    }
}


/* -------------------- INITIALIZE APPLICATION -------------------- */

document.addEventListener("DOMContentLoaded", () => {
    setMode("image");
    checkBackend();
});