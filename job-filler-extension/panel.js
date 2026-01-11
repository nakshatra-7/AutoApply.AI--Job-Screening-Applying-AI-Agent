const $ = (id) => document.getElementById(id);

window.onerror = function (message, source, lineno, colno) {
  const status = $("status");
  if (status) {
    status.textContent = `Error: ${message} (${lineno}:${colno})`;
  }
  return false;
};

function pretty(obj) {
  return typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
}

async function copyText(text) {
  await navigator.clipboard.writeText(text);
}

function setStatus(msg) {
  const el = $("status");
  if (el) el.textContent = msg;
}

function setProfilePreview(profile) {
  const el = $("profilePreview");
  if (!el) return;
  if (!profile || Object.keys(profile).length === 0) {
    el.textContent = "No profile loaded.";
    return;
  }
  el.textContent = pretty(profile);
}

function makeCard({ id, title, bodyText, defaultOpen = true }) {
  const card = document.createElement("div");
  card.className = "card";
  card.dataset.cardId = id;

  const header = document.createElement("div");
  header.className = "cardHeader";

  const left = document.createElement("div");
  left.className = "cardTitle";
  left.textContent = title;

  const actions = document.createElement("div");
  actions.className = "cardActions";

  const copyBtn = document.createElement("button");
  copyBtn.className = "smallBtn";
  copyBtn.textContent = "Copy";

  const chev = document.createElement("span");
  chev.className = "chev";
  chev.textContent = defaultOpen ? "▲" : "▼";

  actions.appendChild(copyBtn);
  actions.appendChild(chev);

  header.appendChild(left);
  header.appendChild(actions);

  const body = document.createElement("div");
  body.className = "cardBody";
  if (!defaultOpen) body.classList.add("hidden");

  const pre = document.createElement("pre");
  pre.textContent = bodyText || "";
  body.appendChild(pre);

  header.addEventListener("click", (e) => {
    if (e.target === copyBtn) return;
    body.classList.toggle("hidden");
    chev.textContent = body.classList.contains("hidden") ? "▼" : "▲";
  });

  copyBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    try {
      await copyText(pre.textContent);
      copyBtn.textContent = "Copied";
      setTimeout(() => (copyBtn.textContent = "Copy"), 900);
    } catch {
      copyBtn.textContent = "Failed";
      setTimeout(() => (copyBtn.textContent = "Copy"), 900);
    }
  });

  card.appendChild(header);
  card.appendChild(body);
  return card;
}

function renderFillPacketUI(apiResponse) {
  const content = $("content");
  if (!content) return;
  content.innerHTML = "";

  const packet = apiResponse.packet || {};
  const screening = apiResponse.screening_answers || {};
  const cover = apiResponse.cover_letter_short || "";
  const oneLiner = apiResponse.one_liner || "";
  const keywords = apiResponse.resume_keywords || [];

  content.appendChild(
    makeCard({ id: "packet", title: "Packet", bodyText: pretty(packet), defaultOpen: true })
  );

  content.appendChild(
    makeCard({
      id: "screening",
      title: "Screening answers",
      bodyText: pretty(screening),
      defaultOpen: true
    })
  );

  content.appendChild(
    makeCard({
      id: "cover",
      title: "Cover letter",
      bodyText: cover,
      defaultOpen: false
    })
  );

  content.appendChild(
    makeCard({
      id: "keywords",
      title: "Resume keywords",
      bodyText: Array.isArray(keywords) ? keywords.join(", ") : pretty(keywords),
      defaultOpen: false
    })
  );

  content.appendChild(
    makeCard({
      id: "one_liner",
      title: "One-liner",
      bodyText: oneLiner,
      defaultOpen: false
    })
  );
}

function setLog(text) {
  const el = $("logOutput");
  if (el) el.textContent = text;
}

function setResumeBanner(text) {
  const el = $("resumeBanner");
  if (!el) return;
  if (!text) {
    el.textContent = "";
    el.classList.add("hidden");
    return;
  }
  el.textContent = text;
  el.classList.remove("hidden");
}

function openResumePickerImmediate() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs?.[0];
    if (!tab?.id) return;
    chrome.tabs.sendMessage(tab.id, { type: "OPEN_RESUME_PICKER" }, () => {});
  });
}

function openResumePickerImmediateRetry() {
  openResumePickerImmediate();
  setTimeout(openResumePickerImmediate, 500);
  setTimeout(openResumePickerImmediate, 1500);
}

