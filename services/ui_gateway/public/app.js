document.addEventListener("DOMContentLoaded", () => {
  const jobList = document.getElementById("job-list");
  const logContainer = document.getElementById("log-container");
  const serviceToggles = document.getElementById("service-toggles");

  const jobs = new Map();
  const services = [
    "drive_watcher",
    "rip_worker",
    "enhance_worker",
    "transcode_worker",
    "metadata_worker",
    "blackhole_integration",
  ];

  // Initialize service toggles
  services.forEach((service) => {
    const div = document.createElement("div");
    div.className = "service-toggle";
    div.innerHTML = `
      <input type="checkbox" id="${service}" checked>
      <label for="${service}">${service.replace("_", " ")}</label>
    `;
    serviceToggles.appendChild(div);

    const checkbox = div.querySelector("input");
    checkbox.addEventListener("change", () => {
      fetch(`/api/services/${service}/toggle`, { method: "POST" })
        .then((res) => res.json())
        .catch((err) => console.error(err));
    });
  });

  // (SSE connection initialized later)

  function renderJobs() {
    jobList.innerHTML = "";
    jobs.forEach((job, id) => {
      const li = document.createElement("li");
      li.className = "job-item";
      li.innerHTML = `
        <div class="job-info">
          <strong>${job.channel}</strong> - ${job.status} ${job.progress ? `(${job.progress}%)` : ""}
        </div>
        <div class="job-controls">
          <button onclick="pauseJob('${id}')">Pause</button>
          <button onclick="cancelJob('${id}')">Cancel</button>
        </div>
      `;
      jobList.appendChild(li);
    });
  }

  function updateJob(data) {
    const jobId = data.job_id || data.id;
    if (!jobId) return;

    if (data.channel.endsWith(".start")) {
      jobs.set(jobId, { ...data, status: "running" });
    } else if (data.channel.endsWith(".progress")) {
      if (jobs.has(jobId)) {
        jobs.get(jobId).progress = data.progress;
      }
    } else if (data.channel.endsWith(".complete")) {
      if (jobs.has(jobId)) {
        jobs.get(jobId).status = "completed";
        setTimeout(() => jobs.delete(jobId), 5000); // Remove after 5s
      }
    }

    renderJobs();
  }

  function appendLog(message) {
    const div = document.createElement("div");
    div.className = "log-entry";
    div.textContent = `${new Date().toLocaleTimeString()}: ${message}`;
    logContainer.appendChild(div);
    logContainer.scrollTop = logContainer.scrollHeight;
  }

  window.pauseJob = (id) => {
    fetch(`/api/jobs/${id}/pause`, { method: "POST" })
      .then(() => appendLog(`Paused job ${id}`))
      .catch((err) => console.error(err));
  };

  window.cancelJob = (id) => {
    fetch(`/api/jobs/${id}/cancel`, { method: "POST" })
      .then(() => appendLog(`Canceled job ${id}`))
      .catch((err) => console.error(err));
  };

  // (EventSource initialized later, after helper functions)

  function handleEvent(data) {
    if (data.channel === "logs") {
      appendLog(data.message || JSON.stringify(data));
    } else if (
      data.channel.startsWith("rip.") ||
      data.channel.startsWith("enhance.") ||
      data.channel.startsWith("transcode.") ||
      data.channel.startsWith("metadata.") ||
      data.channel.startsWith("blackhole.")
    ) {
      updateJob(data);
    } else if (data.channel === "drive_events") {
      // Handle drive events if needed
      appendLog(`Drive event: ${JSON.stringify(data)}`);
    }
  }

  const eventSource = new EventSource("/api/events");

  eventSource.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    handleEvent(payload);
  };

  eventSource.onerror = (err) => {
    console.error("SSE error:", err);
  };
});
