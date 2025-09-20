# Architecture Overview

The **Riparr** project is a modular, micro‑service system that automates the full media pipeline from physical disc to streamed content.

## High‑Level Diagram

```
+----------------+      +----------------+      +----------------+      +----------------+
| Drive Watcher  | ---> | Rip Worker     | ---> | Enhance Worker | ---> | UI Gateway |
+----------------+      +----------------+      +----------------+      +----------------+
      |                       |                       |                       |
      v                       v                       v                       v
 +-----------+          +-----------+          +-----------+          +-----------+
 |  Redis    |<--------|  Redis    |<--------|  Redis    |<--------|  Redis    |
 +-----------+          +-----------+          +-----------+          +-----------+
      ^                       ^                       ^                       ^
      |                       |                       |                       |
 +-----------+          +-----------+          +-----------+          +-----------+
 |   UI      |          |  Log      |          |  Config   |          |  Blackhole|
 +-----------+          +-----------+          +-----------+          +-----------+
```

The system uses **Docker Compose** to orchestrate containers, **Redis Streams** for event‑driven messaging, and **GPU‑accelerated** processing (AMD VAAPI first, later NVIDIA/Intel). All services are stateless except for persistent configuration and job metadata stored in Redis. The UI Gateway serves the web UI and streams logs, while the Log Stream Service centralizes JSON‑line logs from all containers.

### Core Principles

- **Modularity** – each stage is an independent service with a well‑defined contract.
- **Idempotency** – jobs can be retried without side effects.
- **Observability** – JSON‑line logs streamed to the UI via SSE/WebSocket.
- **Security** – containers run as non‑root users, only required devices are exposed.
- **Extensibility** – new workers (e.g., subtitle OCR) can be added by publishing to the same Redis stream.

### Runtime Toggles

- `ENABLE_RIP`, `ENABLE_ENHANCE`, `ENABLE_TRANSCODE`, `ENABLE_METADATA`
- GPU vendor selection (`GPU_VENDOR=amd|nvidia|intel`) and quality presets.

For detailed service contracts see **services.md**.