function appendLog(line) {
  const el = $("logOutput");
  if (!el) return;
  if (el.textContent === "No run yet.") el.textContent = "";
  el.textContent = `${el.textContent}\n${line}`.trim();
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("No active tab.");
  return tab;
}

async function extractJDFromContentScript(tabId) {
  const res = await chrome.tabs.sendMessage(tabId, { type: "EXTRACT_JD" });
  if (!res?.ok) {
    throw new Error(res?.error || "JD extraction failed.");
  }
  const jd = (res.job_description || "").trim();
  if (jd.length < 120) {
    throw new Error(`Couldn't extract a good job description (got ${jd.length} chars).`);
  }
  return res;
}

function joinUrl(base, path) {
  const b = (base || "").trim().replace(/\/+$/, "");
  const p = (path || "").trim().replace(/^\/+/, "");
  return `${b}/${p}`;
}

async function postFillPacket(baseUrl, job_description) {
  const url = joinUrl(baseUrl, "/agent/fill_packet");
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description })
  });

  if (!resp.ok) {
    const txt = await resp.text().catch(() => "");
    throw new Error(`Backend error ${resp.status}: ${txt || resp.statusText}`);
  }
  return await resp.json();
}

async function uploadResume() {
  const { baseUrl, userId } = await loadSettings();
  if (!userId) throw new Error("User ID is required to upload resume.");
  const fileInput = $("resumeFile");
  const file = fileInput?.files?.[0];
  if (!file) throw new Error("Select a resume file first.");
  const url = joinUrl(baseUrl, "/resume/upload");
  const form = new FormData();
  form.append("user_id", userId);
  form.append("file", file);
  const resp = await fetch(url, { method: "POST", body: form });
  if (!resp.ok) {
    const txt = await resp.text().catch(() => "");
    throw new Error(`Resume upload failed ${resp.status}: ${txt || resp.statusText}`);
  }
  const data = await resp.json();
  const filename = data.filename || file.name || "resume";
  const { settings = {} } = await chrome.storage.local.get(["settings"]);
  await chrome.storage.local.set({ settings: { ...settings, resumeFilename: filename } });
  return data;
}

async function loadSettings() {
  const { settings = {} } = await chrome.storage.local.get(["settings"]);
  return {
    baseUrl: settings.baseUrl || $("baseUrl")?.value?.trim() || "http://127.0.0.1:8000",
    userId: settings.userId || $("userId")?.value?.trim() || "",
    accountEmail: settings.accountEmail || $("accountEmail")?.value?.trim() || "",
    accountPassword: settings.accountPassword || $("accountPassword")?.value || "",
    accountPasswordConfirm: settings.accountPasswordConfirm || $("accountPasswordConfirm")?.value || "",
    resumeFilename: settings.resumeFilename || ""
  };
}

async function saveSettings() {
  const baseUrl = $("baseUrl")?.value?.trim() || "http://127.0.0.1:8000";
  const userId = $("userId")?.value?.trim() || "";
  const accountEmail = $("accountEmail")?.value?.trim() || "";
  const accountPassword = $("accountPassword")?.value || "";
  const accountPasswordConfirm = $("accountPasswordConfirm")?.value || "";
  await chrome.storage.local.set({
    settings: { baseUrl, userId, accountEmail, accountPassword, accountPasswordConfirm }
  });
  setStatus("Saved settings.");
}

async function fetchProfile() {
  const { baseUrl, userId } = await loadSettings();
  if (!userId) throw new Error("User ID is required to fetch profile.");
  const url = joinUrl(baseUrl, `/profile/get?user_id=${encodeURIComponent(userId)}`);
  const resp = await fetch(url);
  if (!resp.ok) {
    const txt = await resp.text().catch(() => "");
    throw new Error(`Profile fetch failed ${resp.status}: ${txt || resp.statusText}`);
  }
  return await resp.json();
}

async function runOneClickFlow(trigger = "manual") {
  const tab = await getActiveTab();

  setStatus("Extracting job description...");
  const extracted = await extractJDFromContentScript(tab.id);

  if ($("jd")) $("jd").value = extracted.job_description;

  const { baseUrl } = await loadSettings();

  setStatus("Calling backend...");
  const out = await postFillPacket(baseUrl, extracted.job_description);

  setStatus("Done.");
  renderFillPacketUI(out);

  await chrome.storage.local.set({
    last_run: { url: extracted.url, packet: out, ts: Date.now(), trigger }
  });

  return out;
}

