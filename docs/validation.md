# Validation & Test Plans

Riparr’s reliability depends on thorough validation of each pipeline stage. The following test suites are defined to verify functionality, performance, and resilience.

## 1. Linux Containerization Validation (Rip Stage)
- **Goal**: Confirm that the Rip Worker can access an optical drive inside a container and produce a correct MKV.
- **Steps**:
  1. Mount `/dev/sr0` (or appropriate device) into the container with `--device=/dev/sr0`.
  2. Run a test disc (e.g., a Blu‑ray demo disc) and verify MakeMKV output.
  3. Check that the resulting MKV contains expected video/audio/subtitle tracks.
- **Success Criteria**: MKV file size matches expected range; `rip.complete` event emitted with correct metadata.

## 2. GPU Validation (Enhancement Stage)
- **Goal**: Verify Real‑ESRGAN runs on AMD VAAPI‑enabled GPUs and respects tiling limits.
- **Steps**:
  1. Use a synthetic 1080p test video.
  2. Run the Enhance Worker with different tiling configurations.
  3. Compare output PSNR/SSIM against baseline.
- **Success Criteria**: No GPU memory OOM; processing time within expected bounds; quality improvement > 0.5 dB PSNR.

## 3. Concurrency Stress Test
- **Goal**: Simulate up to 20 simultaneous drives and ensure queue management and resource limits work.
- **Steps**:
  1. Mock `drive.insert` events for 20 virtual drives.
  2. Observe Redis stream back‑pressure, job ordering, and worker scaling.
  3. Verify that no more than `MAX_CONCURRENT_RIPS` jobs run in parallel.
- **Success Criteria**: No deadlocks; jobs complete with correct ordering; CPU/GPU utilization stays below defined thresholds.

## 4. End‑to‑End POC Validation
- **Goal**: Execute the full pipeline on a single disc from ingestion to UI display.
- **Steps**:
  1. Insert a physical disc.
  2. Allow the system to rip, enhance, transcode, add metadata, and move to the blackhole.
  3. Verify UI shows live logs, job status, and final media appears in the target library.
- **Success Criteria**: All stages emit events; final file is playable; UI reflects accurate progress.

## 5. Failure & Retry Handling
- **Goal**: Ensure that transient errors trigger retries with exponential back‑off and that permanent failures are routed to a dead‑letter queue.
- **Steps**:
  1. Inject a temporary network failure during metadata fetch.
  2. Force a permanent error (e.g., unsupported codec) in the transcode stage.
  3. Observe retry counts and dead‑letter routing.
- **Success Criteria**: Transient errors retry up to `MAX_RETRIES`; permanent errors are logged and moved to `dead_letter` stream.

## 6. HDR vs SDR Path Verification
- **Goal**: Confirm that HDR content bypasses the AI upscaler and is processed with VAAPI preserving HDR metadata.
- **Steps**:
  1. Use an HDR 4K test clip.
  2. Run the pipeline and inspect the final HEVC file for HDR10 metadata (BT.2020, ST.2084).
- **Success Criteria**: No Real‑ESRGAN step executed; HDR metadata retained; visual quality matches source.

All test results should be recorded in the `validation_results/` directory (to be added later) and referenced in the project’s CI pipeline.