# Build validation

Validation performed on this build:

- TypeScript compilation: passed.
- Vite production build: passed.
- Python test suite: **31 passed**, pytest return code 0.
- Real generated AVI file ingestion: passed through OpenCV metadata extraction and FFmpeg H.264 preview conversion.
- HTTP Range media response: passed (206 response, requested byte range).
- Model-unavailable behavior: passed; analysis returns a configuration error rather than fabricated events.
- Global frame-sampling offsets, interval reasoning, false temporal premises, counting, duration/gap arithmetic, missing filters, conservative tracking, URL destination checks, API state gates and persistence: covered by the passing tests.

Not validated in this environment:

- Real vision-model inference and natural-language evidence selection: Ollama/the configured vision model was unavailable.
- Event-detection accuracy and difficult tracking on real-world footage: no user video or model evaluation was performed. Use EVALUATION.md.
- Browser visual/interaction QA: the browser could not connect to the sandboxed loopback preview server. A file-based review was blocked by the browser's URL policy; no workaround was attempted.
- Public video downloads across external hosting/CDN providers: implementation is present; end-to-end compatibility was not measured.

The demo video is a synthetic input fixture. It has no saved analysis, precomputed event timeline, or prewritten question answers. Automated test event records exercise the temporal engine; they do not establish AI detection accuracy.
