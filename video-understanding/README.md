# Video Understanding & Temporal Reasoning

A React + TypeScript and Python/FastAPI application for real video ingestion, sampled visual analysis, short-term entity tracking, timestamped events, and grounded temporal questions. No video or results are preloaded.

## Start the application

Requirements: Python 3.11 or newer, Node.js 20 or newer for frontend development, and [Ollama](https://ollama.com/download) with a vision-capable model. FFmpeg is supplied by `imageio-ffmpeg`; a system FFmpeg/FFprobe installation can also be configured.

From this project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
ollama pull qwen2.5vl:7b
```

Start Ollama, then run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. The included `frontend/dist` build is served by FastAPI, so you do not need a second server or Node to use the included build. `Start-App.ps1` launches this command after setup. A vision model can require several GB of disk and substantial RAM/VRAM; inference time depends on your machine. The UI reports model configuration errors instead of returning simulated results.

On macOS/Linux use `.venv/bin/python` instead of `.venv\Scripts\python.exe`.

### Frontend development

```powershell
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` to FastAPI on port 8000. Use `npm run build` to refresh the build served by FastAPI, then restart FastAPI.

### Configuration

Copy `.env.example` to `.env` at the project root. Existing environment variables override the file. Configure `OLLAMA_URL`, `VISION_MODEL`, video size/duration limits, data storage, or explicit FFmpeg/FFprobe paths. Use a model that supports **multiple images and structured JSON**, as documented in [Ollama's API](https://github.com/ollama/ollama/blob/main/docs/api.md) and [structured outputs](https://github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx). A reachable model name is not proof that it supports images; inference errors remain visible.

The default model is `qwen2.5vl:7b`. Model weights are not included in this project. Image requests go to the configured Ollama server; default processing stays on your machine. Fonts use a browser request to Google Fonts, with local system fallbacks.

## Use it

1. Choose **Upload video** or **Video URL**. Neither is automatically selected.
2. Drop/browse an MP4, MOV, AVI, MKV, or WebM file, or load a direct public HTTP/HTTPS file URL. Website pages, signed-in streams, and DRM video are unsupported.
3. Review the actual paused video. The server converts supported codecs to a browser-compatible H.264 MP4 preview.
4. Optionally adjust sampling interval and segment size. Each segment must contain at most 24 sampled frames.
5. Click **Analyze video**. Processing statuses describe actual work, and results open only after successful completion.
6. Search/filter the event timeline, inspect entities and confidence, and click a timestamp to seek. Seeking pauses the player.
7. Ask questions about order, intervals, duration, counts, or entities. Suggested questions only fill the input; they do not submit it.
8. Export your evidence records and question history as JSON if needed.

Native video controls provide play/pause, scrub, volume and fullscreen. The results player includes a playback-speed control. No code calls `play()`, loops footage, or seeks except in the user's timestamp-click handler.

## How real analysis works

```
Video file / public URL
  → streamed disk storage and metadata
  → FFmpeg browser preview
  → bounded chronological segments
  → sampled decoded frames with global presentation times
  → vision model: visible entities, boxes, observed actions, evidence frame IDs
  → appearance + motion track association
  → validated event intervals and conservative continuous-event normalization
  → SQLite evidence records + sparse temporal graph
  → chronological extractive summary
  → question intent + bounded evidence retrieval
  → deterministic temporal operation and timestamped answer
```

The vision model must reference supplied frame indices; it cannot invent event timestamps. Invalid references fail analysis. Events below 0.5 model confidence are omitted. This confidence is a model estimate, not a calibrated probability. All observations retain their evidence frame timestamps.

Tracking associates bounding-box color appearance and camera-compensated location using OpenCV optical flow and a robust affine transform. Tracks remain available for a configurable short gap (30 seconds by default). Ambiguous association creates an uncertain track rather than merging identities. This is a conservative baseline; it does not use facial recognition, learned appearance embeddings, or guaranteed long-range reidentification. Similar objects, occlusion, lighting changes, viewpoint changes and scene cuts remain difficult.

Only explicitly continuous same-type/same-entity observations within one sampling step merge. Discrete repeated events remain separate. Timeline normalization avoids counting a continuous observation multiple times, but visual sampling can miss short events or split a prolonged action.

Question answering separates natural-language intent from evidence selection. Evidence is scanned in bounded batches, including for long-video counting, rather than truncating the event list to one huge model request. The model selects only stored IDs. Invalid IDs fail closed. Missing or ambiguous anchors do not produce a guessed answer. The final answer text, timestamps, order, counts, duration and elapsed-time arithmetic are rendered by Python from the selected evidence. An absent filter never silently becomes an unrestricted query.

The engine supports first, last, sequence, before/after, nearest observed predecessor/successor, during/overlap comparisons, interval search, repeated occurrences, counting, duration, gap, and entity queries. The sparse stored graph records adjacent and nearest-observed relationships; arbitrary event-pair relationships are computed on demand. "Immediately" means the nearest **observed** event, with an explicit sampling-gap caveat, not proof that no unseen event intervened.

## Accuracy and scope

- Event times and durations are **approximate observed bounds**, tied to decoded frame timestamps. The default 2-second sampling interval cannot establish frame-exact onset or offset. FFprobe improves container-duration metadata when available; OpenCV provides a fallback.
- Model-generated descriptions can still be wrong even when frame references are valid. Human review of clickable evidence is necessary to evaluate semantic accuracy. This project does not claim verified detection performance on unseen videos.
- Audio is not analyzed. An audible alarm cannot be inferred from silent images. Visible changes can be described conservatively.
- A stationary object is not proof that it was untouched; occluded interaction and activity between samples are unknown. Unsupported questions report insufficient evidence.
- First-to-last entity visibility is not continuous presence or proof of time spent in an area. Duration answers use detected event intervals.
- No sampled event does not prove that the event never happened. Zero observed occurrences include this qualification.
- Videos are processed from disk in bounded frame batches. Entity/event records grow with video length; decoding and model calls run sequentially, with one active analysis worker.
- SQLite persists video records, events, entities, relationships, and question history. Interrupted analysis is marked failed on restart. This is a local student/demo application; it has no multi-user authentication or distributed worker infrastructure. Keep the default loopback binding.
- Public URL downloads validate scheme, destination IPs, redirect destinations, size and actual video readability. Connections pin a validated public IP and preserve TLS hostname verification. Some CDN hosts may reject direct-IP connections; those URLs show a download error.

## Demonstration

The first screen intentionally contains no selected video. For a real demonstration, upload a short consented clip with visible activities and ask:

- "What happened first?"
- "Describe the sequence of events."
- "What happened immediately before [an event shown in the timeline]?"
- "How many times did [an observed repeated action] happen?"
- "How long did [a detected continuous action] last?"
- "How much time passed between [event A] and [event B]?"

An optional **real input fixture**, `demo/motion-study.mp4`, is supplied. It is explicitly synthetic footage of moving geometric objects with stops, occlusion and camera panning, useful for a reproducible computer-vision demonstration. Select it manually through Upload video; it is never loaded automatically and contains no precomputed AI results. It does not depict people, restricted areas, trucks or alarms. The requested truck/alarm example is a scenario to record in actual footage, not a fabricated analysis state.

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
cd frontend
npm run build
```

Automated tests cover interval relationships (including overlaps and containment), first/last, ties, repeated-event normalization, entity-aware counts, duration/gap arithmetic, missing filters, false "after" premises, unknown event IDs, insufficient-evidence timestamps, global chunk alignment, corrupt files, private URL rejection, short-gap tracking and track expiry, unavailable models, API state gates, real AVI ingestion/FFmpeg transcoding, HTTP Range seeking, and deletion.

Fixtures and manually constructed event records in tests are **test inputs**, not app analysis or claims about model quality. See `EVALUATION.md` for the real-video evaluation protocol. Model inference accuracy, identity continuity under difficult occlusion, and URL ingestion across third-party CDNs require evaluation on your videos and configured model.

## Project files

- `frontend/src/main.tsx` — input, preview, status, results, timeline, filters, question history, tracks.
- `frontend/src/style.css` — responsive visual design and visible focus styles.
- `backend/main.py` — FastAPI endpoints, lifecycle and static serving.
- `backend/ingestion.py` — disk streaming, URL validation/pinning, metadata, transcoding.
- `backend/pipeline.py` — bounded sampling, chunk processing, evidence validation, summary.
- `backend/vision.py` — structured vision inference and bounded question retrieval.
- `backend/tracking.py` — conservative visual association and camera motion compensation.
- `backend/temporal.py` — normalization, graph, interval queries, grounded answer rendering.
- `backend/store.py` — SQLite persistence.
- `backend/tests/` — automated correctness and ingestion tests.

FastAPI's interactive API reference is available at `/docs`. Main endpoints are `/api/video/upload`, `/api/video/url`, `/api/video/{id}/analyze`, `/status`, `/media`, `/events`, `/timeline`, `/summary`, `/entities`, `/questions`, `/question`, and `/relationship`.
