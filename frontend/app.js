// ============================================================
// CrimeVision AI - Frontend Application
// File: frontend/app.js
// ============================================================

const API_BASE_URL = "http://127.0.0.1:5000/api";

const $ = (id) => document.getElementById(id);

let mode = "image";
let file = null;
let preview = null;
let result = {};

// ============================================================
// Configuration
// ============================================================

const cfg = {
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
        uploadSubtitle: "Speech, multilingual transcription, and event extraction",
        accept: "audio/*,.mp3,.wav,.m4a,.ogg,.flac"
    },

    video: {
        label: "Video",
        title: "Video Evidence Analysis",
        uploadTitle: "Upload Video",
        uploadSubtitle: "Video evidence and chronological event review",
        accept: "video/*,.mp4,.mov,.avi,.mkv,.webm"
    }
};

// ============================================================
// Safe HTML and data helpers
// ============================================================

function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[character]);
}

function val(object, keys, fallback = "—") {
    for (const key of keys) {
        let value = object;

        for (const part of key.split(".")) {
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

function arr(value) {
    if (Array.isArray(value)) {
        return value;
    }

    if (typeof value === "string" && value.trim()) {
        return value
            .split(/[,;\n]/)
            .map(item => item.trim())
            .filter(Boolean);
    }

    if (value && typeof value === "object") {
        return Object.values(value);
    }

    return [];
}

function readable(value, fallback = "—") {
    if (
        value === undefined ||
        value === null ||
        value === ""
    ) {
        return fallback;
    }

    if (typeof value === "object") {
        return JSON.stringify(value, null, 2);
    }

    return String(value);
}

function notice(message, type = "") {
    const element = $("notice");

    if (!element) return;

    element.textContent = message;
    element.className = "notice " + type;
}

// ============================================================
// Location formatting
// ============================================================

function inferLocationFromData(data) {
    if (!data) return null;

    const summary = String(
        val(
            data,
            [
                "visual_summary",
                "summary",
                "video_summary",
                "audio_summary",
                "caption_summary"
            ],
            ""
        )
    ).toLowerCase();

    const objects = arr(
        val(data, ["objects", "detected_objects", "object_summary"], [])
    );
    const objectLabels = objects.map(item => {
        if (typeof item === "string") return item.toLowerCase();
        if (item && item.label) return String(item.label).toLowerCase();
        return "";
    }).filter(Boolean);

    if (
        summary.includes("living room") ||
        summary.includes("lounge") ||
        objectLabels.includes("couch") ||
        objectLabels.includes("sofa")
    ) {
        return "Indoor (Living Room)";
    }

    if (
        summary.includes("bedroom") ||
        summary.includes("bed room") ||
        objectLabels.includes("bed")
    ) {
        return "Indoor (Bedroom)";
    }

    if (
        summary.includes("kitchen") ||
        summary.includes("dining") ||
        objectLabels.includes("refrigerator") ||
        objectLabels.includes("microwave") ||
        objectLabels.includes("oven") ||
        objectLabels.includes("dining table")
    ) {
        return "Indoor (Kitchen / Dining)";
    }

    if (
        summary.includes("office") ||
        summary.includes("desk") ||
        summary.includes("workspace") ||
        objectLabels.includes("laptop") ||
        objectLabels.includes("keyboard")
    ) {
        return "Indoor (Office / Workspace)";
    }

    if (
        summary.includes("store") ||
        summary.includes("shop") ||
        summary.includes("supermarket") ||
        summary.includes("market") ||
        summary.includes("counter")
    ) {
        return "Commercial (Store / Retail)";
    }

    if (
        summary.includes("street") ||
        summary.includes("road") ||
        summary.includes("highway") ||
        summary.includes("sidewalk") ||
        summary.includes("traffic") ||
        objectLabels.includes("traffic light") ||
        objectLabels.includes("stop sign")
    ) {
        return "Outdoor (Street / Roadway)";
    }

    if (
        summary.includes("park") ||
        summary.includes("garden") ||
        summary.includes("forest") ||
        summary.includes("field")
    ) {
        return "Outdoor (Park / Open Area)";
    }

    if (
        objectLabels.includes("car") ||
        objectLabels.includes("truck") ||
        objectLabels.includes("bus") ||
        objectLabels.includes("motorcycle")
    ) {
        return "Outdoor / Roadway (Vehicles)";
    }

    if (
        summary.includes("indoor") ||
        summary.includes("room") ||
        objectLabels.includes("chair") ||
        objectLabels.includes("tv") ||
        objectLabels.includes("clock")
    ) {
        return "Indoor (General Scene)";
    }

    return null;
}

function formatLocation(data) {
    let location = val(
        data,
        [
            "location",
            "scene_location",
            "detected_location",
            "forensic_analysis.location",
            "forensic_analysis.scene_location",
            "analysis.location",
            "visual_analysis.location"
        ],
        null
    );

    const isPlaceholder = (str) => {
        if (!str || typeof str !== "string") return true;
        const trimmed = str.trim();
        return (
            !trimmed ||
            trimmed === "—" ||
            trimmed === "-" ||
            /^not established/i.test(trimmed) ||
            /^location not established/i.test(trimmed) ||
            /^scene location unspecified/i.test(trimmed) ||
            /^scene unspecified/i.test(trimmed) ||
            /^unknown/i.test(trimmed)
        );
    };

    if (location === null || location === undefined || location === "") {
        const inferred = inferLocationFromData(data);
        return inferred || "Scene Unspecified";
    }

    if (typeof location === "string") {
        const cleaned = location.replace(/\s+/g, " ").trim();
        if (isPlaceholder(cleaned)) {
            const inferred = inferLocationFromData(data);
            return inferred || "Scene Unspecified";
        }
        return cleaned;
    }

    if (Array.isArray(location)) {
        const items = location
            .map(item => readable(item, ""))
            .filter(Boolean);

        if (items.length) {
            return items.join(", ");
        }
        const inferred = inferLocationFromData(data);
        return inferred || "Scene Unspecified";
    }

    if (typeof location === "object") {
        const parts = [];
        const keys = [
            "address",
            "building",
            "room",
            "area",
            "neighborhood",
            "city",
            "district",
            "state",
            "country",
            "description"
        ];

        for (const key of keys) {
            const value = location[key];
            if (
                value !== undefined &&
                value !== null &&
                typeof value !== "object" &&
                String(value).trim()
            ) {
                parts.push(String(value).trim());
            }
        }

        if (parts.length) {
            return [...new Set(parts)].join(", ");
        }

        if (location.description && !isPlaceholder(String(location.description))) {
            return String(location.description);
        }

        const inferred = inferLocationFromData(data);
        return inferred || "Scene Unspecified";
    }

    return String(location);
}

function setLocation(elementId, data) {
    const element = $(elementId);
    if (!element) return;

    element.textContent = formatLocation(data);

    // Make the value wrap naturally across the full width of the card.
    element.style.display = "block";
    element.style.width = "100%";
    element.style.minWidth = "0";
    element.style.whiteSpace = "normal";
    element.style.wordBreak = "normal";
    element.style.overflowWrap = "break-word";
    element.style.lineHeight = "1.4";
    element.style.fontSize = "13.5px";
    element.style.fontWeight = "700";
    element.style.color = "#ffffff";
    element.style.gridColumn = "1 / -1";
}

// ============================================================
// Mode selection
// ============================================================

function setMode(selectedMode) {
    if (!cfg[selectedMode]) return;

    mode = selectedMode;

    document.querySelectorAll(".nav").forEach(button => {
        button.classList.toggle(
            "active",
            button.dataset.mode === selectedMode
        );
    });

    document.querySelectorAll(".view").forEach(view => {
        view.classList.add("hidden");
    });

    const currentView = $(selectedMode + "View");

    if (currentView) {
        currentView.classList.remove("hidden");
    }

    $("kind").textContent = cfg[selectedMode].label;
    $("title").textContent = cfg[selectedMode].title;
    $("upTitle").textContent = cfg[selectedMode].uploadTitle;
    $("upSub").textContent = cfg[selectedMode].uploadSubtitle;
    $("file").accept = cfg[selectedMode].accept;

    $("file").value = "";
    $("filename").textContent = "No file selected";

    file = null;
    $("process").disabled = true;

    if (preview) {
        URL.revokeObjectURL(preview);
        preview = null;
    }
}

document.querySelectorAll(".nav").forEach(button => {
    button.addEventListener("click", () => {
        setMode(button.dataset.mode);
    });
});

// ============================================================
// File selection and preview
// ============================================================

$("file").addEventListener("change", event => {
    file = event.target.files?.[0] || null;

    if (!file) {
        $("filename").textContent = "No file selected";
        $("process").disabled = true;
        return;
    }

    $("filename").textContent = file.name;
    $("process").disabled = false;

    if (preview) {
        URL.revokeObjectURL(preview);
    }

    preview = URL.createObjectURL(file);

    if (mode === "image") {
        if ($("imageStage")) {
            $("imageStage").className = "stage";

            $("imageStage").innerHTML = `
                <img
                    src="${esc(preview)}"
                    alt="Evidence preview"
                    style="max-width:100%;max-height:650px;object-fit:contain;"
                >
            `;
        }

        if ($("imageMeta")) {
            $("imageMeta").textContent = file.name;
        }
    }

    if (mode === "video") {
        if ($("videoStage")) {
            $("videoStage").className = "stage";

            $("videoStage").innerHTML = `
                <video
                    controls
                    src="${esc(preview)}"
                    style="max-width:100%;max-height:650px;"
                ></video>
            `;
        }

        if ($("videoMeta")) {
            $("videoMeta").textContent = file.name;
        }
    }

    if (mode === "audio" && $("transcript")) {
        $("transcript").textContent =
            `Selected audio: ${file.name}\nStart processing to transcribe this recording.`;
    }
});

// ============================================================
// API request helper
// ============================================================

async function req(url, options = {}) {
    let response;

    try {
        response = await fetch(url, options);
    } catch (error) {
        throw new Error(
            "Cannot connect to the Flask backend. Check that backend/app.py is running on port 5000."
        );
    }

    const text = await response.text();

    let data = {};

    try {
        data = text ? JSON.parse(text) : {};
    } catch {
        data = { raw: text };
    }

    if (!response.ok || data.success === false) {
        throw new Error(
            data.error ||
            data.message ||
            data.raw ||
            `HTTP ${response.status}: ${response.statusText}`
        );
    }

    return data.result ?? data.data ?? data;
}

// ============================================================
// Display helpers
// ============================================================

function chips(elementId, value) {
    const element = $(elementId);

    if (!element) return;

    const items = arr(value);

    element.className = "chips";

    if (!items.length) {
        element.innerHTML =
            '<span class="muted">No data returned.</span>';
        return;
    }

    element.innerHTML = items.map(item => {
        const text = typeof item === "object"
            ? item.name ||
              item.label ||
              item.text ||
              item.description ||
              JSON.stringify(item)
            : item;

        return `<span class="fact">${esc(text)}</span>`;
    }).join("");
}

function facts(elementId, value) {
    if (!value) {
        chips(elementId, []);
        return;
    }

    if (
        !Array.isArray(value) &&
        typeof value === "object"
    ) {
        value = Object.entries(value).flatMap(([key, item]) => {
            const items = Array.isArray(item) ? item : [item];

            return items.map(entry => {
                const formatted = typeof entry === "object"
                    ? JSON.stringify(entry)
                    : entry;

                return `${key.replaceAll("_", " ")}: ${formatted}`;
            });
        });
    }

    chips(elementId, value);
}

// ============================================================
// Timeline rendering
// ============================================================

function timeline(elementId, value) {
    const element = $(elementId);

    if (!element) return;

    const events = arr(value);

    if (!events.length) {
        element.className = "timeline muted";
        element.textContent = "No timeline events returned.";
        return;
    }

    events.sort((a, b) => {
        const startA = Number(
            a.start_raw ?? a.start ?? a.timestamp ?? 0
        );

        const startB = Number(
            b.start_raw ?? b.start ?? b.timestamp ?? 0
        );

        return startA - startB;
    });

    element.className = "timeline";

    element.innerHTML = events.map(event => {
        const rawTime =
            event.start_raw ??
            event.start ??
            event.timestamp;

        const numericTime = Number(rawTime);

        let formattedTime = "—";

        if (
            rawTime !== undefined &&
            rawTime !== null &&
            rawTime !== "" &&
            Number.isFinite(numericTime)
        ) {
            const minutes = Math.floor(numericTime / 60);
            const seconds = Math.floor(numericTime % 60);

            formattedTime =
                `${String(minutes).padStart(2, "0")}:` +
                `${String(seconds).padStart(2, "0")}`;
        } else if (event.time) {
            formattedTime = event.time;
        }

        return `
            <div class="event">
                <div class="time">${esc(formattedTime)}</div>

                <div>
                    <span class="category">
                        ${esc(event.category || event.type || "Event")}
                    </span>

                    <b>
                        ${esc(
                            event.description ||
                            event.text ||
                            event.event ||
                            "Event details not provided."
                        )}
                    </b>

                    <small>
                        ${esc(
                            event.evidence_quote ||
                            "Review against original evidence."
                        )}
                    </small>
                </div>
            </div>
        `;
    }).join("");
}

// ============================================================
// Image results
// ============================================================

function renderImage(data) {
    $("imageSummary").textContent = readable(
        val(
            data,
            [
                "visual_summary",
                "summary",
                "scene_summary",
                "caption",
                "analysis.summary"
            ],
            "Analysis completed; no summary field returned."
        )
    );

    const objects = arr(
        val(
            data,
            ["objects", "detected_objects", "detections"],
            []
        )
    );

    $("objects").textContent = objects.length ||
        val(data, ["object_count"], "—");

    $("people").textContent = val(
        data,
        ["people_count", "person_count"],
        "—"
    );

    const weaponCount = val(
        data,
        ["weapon_count"],
        null
    );

    if (weaponCount !== null) {
        $("weapons").textContent = weaponCount;
    } else {
        const detectedWeapons = objects.filter(item =>
            /knife|gun|weapon|pistol|rifle/i.test(
                JSON.stringify(item)
            )
        ).length;

        $("weapons").textContent = detectedWeapons;
    }

    // IMPORTANT: Use the location formatting helper.
    setLocation("location", data);

    chips(
        "actions",
        val(data, ["actions", "actions_detected"], [])
    );

    facts(
        "facts",
        val(
            data,
            [
                "evidence_facts",
                "facts",
                "objects",
                "detected_objects"
            ],
            objects
        )
    );

    const scenarios = arr(
        val(
            data,
            [
                "hypotheses",
                "scenarios",
                "application_scenarios",
                "hypothesis_analysis.hypotheses"
            ],
            []
        )
    );

    $("scenarios").className = "scenarios";

    $("scenarios").innerHTML = scenarios.length
        ? scenarios.map((item, index) => `
            <div class="scenario">
                <b>
                    ${esc(
                        item.title ||
                        item.name ||
                        `Scenario ${index + 1}`
                    )}
                </b>

                <p>
                    ${esc(
                        item.description ||
                        item.hypothesis ||
                        item.summary ||
                        (
                            typeof item === "string"
                                ? item
                                : JSON.stringify(item)
                        )
                    )}
                </p>
            </div>
        `).join("")
        : "No scenarios returned.";
}

// ============================================================
// Audio results
// ============================================================

function renderAudio(data) {
    $("transcript").textContent = readable(
        val(data, ["transcript", "text"], "No transcript returned.")
    );

    $("translation").textContent =
        $("transcript").textContent;

    const segments = arr(
        val(data, ["segments", "chunks"], [])
    );

    $("audioMeta").textContent =
        `${segments.length} timestamped segments · Language: ` +
        readable(
            val(
                data,
                ["language", "detected_language"],
                "not specified"
            )
        );

    $("audioSummary").textContent = readable(
        val(
            data,
            [
                "summary",
                "ai_summary",
                "forensic_analysis.summary",
                "forensic_analysis.scene_type"
            ],
            "Audio analysis completed."
        )
    );

    const forensicFacts = val(
        data,
        [
            "forensic_analysis",
            "forensic_facts",
            "facts",
            "analysis"
        ],
        {}
    );

    $("eventType").textContent = readable(
        val(
            forensicFacts,
            ["event_type", "scene_type", "incident_type"],
            "Unclassified"
        )
    );

    setLocation("audioLocation", forensicFacts);

    facts("audioFacts", forensicFacts);

    timeline(
        "audioTimeline",
        val(
            data,
            ["timeline", "anchor_events", "events"],
            []
        )
    );
}

// ============================================================
// Video results
// ============================================================

function renderVideo(data) {
    $("videoSummary").textContent = readable(
        val(
            data,
            ["visual_summary", "summary", "video_summary"],
            "Video analysis completed."
        )
    );

    $("vObjects").textContent = arr(
        val(data, ["objects", "detected_objects"], [])
    ).map(item => {
        if (typeof item === "object") {
            return item.label || item.name || JSON.stringify(item);
        }

        return item;
    }).join(", ") || readable(val(data, ["object_count"]));

    $("vPeople").textContent = readable(
        val(data, ["people_count", "person_count"])
    );

    setLocation("vLocation", data);

    $("vAction").textContent = arr(
        val(data, ["actions", "actions_detected"], [])
    ).map(item => readable(item)).join(", ") || "—";

    timeline(
        "videoTimeline",
        val(data, ["timeline", "timeline_results", "events"], [])
    );
}

// ============================================================
// Render results
// ============================================================

function render(selectedMode, data) {
    result = data;

    if (selectedMode === "image") {
        renderImage(data);
    }

    if (selectedMode === "audio") {
        renderAudio(data);
    }

    if (selectedMode === "video") {
        renderVideo(data);
    }
}

// ============================================================
// Upload and analyze
// ============================================================

$("process").addEventListener("click", async () => {
    if (!file) {
        notice("Please select a file first.", "error");
        return;
    }

    const endpoints = {
        image: "/image/analyze",
        audio: "/audio/analyze",
        video: "/video/analyze"
    };

    const endpoint = endpoints[mode];

    $("process").disabled = true;

    notice("Uploading evidence and waiting for analysis...");

    try {
        const formData = new FormData();

        formData.append("file", file);

        const data = await req(
            API_BASE_URL + endpoint,
            {
                method: "POST",
                body: formData
            }
        );

        render(mode, data);

        $("conn").textContent = "Backend connected";

        notice(
            "Analysis finished. Verify generated findings against the original evidence.",
            "success"
        );
    } catch (error) {
        console.error("Evidence analysis error:", error);

        notice(
            `Analysis failed: ${error.message}`,
            "error"
        );
    } finally {
        $("process").disabled = !file;
    }
});

// ============================================================
// Chat
// ============================================================

$("chat").addEventListener("submit", async event => {
    event.preventDefault();

    const question = $("question").value.trim();

    if (!question) return;

    $("question").value = "";

    $("messages").insertAdjacentHTML(
        "beforeend",
        `<div class="bubble user">${esc(question)}</div>`
    );

    const loadingId = "chat-loading-" + Date.now();

    $("messages").insertAdjacentHTML(
        "beforeend",
        `<div class="bubble" id="${loadingId}">Thinking...</div>`
    );

    const loadingElement = $(loadingId);

    try {
        const data = await req(
            `${API_BASE_URL}/chat/${mode}`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    session_id: "CV-LOCAL-001",
                    question: question,
                    context: result
                })
            }
        );

        if (loadingElement) {
            loadingElement.textContent = readable(
                val(
                    data,
                    ["answer", "response", "message"],
                    "No answer was returned."
                )
            );
        }
    } catch (error) {
        console.error("Chat error:", error);

        if (loadingElement) {
            loadingElement.textContent =
                `Chat error: ${error.message}`;
        }
    }

    $("messages").scrollTop = $("messages").scrollHeight;
});

