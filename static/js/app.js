/* ── Toast helper ────────────────────────────────────────────────────────── */
(function () {
  // Inject container + overlay once
  document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("toastContainer")) {
      const div = document.createElement("div");
      div.id = "toastContainer";
      document.body.appendChild(div);
    }
    if (!document.getElementById("loadingOverlay")) {
      const ov = document.createElement("div");
      ov.id = "loadingOverlay";
      ov.innerHTML = `
        <div class="text-center text-white">
          <div class="spinner-border mb-2" role="status"></div>
          <div id="loadingMsg">Please wait…</div>
        </div>`;
      document.body.appendChild(ov);
    }
  });

  window.showToast = function (message, type = "info", duration = 4000) {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast-msg ${type}`;
    const icons = { success: "✔", error: "✖", info: "ℹ" };
    toast.innerHTML = `<strong>${icons[type] || "ℹ"}</strong> ${message}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), duration);
  };

  window.showLoading = function (msg = "Please wait…") {
    document.getElementById("loadingMsg").textContent = msg;
    document.getElementById("loadingOverlay").classList.add("active");
  };

  window.hideLoading = function () {
    document.getElementById("loadingOverlay").classList.remove("active");
  };
})();

/* ── API helpers ─────────────────────────────────────────────────────────── */
async function apiRequest(method, url, body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json();
  return { ok: res.ok, status: res.status, data };
}

/* ── Create job ──────────────────────────────────────────────────────────── */
async function createJob() {
  const name      = document.getElementById("jobName").value.trim();
  const url       = document.getElementById("jobUrl").value.trim();
  const type      = document.getElementById("jobType").value;
  const cron      = document.getElementById("jobCron").value.trim();
  const configRaw = document.getElementById("jobConfig").value.trim();

  if (!name || !url) {
    showToast("Name and URL are required.", "error");
    return;
  }

  let config_json = null;
  if (configRaw) {
    try {
      JSON.parse(configRaw);   // validate JSON
      config_json = configRaw;
    } catch {
      showToast("Selector config is not valid JSON.", "error");
      return;
    }
  }

  showLoading("Creating job…");
  const { ok, data } = await apiRequest("POST", "/api/jobs", {
    name,
    url,
    scraper_type: type,
    schedule_cron: cron || null,
    config_json,
  });
  hideLoading();

  if (ok) {
    showToast(`Job "${name}" created!`, "success");
    bootstrap.Modal.getInstance(document.getElementById("addJobModal")).hide();
    setTimeout(() => location.reload(), 800);
  } else {
    showToast(data.error || "Failed to create job.", "error");
  }
}

/* ── Trigger a job run ───────────────────────────────────────────────────── */
async function triggerJob(jobId) {
  showLoading("Queueing job…");
  const { ok, data } = await apiRequest("POST", `/api/jobs/${jobId}/run`);
  hideLoading();

  if (ok) {
    showToast(`Job queued! Task ID: ${data.data.task_id}`, "success");
  } else {
    showToast(data.error || "Failed to trigger job.", "error");
  }
}

/* ── Delete a job ────────────────────────────────────────────────────────── */
async function deleteJob(jobId) {
  if (!confirm("Delete this job and all its data? This cannot be undone.")) return;
  showLoading("Deleting…");
  const { ok, data } = await apiRequest("DELETE", `/api/jobs/${jobId}`);
  hideLoading();

  if (ok) {
    showToast("Job deleted.", "info");
    setTimeout(() => location.reload(), 600);
  } else {
    showToast(data.error || "Delete failed.", "error");
  }
}

/* ── Toggle job active state ─────────────────────────────────────────────── */
async function toggleJob(jobId, currentState) {
  const { ok, data } = await apiRequest("PUT", `/api/jobs/${jobId}`, {
    is_active: !currentState,
  });
  if (ok) {
    showToast(`Job ${!currentState ? "activated" : "paused"}.`, "success");
    setTimeout(() => location.reload(), 600);
  } else {
    showToast(data.error || "Update failed.", "error");
  }
}
