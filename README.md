# CrimeVision AI

### Intelligent Multimodal Forensic Analysis Platform

CrimeVision AI is an AI-assisted web application intended to help users
review digital evidence by analysing images, audio recordings, and video
footage. It combines computer vision, speech transcription, and
language-model-based analysis to organise extracted information into
findings and a chronological event timeline.

> **Important:** This application supports evidence review; it does not
> replace professional forensic examination. AI-generated detections,
> transcripts, classifications, and hypotheses may be incorrect and must
> be checked against the original evidence.

## Table of Contents

-   [Project Overview](#project-overview)
-   [Objectives](#objectives)
-   [Features](#features)
-   [Technology Stack](#technology-stack)
-   [Architecture](#architecture)
-   [Prerequisites](#prerequisites)
-   [Installation](#installation)
-   [Configuration](#configuration)
-   [Running the Application](#running-the-application)
-   [Workflow](#workflow)
-   [Testing](#testing)
-   [Troubleshooting](#troubleshooting)
-   [Security and Responsible Use](#security-and-responsible-use)
-   [Limitations](#limitations)
-   [Future Improvements](#future-improvements)
-   [License](#license)

## Project Overview

Investigations may involve photographs, video recordings, and spoken
statements. Reviewing these files manually can be time-consuming.
CrimeVision AI aims to provide a central workspace for submitting
supported media, running AI-assisted analysis, reviewing results, and
preparing structured findings.

Depending on the modules configured in the application, it can detect
supported objects in visual media, transcribe speech, extract candidate
events from text, and combine findings into a timeline.

## Objectives

-   Reduce repetitive manual effort when reviewing digital media.
-   Analyse images and video frames for supported objects and visual
    context.
-   Convert audio speech into text.
-   Extract candidate events and relevant details.
-   Organise observations into a chronological timeline.
-   Present results through a web dashboard and support report
    generation.
-   Keep original evidence available for human verification.

## Features

### Image Analysis

-   Upload supported image files.
-   Run configured object-detection models.
-   Generate scene descriptions when an image-captioning model is
    configured.
-   Display available detections and analysis results.

### Audio Analysis

-   Load supported audio files.
-   Use FFmpeg for decoding or format handling when required.
-   Use Whisper for speech-to-text transcription.
-   Extract candidate events from transcripts when the configured
    language-model integration is available.

### Video Analysis

-   Process video files and extract frames.
-   Analyse frames using configured computer-vision models.
-   Associate observations with timestamps when supported.
-   Organise candidate events into a time-based view.

### Multimodal Analysis and Reporting

-   Bring together available image, audio, and video findings.
-   Use a configured language model for structured extraction or
    natural-language queries, if implemented.
-   Present candidate events chronologically.
-   Generate or export reports if the feature is enabled in the current
    build.

> Feature availability depends on the models, API credentials, backend
> routes, and interface components in the actual repository.

## Technology Stack

  -----------------------------------------------------------------------
  Component               Technology              Purpose
  ----------------------- ----------------------- -----------------------
  Backend/API             Python, Flask           Application logic and
                                                  API endpoints

  Image/video processing  OpenCV                  Image handling and
                                                  video-frame extraction

  Deep-learning inference PyTorch                 Running compatible AI
                                                  models

  Object detection        RT-DETR or configured   Detecting supported
                          detector                objects

  Image captioning        BLIP, GIT, Florence, or Describing visual
                          configured alternative  scenes

  Audio transcription     OpenAI Whisper          Converting speech to
                                                  text

  Media utilities         FFmpeg / FFprobe        Decoding and inspecting
                                                  media

  Language-model analysis Groq API or configured  Event extraction and
                          provider                natural-language
                                                  analysis

  3D visualisation        Three.js, if enabled    Interactive
                                                  visualisation

  Development             Visual Studio Code      Development and
                                                  debugging
  -----------------------------------------------------------------------

This table describes the referenced or planned stack. Verify the actual
dependencies and integrations in the repository.

## Architecture

``` text
Investigator
    |
    v
CrimeVision AI Web Interface
    |
    v
Flask Backend / API
    |
    +-------------------+-------------------+
    |                   |                   |
    v                   v                   v
Image Pipeline      Audio Pipeline      Video Pipeline
Object detection    FFmpeg + Whisper    Frame extraction
Scene description   Transcript          Visual analysis
    |                   |                   |
    +-------------------+-------------------+
                        |
                        v
              Multimodal / LLM Analysis
                        |
                        v
             Structured Events and Timeline
                        |
                        v
              Results / Forensic Report
```

This is a conceptual diagram. Adjust it if the implemented application
uses a different frontend, database, or processing design.

## Prerequisites

-   Python 3.9 or later, compatible with the project's dependencies.
-   Git, if cloning the repository.
-   Visual Studio Code or another Python development environment.
-   FFmpeg and FFprobe available on the system `PATH` for media
    processing that requires them.
-   Internet access for dependency installation and external AI
    services, where applicable.
-   An API key for the configured language-model provider, if required.
-   Sufficient memory and disk space for the selected models and files.

Check versions in PowerShell:

``` powershell
python --version
pip --version
ffmpeg -version
ffprobe -version
```

FFmpeg downloads: https://ffmpeg.org/download.html

If `ffmpeg` or `ffprobe` is not recognised, install a Windows build and
add the directory containing the executables to `PATH`. Open a new
terminal after changing `PATH`.

## Installation

### 1. Get the source code

If you have access to the Git repository:

``` bash
git clone <YOUR_REPOSITORY_URL>
cd CrimeVision-AI-Intelligent-Multimodal-Forensic-Analysis-Platform
```

If the project already exists on your computer, open that folder
instead.

### 2. Open the backend directory

If your repository contains a `backend` folder:

``` powershell
cd backend
```

Run the following commands from the directory containing the backend
dependency file.

### 3. Create and activate a virtual environment

``` powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use Command Prompt:

``` bat
venv\Scripts\activate.bat
```

### 4. Install dependencies

If `requirements.txt` exists in the current directory:

``` powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If the file is elsewhere, use its actual path. If no dependency file
exists, check the repository's setup instructions rather than installing
packages at random.

## Configuration

Create a `.env` file only if the application is configured to load one.
For example:

``` dotenv
GROQ_API_KEY=your_api_key_here
```

Use the exact environment-variable names expected by your code. Never
commit `.env` files, API keys, credentials, private evidence, or
generated reports. Add them to `.gitignore`.

Before starting, verify the backend entry point, model names and
weights, upload directory, accepted file formats, API settings, and any
database configuration. Confirm FFmpeg is available from the same
environment used to start the backend.

## Running the Application

Activate the virtual environment and start the backend using the command
appropriate for your repository. For example, if the entry point is
`app.py`:

``` powershell
python app.py
```

Use the actual entry point if it differs. Read the terminal output for
the local address and any startup errors, then open that address in a
browser. If the project has a separate frontend, follow its own setup
instructions and run it in a separate terminal.

## Typical Workflow

1.  Create or select a case if case management is implemented.
2.  Upload supported image, audio, or video evidence.
3.  Select the relevant analysis module and start processing.
4.  Review detections, scene descriptions, transcripts, and extracted
    events.
5.  Inspect timestamps and context against the original media.
6.  Combine findings into a timeline if multimodal fusion is enabled.
7.  Generate a report if report generation is available.
8.  Verify important claims against the original evidence before relying
    on them.

### Suggested test cases

  -----------------------------------------------------------------------
  Test                    Input                   Check
  ----------------------- ----------------------- -----------------------
  Image analysis          A non-sensitive sample  Upload succeeds and
                          image                   image pipeline returns
                                                  results

  Audio analysis          A short, clear speech   Audio loads and
                          recording               transcription is
                                                  returned

  Video analysis          A short sample video    Video opens and frames
                                                  are processed

  Timeline                A sample with known     Events are ordered and
                          events and timestamps   timestamps are
                                                  plausible

  Error handling          Unsupported or corrupt  Application displays a
                          file                    useful error
  -----------------------------------------------------------------------

Use public, licensed, synthetic, or consented sample media for
development tests.

## Testing

Run tests included in the repository. If `pytest` is installed and tests
are configured, a typical command is:

``` powershell
python -m pytest
```

Potential areas to test include upload validation, missing FFmpeg
handling, transcription responses, model failures, timestamp ordering,
API errors, and report generation. Do not claim tests pass unless you
have run them and reviewed the results.

## Troubleshooting

### `ffmpeg was not found`

1.  Run `ffmpeg -version` and `ffprobe -version` in the terminal used to
    launch the backend.
2.  Ensure the folder containing the executables is on `PATH`.
3.  Restart the terminal and backend after updating `PATH`.
4.  Check what Python can locate:

``` powershell
python -c "import shutil; print('ffmpeg:', shutil.which('ffmpeg')); print('ffprobe:', shutil.which('ffprobe'))"
```

If either result is `None`, the backend environment cannot find the
executable. Correct `PATH` or configure the media library with an
explicit executable path if supported.

### Audio transcription fails

-   Confirm the format is supported and the file is readable.
-   Confirm FFmpeg and FFprobe are available.
-   Check the backend terminal for the full error.
-   Confirm Whisper and its dependencies are installed.

### Language-model analysis fails

-   Verify the API key and expected environment-variable name.
-   Check network access, provider availability, rate limits, and model
    configuration.
-   Never print API keys when debugging.

## Security and Responsible Use

-   Process only media you are authorised to use.
-   Treat evidence and reports as sensitive information.
-   Restrict access to case files and reports.
-   Validate file types, content, file sizes, and uploads on the server.
-   Keep credentials out of source control.
-   Preserve original files and follow appropriate chain-of-custody
    procedures.
-   Record model versions and processing settings when reproducibility
    matters.
-   Treat detections, transcripts, timestamps, and generated hypotheses
    as fallible.
-   Do not treat an AI-generated hypothesis as proof of criminal
    activity or identity.

## Limitations

-   Accuracy depends on media quality and model capabilities.
-   Transcription may struggle with noise, overlapping speakers,
    accents, or poor recordings.
-   Object detectors may miss objects or produce false detections.
-   Frame-based video analysis may miss actions between sampled frames.
-   Language models may generate unsupported statements.
-   Cross-media synchronisation requires reliable timestamps and an
    implemented alignment method.
-   Performance depends on hardware, model size, media duration, and
    external API availability.
-   Not every feature described here is necessarily enabled in every
    build.

## Future Improvements

-   Case management and role-based access control.
-   Evidence hashing and audit logs.
-   Improved audio/video timestamp alignment.
-   Configurable models and confidence thresholds.
-   More comprehensive automated tests.
-   Background processing for large media files.
-   Progress indicators and clearer error messages.
-   Reports containing evidence references and model metadata.
-   Deployment, monitoring, and backup documentation.

## Contributing

1.  Create a branch for your change.
2.  Keep secrets and sensitive evidence out of commits.
3.  Add tests for new functionality.
4.  Document new dependencies and configuration variables.
5.  Verify error handling and access controls.
6.  Describe the changes and tests performed when submitting a
    contribution.

## License

Add the project's chosen license before publishing or distributing the
repository. Until a license is included, do not assume others have
permission to reuse or redistribute the code.

## Resources

-   Python: https://www.python.org/
-   Flask: https://flask.palletsprojects.com/
-   OpenCV: https://opencv.org/
-   PyTorch: https://pytorch.org/
-   FFmpeg: https://ffmpeg.org/
-   Whisper: https://github.com/openai/whisper
-   Three.js: https://threejs.org/

Update this README to match the exact dependency versions, commands,
models, database, and features in the final repository before treating
it as definitive documentation.
