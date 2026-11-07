// Translation Keyboard - front end. No build step, no dependencies.
// Privacy: the access code and recent translations live only in memory
// (this tab). Nothing is written to localStorage, cookies or the server.
"use strict";

(() => {
  const DEBOUNCE_MS = 400;
  const MAX_RECENT = 12;
  const TONE_LABELS = { casual: "Casual", friendly: "Friendly", formal: "Formal", playful: "Playful" };

  const $ = (id) => document.getElementById(id);
  const els = {
    unlockView: $("unlockView"), appView: $("appView"), unlockForm: $("unlockForm"), codeInput: $("codeInput"),
    unlockBtn: $("unlockBtn"), unlockErr: $("unlockErr"), mockBanner: $("mockBanner"), globalError: $("globalError"),
    langBtn: $("langBtn"), langName: $("langName"), langNative: $("langNative"), audience: $("audience"),
    tones: $("tones"), scriptSeg: $("scriptSeg"), input: $("input"), count: $("count"), clearBtn: $("clearBtn"),
    dot: $("dot"), stripLabel: $("stripLabel"), out: $("out"), copyBtn: $("copyBtn"), explainBtn: $("explainBtn"),
    reviewNote: $("reviewNote"), reviewText: $("reviewText"), explainPanel: $("explainPanel"),
    recentList: $("recentList"), recentEmpty: $("recentEmpty"), clearRecent: $("clearRecent"),
    dialog: $("langDialog"), dlgClose: $("dlgClose"), search: $("langSearch"), list: $("langList"),
    themeBtn: $("themeBtn"), sr: $("sr"), toast: $("toast"),
  };

  const state = {
    apiBase: "", offline: false, placeholder: false, // placeholder = mock or preview output (English text)
    code: "", groups: [], byCode: {}, maxChars: 1000,
    lang: null, tone: "friendly", script: "latin", arabicScript: null, audience: "unknown",
    timer: 0, controller: null, seq: 0,
    output: "", outputFor: null, lastKey: "", streaming: false,
    recent: [],
  };

  // ------------------------------------------------------------------ helpers
  function el(tag, props = {}, ...children) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
      if (k === "class") n.className = v;
      else if (k === "text") n.textContent = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else if (v !== undefined && v !== null && v !== false) n.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children) if (c != null) n.append(c);
    return n;
  }

  let toastTimer = 0;
  function toast(msg) {
    els.toast.textContent = msg;
    els.toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => els.toast.classList.remove("show"), 1800);
  }
  const announce = (msg) => { els.sr.textContent = ""; setTimeout(() => (els.sr.textContent = msg), 30); };

  function showGlobalError(msg) {
    els.globalError.textContent = msg || "";
    els.globalError.hidden = !msg;
  }

  async function api(path, body, signal) {
    const headers = {};
    if (body) headers["Content-Type"] = "application/json";
    if (state.code) headers["X-Access-Code"] = state.code;
    return fetch(state.apiBase + path, { method: body ? "POST" : "GET", headers, body: body ? JSON.stringify(body) : undefined, signal, cache: "no-store", credentials: "omit" });
  }

  // Find a running server: config.js apiBase, then this page's own server, then localhost:8000.
  async function findServer() {
    const cfg = (window.TK_CONFIG && String(window.TK_CONFIG.apiBase || "").trim().replace(/\/+$/, "")) || "";
    const local = ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
    const candidates = [];
    if (cfg) candidates.push(cfg);
    // Live Server (ports 5500-5502) and GitHub Pages only serve files, so don't ask them for /api.
    const staticHost = /^550[0-2]$/.test(location.port) || location.hostname.endsWith(".github.io");
    if (location.protocol.startsWith("http") && !staticHost) candidates.push("");
    if ((local || location.protocol === "file:") && location.port !== "8000") candidates.push("http://localhost:8000", "http://127.0.0.1:8000");
    for (const base of [...new Set(candidates)]) {
      // A configured server may be a free Render instance that is asleep: keep trying for ~90 s.
      const deadline = Date.now() + (base === cfg && cfg ? 90000 : 3000);
      let tries = 0;
      while (Date.now() < deadline) {
        if (tries++ === 1) showConnecting(base);
        const ctrl = new AbortController();
        const t = setTimeout(() => ctrl.abort(), Math.max(1000, Math.min(30000, deadline - Date.now())));
        try {
          const res = await fetch(base + "/api/health", { cache: "no-store", signal: ctrl.signal, credentials: "omit" });
          const data = res.ok && (res.headers.get("content-type") || "").includes("json") ? await res.json() : null;
          if (data && data.status === "ok") return { base, health: data };
        } catch (_) { /* asleep, unreachable or blocked: retry until the deadline */ } finally { clearTimeout(t); }
        if (Date.now() + 4000 < deadline) await sleep(4000); else break;
      }
    }
    return { base: null, cfg };
  }

  function showConnecting(base) {
    els.mockBanner.hidden = false;
    $("mockText").textContent = `Connecting to the server at ${base}… A free server can take up to a minute to wake up.`;
  }

  // ---------------------------------------------------------------- offline preview (no server)
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function* previewStream(params, signal) {
    const p = state.byCode[params.language];
    const words = `[preview ${p.name} · ${params.tone} · ${params.script}] ${params.text}`.split(" ");
    for (const w of words) {
      await sleep(25);
      if (signal.aborted) throw new DOMException("aborted", "AbortError");
      yield w + " ";
    }
  }
  function previewExplain(params) {
    return {
      source_language: "unknown (preview)", parsed: true, confidence: "low",
      meaning_back: "Preview mode: no server is connected, so this is not a real explanation.",
      tone_check: `Requested tone: ${params.tone}.`,
      cultural_notes: ["Connect the Python server (see README) to get real translations and explanations."],
      naturalness_flags: [],
    };
  }

  async function* serverStream(params, signal) {
    const res = await api("/api/translate", params, signal);
    if (!res.ok) throw new Error(await errorMessage(res));
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let pending = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      pending += decoder.decode(value, { stream: true });
      let nl;
      while ((nl = pending.indexOf("\n")) !== -1) {
        const line = pending.slice(0, nl).trim();
        pending = pending.slice(nl + 1);
        if (!line) continue;
        const ev = JSON.parse(line);
        if (ev.t === "chunk") yield ev.d;
        else if (ev.t === "error") throw new Error(ev.m);
        else if (ev.t === "done") return;
      }
    }
    throw new Error("The connection closed early. Please try again.");
  }

  async function errorMessage(res) {
    let data = {};
    try { data = await res.json(); } catch (_) { /* not JSON */ }
    if (res.status === 401) lockAgain(data.message || "Please enter your access code again.");
    return data.message || ({
      413: "That message is too long.",
      429: "You're going a little fast. Try again in a moment.",
      503: "The service is busy or not available right now.",
    }[res.status] || "Something went wrong. Please try again.");
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch (_) {
      const ta = el("textarea", { class: "sr-only" });
      ta.value = text;
      document.body.append(ta);
      ta.select();
      try { document.execCommand("copy"); } finally { ta.remove(); }
    }
    toast("Copied");
  }

  // ------------------------------------------------------------------ theme
  function effectiveTheme() {
    const t = document.documentElement.dataset.theme;
    if (t !== "auto") return t;
    return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function updateThemeButton() {
    const next = effectiveTheme() === "dark" ? "light" : "dark";
    els.themeBtn.setAttribute("aria-label", `Switch to ${next} mode`);
    els.themeBtn.innerHTML = next === "dark"
      ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>'
      : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
  }
  els.themeBtn.addEventListener("click", () => {
    document.documentElement.dataset.theme = effectiveTheme() === "dark" ? "light" : "dark";
    updateThemeButton();
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", updateThemeButton);

  // ------------------------------------------------------------------ unlock
  function lockAgain(msg) {
    state.code = "";
    abortStream();
    els.appView.hidden = true;
    els.unlockView.hidden = false;
    els.unlockErr.textContent = msg || "";
    els.codeInput.value = "";
    els.codeInput.focus();
  }

  els.unlockForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const code = els.codeInput.value.trim();
    if (!code) { els.unlockErr.textContent = "Enter the access code you were given."; return; }
    els.unlockBtn.disabled = true;
    els.unlockErr.textContent = "";
    try {
      const res = await fetch(state.apiBase + "/api/unlock", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code }), cache: "no-store", credentials: "omit" });
      if (!res.ok) {
        let data = {};
        try { data = await res.json(); } catch (_) {}
        els.unlockErr.textContent = data.message || "That code didn't work.";
        return;
      }
      state.code = code;
      els.codeInput.value = "";
      showApp();
    } catch (_) {
      els.unlockErr.textContent = "Can't reach the server. Check your connection and try again.";
    } finally {
      els.unlockBtn.disabled = false;
    }
  });

  function showApp() {
    els.unlockView.hidden = true;
    els.appView.hidden = false;
    els.input.focus();
    if (els.input.value.trim()) schedule(0);
  }

  // ------------------------------------------------------------------ controls
  function renderTones(tones) {
    els.tones.querySelectorAll(".chip").forEach((n) => n.remove());
    for (const t of tones) {
      const input = el("input", { type: "radio", name: "tone", value: t, checked: t === state.tone });
      input.addEventListener("change", () => { state.tone = t; settingsChanged(); });
      els.tones.append(el("label", { class: "chip" }, input, el("span", { text: TONE_LABELS[t] || t })));
    }
  }

  function selectLanguage(code, { quiet = false } = {}) {
    const p = state.byCode[code];
    if (!p) return;
    state.lang = code;
    // Arabic dialects remember the script the user picked; others use their default.
    state.script = p.scripts.length > 1 && p.scripts.includes(state.arabicScript) ? state.arabicScript : p.default_script;
    els.langName.textContent = p.name;
    els.langNative.textContent = p.native_name !== p.name ? p.native_name : "";
    els.langNative.lang = p.lang_tags[p.default_script];
    els.langNative.dir = "auto";
    els.langBtn.setAttribute("aria-label", `Translate to: ${p.name}. Change language`);
    els.scriptSeg.hidden = p.scripts.length < 2;
    updateScriptButtons();
    const lower = p.resource_level === "lower";
    els.reviewText.textContent = `${p.name} guidance hasn't been reviewed by native speakers yet.` +
      (lower ? " There is less training data for it, so expect more mistakes." : "");
    els.reviewText.title = p.weak_spots;
    applyOutputDirection();
    if (!quiet) settingsChanged();
  }

  function updateScriptButtons() {
    els.scriptSeg.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.script === state.script)));
  }
  els.scriptSeg.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-script]");
    if (!b || b.dataset.script === state.script) return;
    state.script = state.arabicScript = b.dataset.script;
    updateScriptButtons();
    applyOutputDirection();
    settingsChanged();
  });
  els.audience.addEventListener("change", () => { state.audience = els.audience.value; settingsChanged(); });

  function applyOutputDirection() {
    const p = state.byCode[state.lang];
    if (!p) return;
    els.out.dir = state.placeholder ? "ltr" : (p.directions[state.script] || "ltr");
    els.out.lang = p.lang_tags[state.script] || p.code;
  }

  function settingsChanged() {
    hideExplain();
    if (els.input.value.trim()) schedule(0);
  }

  // ------------------------------------------------------------------ language dialog
  function renderLanguageList(filter = "") {
    const q = filter.trim().toLowerCase();
    els.list.textContent = "";
    let shown = 0;
    for (const g of state.groups) {
      const matches = g.languages.filter((p) => !q || [p.name, p.native_name, p.code, g.region].some((s) => s.toLowerCase().includes(q)));
      if (!matches.length) continue;
      const labelId = `grp-${g.region.replace(/\W+/g, "-")}`;
      const group = el("div", { role: "group", "aria-labelledby": labelId }, el("p", { class: "group-label", id: labelId, text: g.region }));
      for (const p of matches) {
        const selected = p.code === state.lang;
        group.append(el("button", {
          type: "button", class: "opt", role: "option", "aria-selected": String(selected), "data-code": p.code, tabindex: "-1",
          onclick: () => { selectLanguage(p.code); els.dialog.close(); els.langBtn.focus(); },
        },
          el("span", { class: "check", "aria-hidden": "true", text: "✓" }),
          el("span", {}, el("span", { class: "o-name", text: p.name }),
            p.native_name !== p.name ? el("br") : null,
            p.native_name !== p.name ? el("span", { class: "o-native", text: p.native_name, lang: p.lang_tags[p.default_script], dir: "auto" }) : null),
          p.resource_level === "lower" ? el("span", { class: "badge o-tag", text: "Less data" }) : null,
        ));
        shown++;
      }
      els.list.append(group);
    }
    if (!shown) els.list.append(el("p", { class: "empty", text: "No language matches that search yet." }));
  }

  const options = () => [...els.list.querySelectorAll(".opt")];
  els.langBtn.addEventListener("click", () => {
    els.search.value = "";
    renderLanguageList();
    els.dialog.showModal();
    els.search.focus();
  });
  els.dlgClose.addEventListener("click", () => { els.dialog.close(); els.langBtn.focus(); });
  els.dialog.addEventListener("click", (e) => { if (e.target === els.dialog) els.dialog.close(); });
  els.search.addEventListener("input", () => renderLanguageList(els.search.value));
  els.search.addEventListener("keydown", (e) => {
    const opts = options();
    if (e.key === "ArrowDown" && opts.length) { e.preventDefault(); opts[0].focus(); }
    if (e.key === "Enter" && opts.length) { e.preventDefault(); opts[0].click(); }
  });
  els.list.addEventListener("keydown", (e) => {
    const opts = options();
    const i = opts.indexOf(document.activeElement);
    if (i === -1) return;
    if (e.key === "ArrowDown") { e.preventDefault(); (opts[i + 1] || opts[0]).focus(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); i === 0 ? els.search.focus() : opts[i - 1].focus(); }
    else if (e.key === "Home") { e.preventDefault(); opts[0].focus(); }
    else if (e.key === "End") { e.preventDefault(); opts[opts.length - 1].focus(); }
  });

  // ------------------------------------------------------------------ typing + streaming
  function updateCount() {
    const n = els.input.value.length;
    els.count.textContent = `${n} / ${state.maxChars}`;
    els.count.style.color = n > state.maxChars ? "var(--danger)" : "";
  }

  els.input.addEventListener("input", () => {
    updateCount();
    hideExplain();
    if (!els.input.value.trim()) { abortStream(); resetOutput(); return; }
    schedule(DEBOUNCE_MS);
  });
  els.clearBtn.addEventListener("click", () => {
    els.input.value = "";
    updateCount();
    abortStream();
    resetOutput();
    hideExplain();
    els.input.focus();
  });

  function schedule(ms) {
    clearTimeout(state.timer);
    state.timer = setTimeout(run, ms);
  }

  function abortStream() {
    clearTimeout(state.timer);
    if (state.controller) state.controller.abort();
    state.controller = null;
    state.streaming = false;
  }

  function setStatus(kind, label) {
    els.dot.className = "dot" + (kind ? ` ${kind}` : "");
    els.stripLabel.textContent = label;
  }

  function resetOutput() {
    state.output = ""; state.outputFor = null; state.lastKey = "";
    els.out.textContent = "";
    setStatus("", "Suggestion");
    els.copyBtn.disabled = true;
    els.explainBtn.disabled = true;
  }

  function renderOutput(text, streaming) {
    els.out.textContent = text;
    if (streaming) els.out.append(el("span", { class: "caret", "aria-hidden": "true" }));
  }

  async function run() {
    const text = els.input.value.trim();
    if (!text || !state.lang) return;
    if (text.length > state.maxChars) {
      setStatus("err", `Please keep it under ${state.maxChars} characters.`);
      return;
    }
    const params = { text, language: state.lang, tone: state.tone, script: state.script, audience: state.audience };
    const key = JSON.stringify(params);
    if (key === state.lastKey && !state.streaming) return;

    abortStream();
    const controller = new AbortController();
    state.controller = controller;
    const seq = ++state.seq;
    state.lastKey = key;
    state.streaming = true;
    let buf = "";
    setStatus("live", "Writing…");
    els.copyBtn.disabled = true;
    els.explainBtn.disabled = true;

    try {
      const source = state.offline ? previewStream(params, controller.signal) : serverStream(params, controller.signal);
      for await (const chunk of source) {
        if (seq !== state.seq) return;
        buf += chunk;
        renderOutput(buf, true);
      }
      if (seq !== state.seq) return;
      buf = buf.trim();
      state.streaming = false;
      renderOutput(buf, false);
      if (!buf.trim()) { setStatus("err", "No suggestion came back. Try rephrasing."); return; }
      state.output = buf;
      state.outputFor = params;
      setStatus("done", `${state.byCode[state.lang].name} · ${TONE_LABELS[state.tone]}`);
      els.copyBtn.disabled = false;
      els.explainBtn.disabled = false;
      announce("Translation ready.");
      addRecent(params, buf);
    } catch (err) {
      if (err.name === "AbortError" || seq !== state.seq) return;
      state.streaming = false;
      state.lastKey = "";
      renderOutput(buf, false);
      const msg = err instanceof TypeError ? "Can't reach the server. Check your connection." : (err.message || "Something went wrong.");
      setStatus("err", msg);
      announce(msg);
    }
  }

  els.copyBtn.addEventListener("click", () => state.output && copyText(state.output));

  // ------------------------------------------------------------------ explain
  function hideExplain() {
    els.explainPanel.hidden = true;
    els.explainPanel.textContent = "";
  }

  els.explainBtn.addEventListener("click", async () => {
    if (!state.output || !state.outputFor) return;
    const params = { ...state.outputFor, translation: state.output };
    const p = state.byCode[params.language];
    const panel = els.explainPanel;
    panel.hidden = false;
    panel.setAttribute("aria-busy", "true");
    panel.textContent = "";
    panel.append(el("h2", { text: "Checking…" }), el("div", { class: "skeleton" }), el("div", { class: "skeleton", style: "width:70%" }));
    els.explainBtn.disabled = true;
    try {
      let d;
      if (state.offline) {
        await sleep(300);
        d = previewExplain(params);
      } else {
        const res = await api("/api/explain", params);
        if (!res.ok) throw new Error(await errorMessage(res));
        d = await res.json();
      }
      renderExplain(d, p, params);
    } catch (err) {
      panel.textContent = "";
      panel.append(el("h2", { text: "Couldn't check this one" }),
        el("p", { text: err instanceof TypeError ? "Can't reach the server. Check your connection." : err.message }));
    } finally {
      panel.setAttribute("aria-busy", "false");
      els.explainBtn.disabled = !state.output;
    }
  });

  function renderExplain(d, p, params) {
    const panel = els.explainPanel;
    panel.textContent = "";
    const conf = d.confidence || "low";
    panel.append(el("h2", {}, "Check and explain ", el("span", { class: `badge ${conf}`, text: `AI confidence: ${conf}` })));
    if (!d.parsed) {
      panel.append(el("p", { text: "The checker's answer couldn't be read this time. Try again." }));
      return;
    }
    panel.append(el("h3", { text: "What it says" }), el("p", { text: d.meaning_back || "—", dir: "auto" }));
    if (d.tone_check) panel.append(el("h3", { text: "How it sounds" }), el("p", { text: d.tone_check, dir: "auto" }));
    if (d.cultural_notes && d.cultural_notes.length) {
      panel.append(el("h3", { text: "Cultural notes" }), el("ul", {}, ...d.cultural_notes.map((n) => el("li", { text: n, dir: "auto" }))));
    }
    panel.append(el("h3", { text: "Naturalness check" }));
    if (d.naturalness_flags && d.naturalness_flags.length) {
      const tag = p.lang_tags[params.script];
      const rtl = p.directions[params.script] === "rtl";
      panel.append(el("ul", {}, ...d.naturalness_flags.map((f) => el("li", { class: "flag" },
        el("b", { text: f.phrase, lang: tag, dir: rtl ? "rtl" : "ltr", class: rtl ? "rtl-text" : "" }), " — ",
        el("span", { text: f.issue, dir: "auto" }),
        f.suggestion ? el("div", {}, "Try: ", el("span", { text: f.suggestion, lang: tag, dir: rtl ? "rtl" : "ltr", class: rtl ? "rtl-text" : "" })) : null,
      ))));
    } else {
      panel.append(el("p", { text: "Nothing flagged. That's the AI's view, not a native speaker's." }));
    }
    panel.append(el("p", { class: "hint", style: "margin-top:12px", text: "Checked by AI, not a person. For anything important, ask a native speaker." }));
  }

  // ------------------------------------------------------------------ recent (memory only)
  function addRecent(params, output) {
    const top = state.recent[0];
    const entry = { ...params, output, at: new Date() };
    const continuing = top && top.language === params.language &&
      (params.text.startsWith(top.text) || top.text.startsWith(params.text));
    if (continuing) state.recent[0] = entry; else state.recent.unshift(entry);
    state.recent.length = Math.min(state.recent.length, MAX_RECENT);
    renderRecent();
  }

  function renderRecent() {
    els.recentList.textContent = "";
    els.recentEmpty.hidden = state.recent.length > 0;
    els.clearRecent.hidden = state.recent.length === 0;
    for (const r of state.recent) {
      const p = state.byCode[r.language];
      const rtl = !state.placeholder && p.directions[r.script] === "rtl";
      els.recentList.append(el("li", { class: "card" },
        el("span", { class: "r-src", text: r.text, dir: "auto" }),
        el("span", { text: r.output, dir: rtl ? "rtl" : "ltr", lang: p.lang_tags[r.script], class: rtl ? "rtl-text" : "" }),
        el("span", { class: "r-meta" },
          el("span", { text: `${p.name} · ${TONE_LABELS[r.tone]} · ${r.at.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` }),
          el("button", { type: "button", class: "btn ghost small", text: "Copy", "aria-label": `Copy ${p.name} translation`, onclick: () => copyText(r.output) })),
      ));
    }
  }
  els.clearRecent.addEventListener("click", () => { state.recent = []; renderRecent(); toast("Cleared"); });

  // ------------------------------------------------------------------ boot
  async function boot() {
    updateThemeButton();
    try {
      const server = await findServer();
      let health, langs;
      if (server.base !== null) {
        state.apiBase = server.base;
        health = server.health;
        const lRes = await api("/api/languages");
        if (!lRes.ok) throw new Error("bad status");
        langs = await lRes.json();
      } else {
        // No server: Live Server or GitHub Pages without a backend. Show the UI in preview mode.
        state.offline = true;
        health = { engine: "preview", access_required: false };
        const lRes = await fetch("languages.json", { cache: "no-store" });
        if (!lRes.ok) throw new Error("no languages.json");
        langs = await lRes.json();
        const mt = $("mockText");
        mt.textContent = "";
        if (server.cfg) {
          mt.append(el("b", { text: "Can't reach the server. " }),
            `Showing a preview with placeholder results. Check that ${server.cfg} is running on Render, ` +
            `and that its ALLOWED_ORIGINS setting includes ${location.origin}.`);
        } else if (location.hostname.endsWith(".github.io")) {
          mt.append(el("b", { text: "Almost there. " }),
            "This page is in preview mode because it doesn't know your server's address yet. " +
            "Put your Render address in web/config.js (apiBase) to get real translations.");
        } else {
          mt.append(el("b", { text: "Preview mode. " }),
            "No server is connected, so results are placeholders. To get real translations, start the Python server (see README).");
        }
      }
      state.groups = langs.groups;
      state.maxChars = langs.max_chars;
      for (const g of langs.groups) for (const p of g.languages) state.byCode[p.code] = p;
      renderTones(langs.tones);
      selectLanguage(langs.groups[0].languages[0].code, { quiet: true });
      updateCount();
      renderRecent();
      state.placeholder = ["mock", "preview"].includes(health.engine);
      applyOutputDirection();
      els.mockBanner.hidden = !["mock", "preview"].includes(health.engine);
      if (health.access_required) { els.unlockView.hidden = false; els.codeInput.focus(); }
      else showApp();
    } catch (_) {
      showGlobalError(location.protocol === "file:"
        ? "Open this page through VS Code Live Server or the Python server, not by double-clicking the file."
        : "Can't load the app right now. Check your connection and refresh the page.");
    }
  }
  boot();
})();
