
## Team Members

- [Aayan Mathur](https://github.com/aayanmathur)
- [Aden Juda](https://github.com/yungsemitone)
- [Eason Huang](https://github.com/GILGAMESH605)
- [Luna Suzuki](https://github.com/lunasuzuki)
- [Zeba Shafi](https://github.com/Zeba-Shafi)

[![web-app lint](https://img.shields.io/github/actions/workflow/status/swe-students-fall2025/4-containers-randomaccessmemories/lint.yml?branch=main&label=web-app%20lint)](https://github.com/swe-students-fall2025/4-containers-randomaccessmemories/actions/workflows/lint.yml)
[![machine-learning-client lint](https://img.shields.io/github/actions/workflow/status/swe-students-fall2025/4-containers-randomaccessmemories/lint.yml?branch=main&label=machine-learning-client%20lint)](https://github.com/swe-students-fall2025/4-containers-randomaccessmemories/actions/workflows/lint.yml)

# Notely

Notely is an audio-first knowledge capture system. The Flask web app lets teammates upload or record short voice memos, stores the raw audio in MongoDB GridFS, and turns every recording into searchable, structured notes by calling OpenAI-powered speech-to-text and natural-language models. A background machine-learning client continuously polls MongoDB for new jobs and enriches each memo with transcripts, summaries, keywords, and action items so teams never lose track of what was said.

## Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Running with Docker Compose](#running-with-docker-compose)
- [Running Services Individually](#running-services-individually)
- [API Surface](#api-surface)
- [Data Model](#data-model)
- [Testing & Quality](#testing--quality)
- [Troubleshooting](#troubleshooting)
- [Team](#team)
- [License](#license)

## Overview

### Key capabilities

- Upload audio in common formats (wav, mp3, ogg, webm, m4a, mp4) and persist it in MongoDB via GridFS with file-size validation.
- Automatically transcribe recordings with OpenAI Speech-to-Text and generate summaries, highlights, keywords, and action items using GPT-based text models.
- Browse recent recordings, view status, drill into details, and search notes by keyword or transcript snippets via REST endpoints (and the included Jinja templates).
- Deploy everything as coordinated Docker containers or run the subsystems independently with Pipenv.

### Tech stack

- **Web app:** Flask 3, Flask-CORS, PyMongo, GridFS, Jinja templates, OpenAI Python SDK.
- **Machine-learning client:** Python 3.12 service with Poller loop, PyMongo, GridFS, and custom OpenAI STT/NLP wrappers.
- **Database:** MongoDB 7 running in its own container with a dedicated Docker volume for persistence.
- **Tooling:** Docker Compose, Pipenv for dependency locking, Pytest + Coverage for tests, and GitHub Actions lint workflow (Black + pylint) for both subsystems.

## Architecture

Three containers make up the deployment: (1) the Flask web experience and REST API, (2) the machine-learning worker, and (3) MongoDB with GridFS storage. The web app writes recording metadata and binary audio blobs, while the worker continuously polls for `pending` documents, downloads the audio, calls OpenAI to transcribe/summarize, and writes results back so the UI and API can surface structured notes. If you set `PROCESS_INLINE=true`, the web app can do the STT/NLP work immediately for demo mode, but the default flow keeps the workloads isolated in the ML container.

```text
[Browser / REST client] --(multipart upload)--> [Flask Web App]
        |                                              |
        |                                      stores audio + metadata
        |                                              v
        |                                     MongoDB + GridFS
        |                                              |
        |<--- notes/search JSON -----------------------|
                                                       |
                                               [Machine-learning client]
                                                       |
                                      OpenAI STT + GPT summaries -> MongoDB notes
```

## Repository Layout

```text
.
├── docker-compose.yml         # Spins up MongoDB, machine-learning client, and web app
├── .env.example               # Copy to .env and fill in credentials + API keys
├── machine-learning-client/
│   ├── app/                   # Poller, db helpers, OpenAI STT/NLP adapters, CLI entrypoint
│   ├── test/                  # Pytest suites (main loop, poller logic, NLP parser)
│   └── Dockerfile             # Python 3.12 slim image with Pipenv install
├── web-app/
│   ├── app/                   # Flask factory, routes, storage helpers, OpenAI services
│   ├── templates/             # Dashboard, upload, detail, and supporting CSS
│   ├── tests/                 # Storage/search unit tests
│   └── Dockerfile             # Python 3.12 slim image with Pipenv install
└── instructions.md            # Assignment brief / grading rubric
```

## Prerequisites

- Docker Desktop 4.x (or Docker Engine 24+) with the Compose plugin.
- Python 3.12+ and [Pipenv](https://pipenv.pypa.io/) if you plan to run or develop subsystems outside containers.
- An OpenAI API key that has access to both audio transcription and chat-completions models (usage incurs OpenAI charges).
- Optional: `mongosh` for inspecting MongoDB locally.

## Configuration

All services read environment variables from `.env` (when running via Compose or Pipenv + python-dotenv). Start by copying the template and filling in the blanks:

```bash
cp .env.example .env
```

Never commit the populated `.env`. When developing outside Docker, either copy the `.env` file into each subsystem directory or set `PIPENV_DOTENV_LOCATION=../.env` before running Pipenv commands so both apps load the shared configuration.

### Core settings

| Variable | Required? | Description | Default |
| --- | --- | --- | --- |
| `MONGO_HOST` | No | Hostname the containers use to reach MongoDB. | `mongodb` |
| `MONGO_PORT` | No | Port exposed from MongoDB to the host. | `27017` |
| `MONGO_DB` | No | Database name used by both services. | `audio_notes` |
| `MONGO_USER` | Yes (when using Compose) | Admin/root username seeded in the Mongo container and used by clients. | `admin` |
| `MONGO_PASSWORD` | Yes | Password for the Mongo admin user. | `adminpassword` |
| `MONGO_URI` | Optional | Full MongoDB URI override (takes precedence over host/port). Useful for Atlas or remote instances. | derived from the values above |
| `PROCESS_INLINE` | No | When `true`, the web app performs STT/NLP as soon as a file uploads. Leave `false` to offload work to the ML container. | `false` |
| `MAX_FILE_MB` | No | Maximum upload size enforced by the web app. | `10` |
| `WEB_PORT` | No | Host port forwarded to the Flask container (Compose only). | `5050` |
| `FLASK_SECRET_KEY` | Yes in production | Flask session/CSRF secret. Generate a long random value before deploying. | `dev-secret-key` |
| `FLASK_DEBUG` | No | Set to `0` in production to disable debug mode. | `1` |

### OpenAI settings

| Variable | Used by | Description | Default |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | Web + ML containers | Required API key for both speech and text calls. |
| `OPENAI_BASE_URL` | Web + ML containers | Optional custom endpoint (e.g., Azure OpenAI) if you are not using the public API. | unset |
| `OPENAI_MODEL` | Machine-learning client | GPT model used for structured note generation. | `gpt-4o-mini` |
| `OPENAI_MAX_TOKENS` | Machine-learning client | Max tokens for the NLP summary response. | `1024` |
| `OPENAI_STT_MODEL` | Machine-learning client | Audio model for STT (`transcribe` endpoint). | `gpt-4o-transcribe` |
| `OPENAI_TRANSCRIBE_MODEL` | Web app (inline mode) | Audio transcription model when `PROCESS_INLINE=true` (e.g., `gpt-4o-mini-transcribe`). | Required when inline processing |
| `OPENAI_TEXT_MODEL` | Web app (inline mode) | Chat completion model for summary/keywords (e.g., `gpt-4o-mini`). | Required when inline processing |

Keep your API key secret and rotate it periodically. You can set additional provider-specific environment variables (like `OPENAI_ORG_ID`) if needed; both subsystems lazily configure the OpenAI client on startup.

## Running with Docker Compose

1. **Clone the repo**

   ```bash
   git clone https://github.com/swe-students-fall2025/4-containers-randomaccessmemories.git
   cd 4-containers-randomaccessmemories
   ```

2. **Prepare configuration**

   ```bash
   cp .env.example .env
   # edit .env with your Mongo credentials + OpenAI key
   ```

3. **Build and launch the stack**

   ```bash
   docker compose up --build
   ```

   Compose starts MongoDB first, then the machine-learning client, then the Flask web app. Logs are auto-streamed to your terminal; open a second terminal and tail specific services with `docker compose logs -f web-app` or `docker compose logs -f machine-learning-client`.

4. **Use the app**

   - Web UI / REST API: [http://localhost:${WEB_PORT:-5050}](http://localhost:5050)
   - MongoDB: `mongodb://MONGO_USER:MONGO_PASSWORD@localhost:27017/MONGO_DB?authSource=admin`
   - Upload audio via the `/upload` endpoint or by wiring the templates into your preferred front end.

5. **Stop and clean up**

   ```bash
   docker compose down               # stop services, keep Mongo volume
   docker compose down -v            # stop and delete the mongo_data volume
   ```

   MongoDB data and uploaded audio persist inside the `mongo_data` Docker volume until you remove it.

## Running Services Individually

Running subsystems without Compose is helpful for local debugging. Make sure MongoDB is available (e.g., `docker compose up mongodb`) and export the same environment variables defined in `.env` (Pipenv automatically loads a `.env` that lives in the same directory as the Pipfile, so copy or symlink the root `.env` if needed).

### Web app (Flask)

```bash
cd web-app
pipenv install --dev
pipenv run flask --app app:create_app run --host 0.0.0.0 --port 5000
```

The Flask server enforces the `MAX_FILE_MB` limit and writes uploads to MongoDB/ GridFS. Use `pipenv run flask --app app:create_app shell` for quick PyMongo debugging.

### Machine-learning client

```bash
cd machine-learning-client
pipenv install --dev
pipenv run python -m app.main --interval 5
# or run once for debugging
pipenv run python -m app.main --once --log-level DEBUG
```

The client polls the `recordings` collection for `status="pending"`, downloads audio, calls `_safe_transcribe` and `_safe_generate_notes`, and persists transcripts/notes. Adjust `--interval` (seconds between polling) based on your workload.

### MongoDB access

Use `mongosh "mongodb://MONGO_USER:MONGO_PASSWORD@localhost:27017/admin"` to inspect collections manually. Records appear in `recordings`, `notes`, `transcriptions`, and `structured_notes`, while raw audio files are stored in the `fs.files`/`fs.chunks` GridFS collections.

## API Surface

The Flask blueprint (`web-app/app/routes.py`) exposes REST endpoints that the dashboard (or any client) can call:

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Health check that returns `"Audio Note Web App is running!"`. |
| `POST` | `/upload` | Accepts `multipart/form-data` with `file`. Saves audio to GridFS, creates a `recordings` document, and optionally processes inline. Returns `{"recording_id": "<ObjectId>"}`. |
| `GET` | `/notes` | Returns the latest 50 recordings with summarized note snippets for dashboards. |
| `GET` | `/notes/<recording_id>` | Detailed note payload (timestamps, status, transcript, keywords, action items). |
| `GET` | `/search?q=term` | Case-insensitive search across transcript + keywords (transcript text omitted in results by default). |
| `POST` | `/process/<recording_id>` | Force re-processing of an existing recording using the inline pipeline—handy when `PROCESS_INLINE=false` but you want an immediate refresh. |

All responses are JSON unless noted otherwise. See `web-app/templates/` for an example HTML dashboard that consumes the REST data and renders summaries.

## Data Model

- **GridFS (`fs.files`, `fs.chunks`):** Stores the binary audio payloads uploaded via `/upload`. The `audio_gridfs_id` in `recordings` references these files.
- **`recordings` collection:** Metadata for each upload (status lifecycle: `pending → processing → done` or `error`), timestamps, detected language, duration, and error messages if something fails.
- **`transcriptions` collection:** Raw STT output with optional confidence scores. Each document links back to its recording.
- **`structured_notes` collection:** JSON returned by OpenAI summarization for advanced analytics or export.
- **`notes` collection:** Web-app-friendly documents that merge transcript, keywords, summary, and action items so the UI can render dashboards quickly.

### Processing lifecycle

1. `/upload` saves audio to GridFS and inserts a `recordings` document with `status="pending"`.
2. The machine-learning client (`app.poller.process_pending`) picks up pending docs, downloads audio, and calls OpenAI STT (`app.stt_openai`).
3. The transcript flows into `app.nlp_openai.generate_structured_note`, producing summaries/highlights/action items.
4. Results are written back to MongoDB (`transcriptions`, `structured_notes`, and `notes`), the recording status flips to `done`, and the dashboard/search endpoints immediately surface the new note.

## Testing & Quality

- **Machine-learning client**

  ```bash
  cd machine-learning-client
  pipenv install --dev
  pipenv run pytest --cov=app --cov-report=term-missing
  pipenv run black --check app test
+  pipenv run pylint app
  ```

- **Web app**

  ```bash
  cd web-app
  pipenv install --dev
  pipenv run pytest --maxfail=1 --disable-warnings
  pipenv run black --check app tests
  pipenv run pylint app
  ```

Pytest suites cover the poller loop, NLP parser, storage helpers, and search utilities with >80% coverage targets. The GitHub Actions workflow (`.github/workflows/lint.yml`) runs Black and pylint for both subsystems on every push/PR to keep formatting and style consistent.

## Troubleshooting

- **OpenAI authentication errors:** Ensure `OPENAI_API_KEY` (and `OPENAI_BASE_URL` if applicable) are present in `.env`. Check quota on your OpenAI account.
- **Machine-learning client not processing recordings:** Confirm `PROCESS_INLINE` is `false` (or stop inline mode) so uploads remain `pending`. Watch logs via `docker compose logs -f machine-learning-client` and run `pipenv run python -m app.main --once --log-level DEBUG` during debugging.
- **MongoDB auth fails:** The Mongo container uses `MONGO_USER`/`MONGO_PASSWORD` for the root user (`authSource=admin`). Make sure these match between `.env`, Compose, and any local Mongo clients.
- **Uploads rejected for size or type:** Supported extensions are `{wav, mp3, ogg, webm, m4a, mp4}`, and the size limit defaults to 10 MB. Adjust `MAX_FILE_MB` for larger files.
- **Need to start fresh:** `docker compose down -v` removes the `mongo_data` volume so the next `up` starts from a clean database.


## License

Distributed under the [GNU GPL v3](LICENSE). See the license file for details about redistribution and derivative works.
