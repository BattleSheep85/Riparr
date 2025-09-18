# Project To‑Do List

The table below tracks the status of each major task. Update the **Status** column as work progresses.

| # | Task | Status |
|---|------|--------|
| 1 | Use Context7 to retrieve Ollama API docs and confirm availability of a small local model comparable to Exaone 4 1.2B | Completed |
| 2 | Use Context7 to retrieve Real‑ESRGAN NCNN Vulkan docs and container usage patterns | Completed |
| 3 | Use Context7 to retrieve FFmpeg hardware acceleration docs prioritizing VAAPI for AMD (hevc_vaapi), include AMF notes, map CRF‑like quality, and document /dev/dri permissions | In Progress |
| 4 | Use Context7 to retrieve HandBrake CLI docs for profile templating and passthrough constraints | Pending |
| 5 | Draft service boundaries and contracts for Drive Watcher, Rip Worker, Enhance Worker, Metadata Worker, Orchestrator, UI Gateway, and Log Stream | Completed |
| 6 | Define durable job schemas for rip, encode, enhance, and serve including idempotency keys, progress events, and error taxonomy | Completed |
| 7 | Draft Docker Compose skeleton with services, Redis, Ollama, and volumes without implementation yet | Completed |
| 8 | Specify container run flags for optical drives including device mappings, groups, and privileges for Linux hosts | Completed |
| 9 | Specify GPU runtime requirements per vendor with AMD‑first (VAAPI hevc, /dev/dri mapping, Mesa/AMDGPU and Vulkan dependencies), note NVIDIA/Intel later | Completed |
|10 | Create Drive Watcher design using udev events and a lightweight agent that publishes drive‑insert and eject messages | Completed |
|11 | Create Rip Worker design for MakeMKV CLI invocation, title selection policy, and progress parsing | Completed |
|12 | Decide rip policy defaults remux only vs optional transcode, and subtitle and audio retention rules | Completed |
|13 | Create Enhance Worker design using Real‑ESRGAN NCNN Vulkan with pluggable denoise and scaling profiles plus CPU fallback | Completed |
|14 | Define 4K upscaling profiles and quality presets for enhancement (2x/4x, denoise levels, tiling for VRAM), AMD‑first | Pending |
|15 | Approve HDR handling policy: HDR content skips AI upscaler; use VAAPI 10‑bit scaling to 4K preserving HDR10. SDR uses Real‑ESRGAN upscaler. | Completed |
|16 | Define transcode profiles using FFmpeg (hevc_vaapi) with CPU fallback; map CRF‑like quality; audio pass‑through + EAC3/AAC/OPUS downmix policy | Pending |
|17 | Create Metadata Worker design that calls Ollama to normalize names and build directory and file patterns | Completed |
|18 | Define blackhole integration contract target directory, sidecar metadata files if needed, and move semantics | Completed |
|19 | Design central log stream structure with per‑job correlation and severity and streaming to UI | Completed |
|20 | Design UI views job list, job detail with live logs, queue toggles, service toggles, and pause or cancel controls | Completed |
|21 | Draft failure handling strategy retries, backoff, dead‑letter queues, and operator visibility | Completed |
|22 | Draft configuration model runtime toggles per service, GPU policy, naming policy, and profile selection | Completed |
|23 | Produce Linux containerization validation plan for rip stage with a real optical drive and a sample disc | Completed |
|24 | Produce GPU validation plan for enhancement across AMD (first) then NVIDIA and Intel with synthetic test media | Completed |
|25 | Produce concurrency test plan simulating up to 20 drives and verifying queues and resource limits | Completed |
|26 | Write initial README outline with deployment steps, runtime flags, and safety notes | Completed |
|27 | Prepare minimal POC plan rip one disc to MKV, upscale to 4K, transcode to HEVC with VAAPI, drop to blackhole, and display in UI with live logs | Completed |
|28 | Investigate MakeMKV UHD/AACS compatibility and UHD‑friendly drive policy; keydb.cfg handling; confirm licensing/beta key workflow in container | Completed |
|29 | Decide video upscaling integration method (image sequence round‑trip vs ffmpeg pipe to Real‑ESRGAN) and I/O strategy (tiling, format choices) | Completed |
|30 | Define AMD VAAPI quality mapping plan to target CRF 18 equivalence (CQP/ICQ/global_quality vs qp) and create validation clip set | Completed |
|31 | Define Real‑ESRGAN containerization specifics for Vulkan (map /dev/dri, Vulkan ICD envs, model cache volume) and AMD‑first GPU notes | Completed |
|32 | Use Context7 to retrieve MakeMKV CLI usage and containerization references | Completed |