// ============================================================
// Export report
// ============================================================

function downloadFile(filename, content, mimeType) {
    const blob = new Blob(
        [content],
        { type: mimeType }
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = filename;

    document.body.appendChild(link);
    link.click();
    link.remove();

    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

$("json").addEventListener("click", () => {
    downloadFile(
        "crimevision-report.json",
        JSON.stringify(
            {
                case_id: "CV-LOCAL-001",
                mode: mode,
                generated_at: new Date().toISOString(),
                analysis: result
            },
            null,
            2
        ),
        "application/json"
    );
});

$("txt").addEventListener("click", () => {
    const content = [
        "CrimeVision AI Evidence Review",
        "Case: CV-LOCAL-001",
        `Mode: ${mode}`,
        `Generated: ${new Date().toLocaleString()}`,
        "",
        JSON.stringify(result, null, 2),
        "",
        "AI outputs are provisional and require independent verification."
    ].join("\n");

    downloadFile(
        "crimevision-summary.txt",
        content,
        "text/plain;charset=utf-8"
    );
});

// ============================================================
// Backend health check
// ============================================================

async function checkBackend() {
    const connection = $("conn");

    if (!connection) return;

    try {
        await req(`${API_BASE_URL}/health`);

        connection.textContent = "Backend connected (Online)";
        connection.classList.remove("disconnected");
    } catch (error) {
        connection.textContent = "Backend disconnected";
        connection.classList.add("disconnected");

        console.error("Backend health check failed:", error);
    }
}

// ============================================================
// Start application
// ============================================================

setMode("image");
checkBackend();

setInterval(checkBackend, 15000);