# Riparr – Automated Media Ripping & Enhancement

**Riparr** is a self‑hosted, micro‑service pipeline that converts physical optical media into high‑quality, AI‑upscaled streams. It watches for inserted drives, rips discs with MakeMKV, upscales video using Real‑ESRGAN (AMD‑first), transcodes to HEVC via VAAPI, enriches metadata with a local LLM (Ollama), and delivers the result to a user‑specified library. All components run in Docker containers and communicate via Redis Streams.

## Table of Contents
- [Architecture Overview](docs/architecture.md)
- [Service Definitions](docs/services.md)
- [Validation & Test Plans](docs/validation.md)
- [Project To‑Do List](docs/todo.md)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Git Repository Setup](#git-repository-setup)
- [License](#license)

## Getting Started

1. **Prerequisites**
   - Docker Desktop (or Docker Engine) with **GPU support** (AMD VAAPI recommended).  
   - An optical drive that can be passed through to containers.  
   - `git` installed for version control.

2. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/riparr.git
   cd riparr
   ```

3. **Create Required Directories**
   ```bash
   mkdir -p docs validation_results data config
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the project root (or export variables in your shell) to enable the desired services and set runtime options:

   ```dotenv
   # Service toggles (set to true to enable)
   ENABLE_DRIVE_WATCHER=true
   ENABLE_RIP=true
   ENABLE_ENHANCE=true
   ENABLE_TRANSCODE=true
   ENABLE_METADATA=true
   ENABLE_UI=true

   # Redis connection (default works with docker‑compose)
   REDIS_HOST=redis
   REDIS_PORT=6379

   # Paths inside containers
   MKV_OUTPUT_DIR=/data/rips
   ENHANCED_OUTPUT_DIR=/data/enhanced
   TRANSCODED_OUTPUT_DIR=/data/transcoded
   METADATA_DIR=/data/metadata
   BLACKHOLE_PATH=/media/plex

   # GPU / model settings
   GPU_VENDOR=amd
   ESRGAN_PROFILE=amd-4x-med-vram4
   VAAPI_PROFILE=hevc_vaapi
   TRANSCODE_PROFILE=high
   AUDIO_FORMAT=aac
   ```

5. **Review the Docker Compose File**
   The repository contains a minimal `docker-compose.yml`. Adjust volume mounts, device mappings, and any additional environment variables to match your host setup (e.g., map `/dev/dri` for GPU access).

6. **Start the Stack**
   ```bash
   docker compose up -d
   ```

   Docker will pull/build the service images, start Redis, and launch each micro‑service container. Logs can be inspected with `docker compose logs -f <service>`.

7. **Open the UI**
   Navigate to `http://localhost:8080` (default UI port) to monitor jobs, view live logs, and control the pipeline (pause, cancel, toggle services).

8. **Running the Test Suite**
   ```bash
   pip install -r tests/requirements.txt
   pytest tests/
   ```
   Test results are stored in `validation_results/` and are also displayed in the CI pipeline.

9. **Stopping the Stack**
   ```bash
   docker compose down
   ```

## Development Workflow

- **Documentation** – Keep all design docs in the `docs/` folder. Update the markdown files as the architecture evolves.
- **To‑Do Tracking** – Edit `docs/todo.md` to reflect progress. The table uses simple status keywords (`Pending`, `In Progress`, `Completed`).
- **Testing** – Follow the validation steps in `docs/validation.md`. Add results to `validation_results/`.
- **Adding New Services** – Create a new service directory, add its Docker definition to `docker-compose.yml`, and update `docs/services.md` with the contract.

## Git Repository Setup

```bash
# Initialise a new repository (if not already)
git init
git add .
git commit -m "Initial commit – documentation and skeleton"

# Create a .gitignore (example)
cat > .gitignore <<'EOF'
# Docker artefacts
docker-compose.override.yml
*.log

# Media files
data/
validation_results/

# Secrets
.env
EOF

git add .gitignore
git commit -m "Add .gitignore"

# Optional: set up a remote
git remote add origin https://github.com/your‑username/riparr.git
git push -u origin master
```

Use feature branches for new services or major changes, and open pull requests to review updates to documentation and code.

## License

This project is licensed under the **MIT License** – see the `LICENSE` file for details.

---

*For any questions or contributions, please open an issue or submit a pull request on the GitHub repository.*