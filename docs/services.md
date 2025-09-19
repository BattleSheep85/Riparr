# Service Definitions

Riparr consists of several independent micro‑services, each running in its own Docker container and communicating via Redis Streams. The following sections describe the purpose, contract, and key configuration of each service.

### Code Simplification Updates
The recent code‑simplification effort applied to all Python services introduced the following improvements:

- **Dead Code Removal** – Unused variables, flags, and placeholder blocks (e.g., the `cleanup` flag in `blackhole_integration`) have been eliminated.
- **Structured Logging** – All `print` statements were replaced with the standard `logging` module (INFO, ERROR levels) for consistent, configurable output.
- **Type Hints** – Comprehensive type annotations were added to function signatures and key variables, improving readability and enabling static analysis tools.
- **Exception Handling** – Broad `except Exception` clauses were narrowed to specific exception types (e.g., `redis.ConnectionError`, `json.JSONDecodeError`), allowing more precise error recovery.
- **Redis Connection Standardization** – Redis clients are now created uniformly via `redis.from_url()` across services, simplifying configuration.
- **Documentation Alignment** – Service documentation has been updated to reflect these changes and to guide future contributors.

These updates reduce code size by roughly 15 % in the affected services and enhance maintainability without altering functional behavior.

## Drive Watcher
- **Implementation**: Python script [`services/drive_watcher/drive_watcher.py`](services/drive_watcher/drive_watcher.py:1) runs as a container defined in [`services/drive_watcher/Dockerfile`](services/drive_watcher/Dockerfile:1).
- **Key Env Vars**: `ENABLE_DRIVE_WATCHER`, `REDIS_HOST`, `REDIS_PORT`.
- **Entry Point**: Publishes `drive_events` to Redis streams.

## Rip Worker
- **Purpose**: Consume `drive.insert` events, invoke MakeMKV to rip the disc to an MKV file.
- **Contract**: Reads from `drive_events`, publishes `rip.start` and `rip.progress` events with job ID, source path, and progress percentage. Emits `rip.complete` with output file location.
- **Implementation**: Python script [`services/rip_worker/rip_worker.py`](services/rip_worker/rip_worker.py:1) with Dockerfile [`services/rip_worker/Dockerfile`](services/rip_worker/Dockerfile:1).
- **Key Env Vars**: `ENABLE_RIP`, `MKV_OUTPUT_DIR`, `TITLE_SELECTION`, `SUBTITLE_POLICY`, `AUDIO_POLICY`, `REDIS_URL`.
- **Entry Point**: Consumes `drive_events`, runs `makemkvcon`, publishes `rip.start`, `rip.progress`, `rip.complete`.

## Enhance Worker
- **Purpose**: Upscale and denoise video using Real‑ESRGAN (NCNN Vulkan) on AMD GPUs.
- **Contract**: Subscribes to `rip.complete`, processes the MKV, and publishes `enhance.start`, `enhance.progress`, and `enhance.complete` events with the enhanced file path.
- **Implementation**: Python script [`services/enhance_worker/enhance_worker.py`](services/enhance_worker/enhance_worker.py:1) with Dockerfile [`services/enhance_worker/Dockerfile`](services/enhance_worker/Dockerfile:1).
- **Key Env Vars**: `ENABLE_ENHANCE`, `ESRGAN_PROFILE`, `GPU_VENDOR`, `ENHANCED_OUTPUT_DIR`, `MODELS_DIR`, `CPU_FALLBACK`, `REDIS_URL`.
- **Entry Point**: Subscribes to `rip.complete`, performs HDR detection, runs Real‑ESRGAN, publishes `enhance.start`, `enhance.progress`, `enhance.complete`.

## Transcode Worker
- **Purpose**: Encode enhanced video to HEVC (10‑bit) using VAAPI (AMD) or fallback CPU encoder.
- **Contract**: Listens to `enhance.complete`, outputs `transcode.start`, `transcode.progress`, `transcode.complete` with final HEVC file location.
- **Implementation**: Python script [`services/transcode_worker/transcode_worker.py`](services/transcode_worker/transcode_worker.py:1) with Dockerfile [`services/transcode_worker/Dockerfile`](services/transcode_worker/Dockerfile:1).
- **Key Env Vars**: `ENABLE_TRANSCODE`, `VAAPI_PROFILE`, `TRANSCODE_PROFILE`, `ENHANCED_OUTPUT_DIR`, `TRANSCODED_OUTPUT_DIR`, `CPU_FALLBACK`, `AUDIO_FORMAT`, `REDIS_URL`.
- **Entry Point**: Consumes `enhance.complete`, runs `ffmpeg` with VAAPI or CPU fallback, publishes `transcode.start`, `transcode.progress`, `transcode.complete`.