async function applyAndFillBeta() {
  setLog("Starting Apply + Fill (Beta)...");
  setResumeBanner("");
  autoRunSuppressedUntil = Date.now() + 60000;
  const tab = await getActiveTab();
  const output = await runOneClickFlow("apply_beta");
  appendLog("Generated fill packet.");

  setStatus("Sending apply/fill to page...");
  let profile = {};
  try {
    profile = await fetchProfile();
    appendLog("Fetched profile from backend.");
    setProfilePreview(profile);
  } catch (e) {
    appendLog(`Profile fetch failed: ${e.message || e}`);
    setProfilePreview({});
  }
  const { accountEmail, accountPassword, accountPasswordConfirm } = await loadSettings();
  const res = await new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(
      tab.id,
      {
        type: "APPLY_AND_FILL",
        packet: output.packet || {},
        screening_answers: output.screening_answers || {},
        profile: profile || {},
        account: {
          email: accountEmail,
          password: accountPassword,
          confirmPassword: accountPasswordConfirm
        }
      },
      (response) => {
        if (chrome.runtime.lastError) {
          return reject(new Error("No content script. Open a job page (not chrome://) and retry."));
        }
        resolve(response);
      }
    );
  });

  if (!res?.ok) {
    throw new Error(res?.error || "Apply + Fill failed.");
  }

  (res.logs || []).forEach((line) => appendLog(line));
  if (res.blocked === "captcha") {
    setStatus("Captcha detected. Complete it, then click Continue after CAPTCHA.");
    return;
  }
  if (res.blocked === "resume_upload") {
    const { resumeFilename } = await loadSettings();
    const name = resumeFilename || "your resume file";
    setResumeBanner(`Select ${name} now in the file picker.`);
    setStatus("Resume upload required. Select the file, then Continue after Resume Upload.");
    return;
  }
  if (res.blocked === "missing_fields") {
    setStatus("Missing required fields. Please fill them manually, then Continue.");
    return;
  }
  setStatus("Apply + Fill done (best effort).");
}

async function continueAfterCaptcha() {
  setStatus("Continuing after CAPTCHA...");
  const tab = await getActiveTab();
  const { last_run } = await chrome.storage.local.get(["last_run"]);
  const packet = last_run?.packet || {};
  const res = await new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(
      tab.id,
      { type: "CONTINUE_AFTER_CAPTCHA", packet: packet.packet || {}, screening_answers: packet.screening_answers || {} },
      (response) => {
        if (chrome.runtime.lastError) {
          return reject(new Error("No content script. Open a job page (not chrome://) and retry."));
        }
        resolve(response);
      }
    );
  });

  if (!res?.ok) {
    throw new Error(res?.error || "Continue after CAPTCHA failed.");
  }
  (res.logs || []).forEach((line) => appendLog(line));
  setStatus("Continue flow finished.");
}

async function continueAfterResumeUpload() {
  setStatus("Continuing after resume upload...");
  setResumeBanner("");
  const tab = await getActiveTab();
  const { last_run } = await chrome.storage.local.get(["last_run"]);
  const packet = last_run?.packet || {};
  const res = await new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(
      tab.id,
      { type: "CONTINUE_AFTER_RESUME", packet: packet.packet || {}, screening_answers: packet.screening_answers || {} },
      (response) => {
        if (chrome.runtime.lastError) {
          return reject(new Error("No content script. Open a job page (not chrome://) and retry."));
        }
        resolve(response);
      }
    );
  });

  if (!res?.ok) {
    throw new Error(res?.error || "Continue after resume upload failed.");
  }
  (res.logs || []).forEach((line) => appendLog(line));
  setStatus("Continue flow finished.");
}

async function loadLastRun() {
  const { last_run } = await chrome.storage.local.get(["last_run"]);
  if (last_run?.packet) {
    renderFillPacketUI(last_run.packet);
    setStatus(`Loaded last result (${new Date(last_run.ts).toLocaleString()})`);
  } else {
    setStatus("Ready.");
  }
}

async function loadAutorunToggle() {
  const { autorun = true } = await chrome.storage.local.get(["autorun"]);
  if ($("autorun")) $("autorun").checked = autorun;
  return autorun;
}

