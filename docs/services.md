# Service Definitions

Riparr consists of several independent micro‑services, each running in its own Docker container and communicating via Redis Streams. The following sections describe the purpose, contract, and key configuration of each service.

## Drive Watcher
- **Purpose**: Detect insertion/ejection of optical drives using udev events and publish `drive.insert` / `drive.eject` messages.
- **Contract**: Publishes JSON payload `{ "drive_id": "<uuid>", "device": "/dev/sr0", "event": "insert|eject" }` on the `drive_events` stream.
- **Key Config**: `ENABLE_DRIVE_WATCHER=true`, device group `cdrom`, read‑only mount of `/dev`.

## Rip Worker
- **Purpose**: Consume `drive.insert` events, invoke MakeMKV to rip the disc to an MKV file.
- **Contract**: Reads from `drive_events`, publishes `rip.start` and `rip.progress` events with job ID, source path, and progress percentage. Emits `rip.complete` with output file location.
- **Key Config**: `ENABLE_RIP=true`, `MKV_OUTPUT_DIR=/data/rips`, MakeMKV options (title selection, subtitle handling).

## Enhance Worker
- **Purpose**: Upscale and denoise video using Real‑ESRGAN (NCNN Vulkan) on AMD GPUs.
- **Contract**: Subscribes to `rip.complete`, processes the MKV, and publishes `enhance.start`, `enhance.progress`, and `enhance.complete` events with the enhanced file path.
- **Key Config**: `ENABLE_ENHANCE=true`, `ESRGAN_MODEL=RealESRGAN_x4plus`, tiling parameters, GPU device mapping `/dev/dri`.

## Transcode Worker
- **Purpose**: Encode enhanced video to HEVC (10‑bit) using VAAPI (AMD) or fallback CPU encoder.
- **Contract**: Listens to `enhance.complete`, outputs `transcode.start`, `transcode.progress`, `transcode.complete` with final HEVC file location.
- **Key Config**: `ENABLE_TRANSCODE=true`, `VAAPI_PROFILE=hevc_vaapi`, quality preset mapping (CRF‑like), audio pass‑through/downmix.

## Metadata Worker
- **Purpose**: Call Ollama locally to normalize titles, generate directory structures, and create side‑car metadata files.
- **Contract**: Subscribes to `transcode.complete`, publishes `metadata.start` and `metadata.complete` with JSON metadata.
- **Key Config**: `ENABLE_METADATA=true`, `OLLAMA_MODEL=llama2`, `METADATA_DIR=/data/metadata`.

## Blackhole Integration
- **Purpose**: Move final media files to a user‑specified drop directory (e.g., Plex library) and optionally create side‑car files.
- **Contract**: Consumes `metadata.complete`, performs filesystem move, emits `blackhole.complete`.
- **Key Config**: `BLACKHOLE_PATH=/media/plex`, `CLEANUP=true`.

## UI Gateway
- **Purpose**: Serve a web UI that displays job lists, live logs, and control actions (pause, cancel, toggle services).
- **Contract**: Subscribes to all job‑related streams for real‑time updates, provides REST endpoints for manual job control.
- **Key Config**: `UI_PORT=8080`, `ENABLE_UI=true`.

## Log Stream Service
- **Purpose**: Centralize JSON‑line logs from all containers, expose an SSE endpoint for the UI.
- **Contract**: Receives logs via STDOUT, tags with `job_id` and `severity`, stores in Redis for replay.
- **Key Config**: `LOG_LEVEL=info`, `REDIS_LOG_STREAM=logs`.

## Orchestrator (Coordinator)
- **Purpose**: Maintain global configuration, health checks, and graceful shutdown of services.
- **Contract**: Reads configuration from `config.yaml`, monitors service health via Docker healthchecks, can pause/resume pipelines.
- **Key Config**: `CONFIG_PATH=/config/config.yaml`.

All services are stateless; persistent state resides in Redis and mounted volumes for media and configuration.