## Metadata Worker
- **Purpose**: Call Ollama locally to normalize titles, generate directory structures, and create side‑car metadata files.
- **Contract**: Subscribes to `transcode.complete`, publishes `metadata.start` and `metadata.complete` with JSON metadata.
- **Implementation**: Python script [`services/metadata_worker/metadata_worker.py`](services/metadata_worker/metadata_worker.py:1) with Dockerfile [`services/metadata_worker/Dockerfile`](services/metadata_worker/Dockerfile:1).
- **Key Env Vars**: `ENABLE_METADATA`, `OLLAMA_MODEL`, `METADATA_DIR`, `REDIS_URL`.
- **Entry Point**: Subscribes to `transcode.complete`, calls Ollama for title normalization, writes JSON side‑car files, publishes `metadata.start`, `metadata.complete`.

## Blackhole Integration
- **Purpose**: Move final media files to a user‑specified drop directory (e.g., Plex library) and optionally create side‑car files.
- **Contract**: Consumes `metadata.complete`, performs filesystem move, emits `blackhole.complete`.
- **Implementation**: Python script [`services/blackhole_integration/blackhole_integration.py`](services/blackhole_integration/blackhole_integration.py:1) with Dockerfile [`services/blackhole_integration/Dockerfile`](services/blackhole_integration/Dockerfile:1).
- **Key Env Vars**: `BLACKHOLE_PATH`, `CLEANUP`, `REDIS_URL`.
- **Entry Point**: Consumes `metadata.complete`, moves final media files, optionally creates `.nfo` side‑car, publishes `blackhole.complete`.

## UI Gateway
- **Purpose**: Serve a web UI that displays job lists, live logs, and control actions (pause, cancel, toggle services).
- **Contract**: Subscribes to all job‑related streams for real‑time updates, provides REST endpoints for manual job control.
- **Implementation**: Node.js server [`services/ui_gateway/server.js`](services/ui_gateway/server.js:1) with Dockerfile [`services/ui_gateway/Dockerfile`](services/ui_gateway/Dockerfile:1).
- **Key Env Vars**: `UI_PORT`, `ENABLE_UI`, `REDIS_HOST`, `REDIS_PORT`.
- **Entry Point**: Serves static UI, provides SSE endpoint `/api/events`, REST controls for pause/cancel/toggle, streams all job‑related Redis events.

## Log Stream Service
- **Purpose**: Centralize JSON‑line logs from all containers, expose an SSE endpoint for the UI.
- **Contract**: Receives logs via STDOUT, tags with `job_id` and `severity`, stores in Redis for replay.
- **Implementation**: Node.js server [`services/log_stream_service/server.js`](services/log_stream_service/server.js:1) with Dockerfile [`services/log_stream_service/Dockerfile`](services/log_stream_service/Dockerfile:1).
- **Key Env Vars**: `REDIS_HOST`, `REDIS_PORT`.
- **Entry Point**: Subscribes to all service streams, writes JSON‑line logs to Redis `logs` stream for UI consumption.

## Orchestrator (Coordinator)
- **Purpose**: Maintain global configuration, health checks, and graceful shutdown of services.
- **Contract**: Reads configuration from `config.yaml`, monitors service health via Docker healthchecks, can pause/resume pipelines.
- **Implementation**: Python script [`services/orchestrator/orchestrator.py`](services/orchestrator/orchestrator.py:1) with Dockerfile [`services/orchestrator/Dockerfile`](services/orchestrator/Dockerfile:1).
- **Key Env Vars**: `CONFIG_PATH`, `REDIS_HOST`, `REDIS_PORT`.
- **Entry Point**: Reads `config.yaml`, monitors container health, provides global control via Redis `control` stream.

All services are stateless; persistent state resides in Redis and mounted volumes for media and configuration.