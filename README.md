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

### Prerequisites
Before deploying Riparr, ensure your system meets the following requirements:

- **Docker**: Docker Desktop (Windows/Mac) or Docker Engine (Linux) version 20.10 or later. Enable GPU support for hardware acceleration.
  - Installation: [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **GPU Drivers and Support**:
  - For AMD GPUs: Install AMDGPU-PRO drivers and ensure VAAPI support. Verify with `vainfo`.
  - For NVIDIA GPUs: Install NVIDIA drivers and NVIDIA Container Toolkit.
  - For Intel GPUs: Ensure i965 VAAPI drivers are installed.
- **Optical Drives**: At least one optical drive (DVD/Blu-ray) accessible to Docker containers. On Linux, ensure proper permissions for device passthrough.
- **Git**: Version 2.30 or later for repository management.
- **Operating System**: Linux (recommended), Windows 10/11, or macOS with Docker support.
- **Hardware Requirements**: 
  - CPU: Multi-core processor (4+ cores recommended)
  - RAM: 8GB minimum, 16GB+ recommended
  - Storage: Sufficient space for ripped media (depends on usage)

### Installation and Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/riparr.git
   cd riparr
   ```

2. **Create Required Directories**
   ```bash
   mkdir -p data/rips data/enhanced data/transcoded data/metadata validation_results
   ```

3. **Environment Configuration**
   Create a `.env` file in the project root with the following variables:

   ```dotenv
   # Service Toggles
   ENABLE_DRIVE_WATCHER=true
   ENABLE_RIP=true
   ENABLE_ENHANCE=true
   ENABLE_TRANSCODE=true
   ENABLE_METADATA=true
   ENABLE_UI=true

   # Redis Configuration
   REDIS_HOST=redis
   REDIS_PORT=6379

   # Directory Paths (host paths, adjust as needed)
   HOST_DATA_DIR=/path/to/your/data
   HOST_CONFIG_DIR=/path/to/your/config
   HOST_MEDIA_DIR=/path/to/your/media/library

   # GPU and Processing Settings
   GPU_VENDOR=amd  # Options: amd, nvidia, intel
   ESRGAN_MODEL=realesrgan-x4plus
   VAAPI_DEVICE=/dev/dri/renderD128
   TRANSCODE_PRESET=medium
   AUDIO_CODEC=aac

   # MakeMKV Configuration
   MAKEMKV_KEY=your-makemkv-key-here  # Required for Blu-ray ripping

   # Ollama Configuration (for metadata enhancement)
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   OLLAMA_MODEL=llama2

   # UI Configuration
   UI_PORT=8080
   ```

   **Note**: Adjust paths to match your host system. For Windows, use Windows-style paths (e.g., `C:\Users\YourName\Data`).

4. **Docker Compose Configuration**
   Review and modify `docker-compose.yml`:
   - Ensure volume mounts point to correct host directories
   - Verify device mappings for GPU and optical drives
   - Adjust service ports if conflicts exist

### Deployment Commands

1. **Build and Start Services**
   ```bash
   docker compose up --build -d
   ```

2. **View Logs**
   ```bash
   # All services
   docker compose logs -f
   ```

   ```bash
   # Specific service
   docker compose logs -f orchestrator
   ```

3. **Stop Services**
   ```bash
   docker compose down
   ```

4. **Restart Specific Service**
   ```bash
   docker compose restart rip_worker
   ```

5. **Update Services**
   ```bash
   docker compose pull
   docker compose up -d
   ```

6. **Clean Up**
   ```bash
   # Remove containers and volumes
   docker compose down -v
   
   # Remove images
   docker compose down --rmi all
   ```

### Portainer Deployment

Portainer provides a web-based UI for managing Docker containers and stacks. The updated `docker-compose.yml` is fully compatible with Portainer and includes proper labels for organization and environment variable configuration.

#### Prerequisites for Portainer Deployment

- Portainer CE or EE installed and running
- Access to Portainer web interface
- Docker environment configured in Portainer

#### Stack Creation Steps

1. **Access Portainer Web Interface**
   - Open your Portainer instance in a web browser
   - Log in with your administrator credentials

2. **Navigate to Stacks**
   - Click on "Stacks" in the left sidebar
   - Click "Add stack"

3. **Create the Riparr Stack**
   - **Name**: Enter `riparr` as the stack name
   - **Repository URL**: If using Git repository method:
     - Repository URL: `https://github.com/your-username/riparr.git`
     - Repository reference: `main` (or your default branch)
     - Compose path: `docker-compose.yml`
   - **Web editor**: Alternatively, copy and paste the contents of `docker-compose.yml`

4. **Configure Environment Variables**
   - In the "Environment variables" section, add the following variables:
   
   ```env
   # Redis Configuration
   REDIS_URL=redis://redis:6379
   REDIS_PORT=6379
   
   # Service Toggles
   ENABLE_ENHANCE=true
   ENABLE_TRANSCODE=true
   ENABLE_BLACKHOLE=true
   
   # GPU and Processing Settings
   GPU_VENDOR=amd
   ESRGAN_PROFILE=amd-4x-med-vram4
   VAAPI_PROFILE=hevc_vaapi
   TRANSCODE_PROFILE=high
   CPU_FALLBACK=false
   
   # Directory Paths (container paths)
   WATCH_PATH=/data
   ENHANCED_OUTPUT_DIR=/data/enhanced
   MKV_OUTPUT_DIR=/data/rips
   TRANSCODED_OUTPUT_DIR=/data/transcoded
   MODELS_DIR=/models
   BLACKHOLE_PATH=/media/plex
   CONFIG_PATH=/config/config.yaml
   
   # Media Processing Options
   TITLE_SELECTION=all
   SUBTITLE_POLICY=retain
   AUDIO_POLICY=retain
   AUDIO_FORMAT=aac
   
   # Service Configuration
   CLEANUP=true
   UI_PORT=8080
   LOG_STREAM_PORT=9000
   OLLAMA_PORT=11434
   OLLAMA_MODEL=llama3.0
   VAAPI=1
   ```

5. **Deploy the Stack**
   - Click "Deploy the stack"
   - Monitor the deployment progress in the "Logs" tab

6. **Verify Deployment**
   - Check the "Containers" section to ensure all services are running
   - Access the web UI at `http://your-host:8080`
   - View logs through Portainer's container logs interface

#### Portainer-Specific Features

- **Service Organization**: All services are labeled with `com.docker.compose.project=riparr` for easy identification
- **Access Control**: Services include `io.portainer.accesscontrol.teams=admin` labels for team-based access control
- **Network Isolation**: Services are organized into `frontend`, `backend`, and `data` networks for security
- **Environment Configuration**: All variables can be modified through Portainer's UI without editing files
- **Volume Management**: Named volumes are created with project labels for easy management

#### Managing the Stack in Portainer

- **Update Services**: Use "Pull and redeploy" to update to latest images
- **Environment Changes**: Edit environment variables directly in Portainer
- **Logs**: View real-time logs for any service through the Portainer interface
- **Scaling**: Scale services up or down as needed
- **Backup**: Export stack configuration for backup purposes

### Accessing the Application

- **Web UI**: Open `http://localhost:8080` in your browser
- **API Endpoints**: Available at `http://localhost:8080/api/*`
- **Logs**: View real-time logs in the UI or via Docker commands

### Troubleshooting

#### Common Issues

1. **GPU Not Detected**
   - Ensure GPU drivers are installed and up-to-date
   - Verify Docker GPU support is enabled
   - Check device permissions: `ls -la /dev/dri/`
   - For NVIDIA: Install nvidia-docker2

2. **Optical Drive Not Accessible**
   - On Linux: Add user to `cdrom` group: `sudo usermod -aG cdrom $USER`
   - Ensure drive is not mounted by host system
   - Check device permissions and ownership

3. **Container Startup Failures**
   - Check logs: `docker compose logs <service>`
   - Verify environment variables are set correctly
   - Ensure required directories exist and are writable
   - Check for port conflicts

4. **MakeMKV License Issues**
   - Obtain a valid MakeMKV beta key from https://www.makemkv.com/forum/viewtopic.php?t=1053
   - Set `MAKEMKV_KEY` in `.env` file
   - Restart rip_worker service

5. **Ollama Connection Errors**
   - Ensure Ollama is running on host: `ollama serve`
   - Verify `OLLAMA_BASE_URL` points to correct host/port
   - Pull required model: `ollama pull llama2`

6. **Permission Errors**
   - Ensure data directories are writable by Docker user (UID 1000 typically)
   - On Windows: Check Docker Desktop file sharing settings
   - On Linux: Adjust directory permissions: `chmod 755 /path/to/data`

7. **High CPU/Memory Usage**
   - Monitor resource usage: `docker stats`
   - Adjust service toggles in `.env` to disable unused features
   - Consider hardware upgrades for intensive workloads

#### Debugging Steps

1. **Check Service Health**
   ```bash
   docker compose ps
   ```

2. **Inspect Container**
   ```bash
   docker compose exec orchestrator bash
   ```

3. **View Detailed Logs**
   ```bash
   docker compose logs --tail=100 -f <service>
   ```

4. **Reset Environment**
   ```bash
   docker compose down -v
   docker system prune -a
   docker compose up --build -d
   ```

#### Getting Help

- Check existing GitHub issues for similar problems
- Provide detailed logs and system information when reporting issues
- Include your Docker version, OS, and hardware specs

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

---riparr–automated-media-ripping-&-enhancement

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

### Prerequisites
Before deploying Riparr, ensure your system meets the following requirements:

- **Docker**: Docker Desktop (Windows/Mac) or Docker Engine (Linux) version 20.10 or later. Enable GPU support for hardware acceleration.
  - Installation: [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **GPU Drivers and Support**:
  - For AMD GPUs: Install AMDGPU-PRO drivers and ensure VAAPI support. Verify with `vainfo`.
  - For NVIDIA GPUs: Install NVIDIA drivers and NVIDIA Container Toolkit.
  - For Intel GPUs: Ensure i965 VAAPI drivers are installed.
- **Optical Drives**: At least one optical drive (DVD/Blu-ray) accessible to Docker containers. On Linux, ensure proper permissions for device passthrough.
- **Git**: Version 2.30 or later for repository management.
- **Operating System**: Linux (recommended), Windows 10/11, or macOS with Docker support.
- **Hardware Requirements**: 
  - CPU: Multi-core processor (4+ cores recommended)
  - RAM: 8GB minimum, 16GB+ recommended
  - Storage: Sufficient space for ripped media (depends on usage)

### Installation and Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/riparr.git
   cd riparr
   ```

2. **Create Required Directories**
   ```bash
   mkdir -p data/rips data/enhanced data/transcoded data/metadata validation_results
   ```

3. **Environment Configuration**
   Create a `.env` file in the project root with the following variables:

   ```dotenv
   # Service Toggles
   ENABLE_DRIVE_WATCHER=true
   ENABLE_RIP=true
   ENABLE_ENHANCE=true
   ENABLE_TRANSCODE=true
   ENABLE_METADATA=true
   ENABLE_UI=true

   # Redis Configuration
   REDIS_HOST=redis
   REDIS_PORT=6379

   # Directory Paths (host paths, adjust as needed)
   HOST_DATA_DIR=/path/to/your/data
   HOST_CONFIG_DIR=/path/to/your/config
   HOST_MEDIA_DIR=/path/to/your/media/library

   # GPU and Processing Settings
   GPU_VENDOR=amd  # Options: amd, nvidia, intel
   ESRGAN_MODEL=realesrgan-x4plus
   VAAPI_DEVICE=/dev/dri/renderD128
   TRANSCODE_PRESET=medium
   AUDIO_CODEC=aac

   # MakeMKV Configuration
   MAKEMKV_KEY=your-makemkv-key-here  # Required for Blu-ray ripping

   # Ollama Configuration (for metadata enhancement)
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   OLLAMA_MODEL=llama2

   # UI Configuration
   UI_PORT=8080
   ```

   **Note**: Adjust paths to match your host system. For Windows, use Windows-style paths (e.g., `C:\Users\YourName\Data`).

4. **Docker Compose Configuration**
   Review and modify `docker-compose.yml`:
   - Ensure volume mounts point to correct host directories
   - Verify device mappings for GPU and optical drives
   - Adjust service ports if conflicts exist

### Deployment Commands

1. **Build and Start Services**
   ```bash
   docker compose up --build -d
   ```

2. **View Logs**
   ```bash
   # All services
   docker compose logs -f
   ```

   ```bash
   # Specific service
   docker compose logs -f orchestrator
   ```

3. **Stop Services**
   ```bash
   docker compose down
   ```

4. **Restart Specific Service**
   ```bash
   docker compose restart rip_worker
   ```

5. **Update Services**
   ```bash
   docker compose pull
   docker compose up -d
   ```

6. **Clean Up**
   ```bash
   # Remove containers and volumes
   docker compose down -v
   
   # Remove images
   docker compose down --rmi all
   ```

### Portainer Deployment

Portainer provides a web-based UI for managing Docker containers and stacks. The updated `docker-compose.yml` is fully compatible with Portainer and includes proper labels for organization and environment variable configuration.

#### Prerequisites for Portainer Deployment

- Portainer CE or EE installed and running
- Access to Portainer web interface
- Docker environment configured in Portainer

#### Stack Creation Steps

1. **Access Portainer Web Interface**
   - Open your Portainer instance in a web browser
   - Log in with your administrator credentials

2. **Navigate to Stacks**
   - Click on "Stacks" in the left sidebar
   - Click "Add stack"

3. **Create the Riparr Stack**
   - **Name**: Enter `riparr` as the stack name
   - **Repository URL**: If using Git repository method:
     - Repository URL: `https://github.com/your-username/riparr.git`
     - Repository reference: `main` (or your default branch)
     - Compose path: `docker-compose.yml`
   - **Web editor**: Alternatively, copy and paste the contents of `docker-compose.yml`

4. **Configure Environment Variables**
   - In the "Environment variables" section, add the following variables:
   
   ```env
   # Redis Configuration
   REDIS_URL=redis://redis:6379
   REDIS_PORT=6379
   
   # Service Toggles
   ENABLE_ENHANCE=true
   ENABLE_TRANSCODE=true
   ENABLE_BLACKHOLE=true
   
   # GPU and Processing Settings
   GPU_VENDOR=amd
   ESRGAN_PROFILE=amd-4x-med-vram4
   VAAPI_PROFILE=hevc_vaapi
   TRANSCODE_PROFILE=high
   CPU_FALLBACK=false
   
   # Directory Paths (container paths)
   WATCH_PATH=/data
   ENHANCED_OUTPUT_DIR=/data/enhanced
   MKV_OUTPUT_DIR=/data/rips
   TRANSCODED_OUTPUT_DIR=/data/transcoded
   MODELS_DIR=/models
   BLACKHOLE_PATH=/media/plex
   CONFIG_PATH=/config/config.yaml
   
   # Media Processing Options
   TITLE_SELECTION=all
   SUBTITLE_POLICY=retain
   AUDIO_POLICY=retain
   AUDIO_FORMAT=aac
   
   # Service Configuration
   CLEANUP=true
   UI_PORT=8080
   LOG_STREAM_PORT=9000
   OLLAMA_PORT=11434
   OLLAMA_MODEL=llama3.0
   VAAPI=1
   ```

5. **Deploy the Stack**
   - Click "Deploy the stack"
   - Monitor the deployment progress in the "Logs" tab

6. **Verify Deployment**
   - Check the "Containers" section to ensure all services are running
   - Access the web UI at `http://your-host:8080`
   - View logs through Portainer's container logs interface

#### Portainer-Specific Features

- **Service Organization**: All services are labeled with `com.docker.compose.project=riparr` for easy identification
- **Access Control**: Services include `io.portainer.accesscontrol.teams=admin` labels for team-based access control
- **Network Isolation**: Services are organized into `frontend`, `backend`, and `data` networks for security
- **Environment Configuration**: All variables can be modified through Portainer's UI without editing files
- **Volume Management**: Named volumes are created with project labels for easy management

#### Managing the Stack in Portainer

- **Update Services**: Use "Pull and redeploy" to update to latest images
- **Environment Changes**: Edit environment variables directly in Portainer
- **Logs**: View real-time logs for any service through the Portainer interface
- **Scaling**: Scale services up or down as needed
- **Backup**: Export stack configuration for backup purposes

### Accessing the Application

- **Web UI**: Open `http://localhost:8080` in your browser
- **API Endpoints**: Available at `http://localhost:8080/api/*`
- **Logs**: View real-time logs in the UI or via Docker commands

### Troubleshooting

#### Common Issues

1. **GPU Not Detected**
   - Ensure GPU drivers are installed and up-to-date
   - Verify Docker GPU support is enabled
   - Check device permissions: `ls -la /dev/dri/`
   - For NVIDIA: Install nvidia-docker2

2. **Optical Drive Not Accessible**
   - On Linux: Add user to `cdrom` group: `sudo usermod -aG cdrom $USER`
   - Ensure drive is not mounted by host system
   - Check device permissions and ownership

3. **Container Startup Failures**
   - Check logs: `docker compose logs <service>`
   - Verify environment variables are set correctly
   - Ensure required directories exist and are writable
   - Check for port conflicts

4. **MakeMKV License Issues**
   - Obtain a valid MakeMKV beta key from https://www.makemkv.com/forum/viewtopic.php?t=1053
   - Set `MAKEMKV_KEY` in `.env` file
   - Restart rip_worker service

5. **Ollama Connection Errors**
   - Ensure Ollama is running on host: `ollama serve`
   - Verify `OLLAMA_BASE_URL` points to correct host/port
   - Pull required model: `ollama pull llama2`

6. **Permission Errors**
   - Ensure data directories are writable by Docker user (UID 1000 typically)
   - On Windows: Check Docker Desktop file sharing settings
   - On Linux: Adjust directory permissions: `chmod 755 /path/to/data`

7. **High CPU/Memory Usage**
   - Monitor resource usage: `docker stats`
   - Adjust service toggles in `.env` to disable unused features
   - Consider hardware upgrades for intensive workloads

#### Debugging Steps

1. **Check Service Health**
   ```bash
   docker compose ps
   ```

2. **Inspect Container**
   ```bash
   docker compose exec orchestrator bash
   ```

3. **View Detailed Logs**
   ```bash
   docker compose logs --tail=100 -f <service>
   ```

4. **Reset Environment**
   ```bash
   docker compose down -v
   docker system prune -a
   docker compose up --build -d
   ```

#### Getting Help

- Check existing GitHub issues for similar problems
- Provide detailed logs and system information when reporting issues
- Include your Docker version, OS, and hardware specs

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