async function setAutorun(val) {
  await chrome.storage.local.set({ autorun: !!val });
}

let isRunning = false;
let autoRunSuppressedUntil = 0;

async function safeRun(trigger) {
  if (isRunning) return;
  if (trigger === "auto" && Date.now() < autoRunSuppressedUntil) return;
  isRunning = true;
  try {
    await runOneClickFlow(trigger);
  } catch (e) {
    setStatus(`Error: ${e.message || e}`);
  } finally {
    isRunning = false;
  }
}

let lastAutoTs = 0;
function shouldAutoRunNow() {
  const now = Date.now();
  if (now - lastAutoTs < 1200) return false;
  lastAutoTs = now;
  return true;
}

chrome.runtime.onMessage.addListener(async (msg) => {
  if (!msg?.type) return;

  if (msg.type === "TAB_URL_CHANGED" || msg.type === "TAB_ACTIVATED") {
    const { autorun = true } = await chrome.storage.local.get(["autorun"]);
    if (!autorun) return;
    if (!shouldAutoRunNow()) return;
    safeRun("auto");
  }
});

function wireUI() {
  if ($("runOneClick")) {
    $("runOneClick").addEventListener("click", () => safeRun("manual"));
  }

  if ($("copyAll")) {
    $("copyAll").addEventListener("click", async () => {
      const { last_run } = await chrome.storage.local.get(["last_run"]);
      if (!last_run?.packet) return setStatus("Nothing to copy yet.");
      await copyText(pretty(last_run.packet));
      setStatus("Copied full packet to clipboard.");
    });
  }

  if ($("applyBeta")) {
    $("applyBeta").addEventListener("click", async () => {
      try {
        openResumePickerImmediateRetry();
        await applyAndFillBeta();
      } catch (e) {
        setStatus(`Error: ${e.message || e}`);
        appendLog(`Error: ${e.message || e}`);
      }
    });
  }

  if ($("uploadResume")) {
    $("uploadResume").addEventListener("click", async () => {
      try {
        setStatus("Uploading resume...");
        await uploadResume();
        setStatus("Resume uploaded. Refreshing profile...");
        const profile = await fetchProfile();
        setProfilePreview(profile);
        setStatus("Profile refreshed.");
      } catch (e) {
        setStatus(`Error: ${e.message || e}`);
      }
    });
  }

  if ($("continueAfterCaptcha")) {
    $("continueAfterCaptcha").addEventListener("click", async () => {
      try {
        await continueAfterCaptcha();
      } catch (e) {
        setStatus(`Error: ${e.message || e}`);
        appendLog(`Error: ${e.message || e}`);
      }
    });
  }

  if ($("continueAfterResume")) {
    $("continueAfterResume").addEventListener("click", async () => {
      try {
        await continueAfterResumeUpload();
      } catch (e) {
        setStatus(`Error: ${e.message || e}`);
        appendLog(`Error: ${e.message || e}`);
      }
    });
  }

  if ($("autorun")) {
    $("autorun").addEventListener("change", async (e) => {
      await setAutorun(e.target.checked);
    });
  }

  if ($("saveSettings")) {
    $("saveSettings").addEventListener("click", saveSettings);
  }

  const accountFields = ["accountEmail", "accountPassword", "accountPasswordConfirm", "userId"];
  accountFields.forEach((fieldId) => {
    const el = $(fieldId);
    if (!el) return;
    el.addEventListener("change", saveSettings);
  });
}

(async () => {
  try {
    wireUI();

    const { settings = {} } = await chrome.storage.local.get(["settings"]);
    if ($("baseUrl")) $("baseUrl").value = settings.baseUrl || "http://127.0.0.1:8000";
    if ($("userId")) $("userId").value = settings.userId || "";
    if ($("accountEmail")) $("accountEmail").value = settings.accountEmail || "";
    if ($("accountPassword")) $("accountPassword").value = settings.accountPassword || "";
    if ($("accountPasswordConfirm")) $("accountPasswordConfirm").value = settings.accountPasswordConfirm || "";

    if (settings.userId) {
      try {
        const profile = await fetchProfile();
        setProfilePreview(profile);
      } catch {
        setProfilePreview({});
      }
    }

    await loadLastRun();
    const autorun = await loadAutorunToggle();

    if (autorun) {
      await safeRun("panel_open");
    }
  } catch (e) {
    setStatus(`Ready. (Init failed: ${e.message || e})`);
  }
})();
