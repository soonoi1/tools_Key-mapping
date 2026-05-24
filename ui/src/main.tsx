import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type MappingMode = "hold" | "tap";

type Mapping = {
  name: string;
  enabled: boolean;
  mode: MappingMode;
  trigger: { all: string[] };
  target: { keys: string[] };
};

type AppConfig = {
  mappings: Mapping[];
};

type AppStatus = {
  running: boolean;
  log: string[];
};

declare global {
  interface Window {
    pywebview?: {
      api: {
        get_config: () => Promise<AppConfig>;
        save_config: (config: AppConfig) => Promise<{ ok: boolean; error?: string }>;
        start_mapping: (config: AppConfig) => Promise<{ ok: boolean; error?: string }>;
        stop_mapping: () => Promise<{ ok: boolean }>;
        get_status: () => Promise<AppStatus>;
      };
    };
  }
}

const triggerOptions = [
  { token: "mouse.left", label: "Left", hint: "Mouse left button" },
  { token: "mouse.right", label: "Right", hint: "Mouse right button" },
  { token: "mouse.middle", label: "Wheel", hint: "Middle wheel click" },
  { token: "mouse.x1", label: "Side 1", hint: "Recommended trigger" },
  { token: "mouse.x2", label: "Side 2", hint: "Try this if Side 1 does not react" },
  { token: "ctrl", label: "Ctrl", hint: "Keyboard combo" },
  { token: "shift", label: "Shift", hint: "Keyboard combo" },
  { token: "tab", label: "Tab", hint: "Keyboard combo" },
];

const targetOptions = [
  { token: "alt_r", label: "Right Alt", hint: "Typeless target" },
  { token: "alt_l", label: "Left Alt", hint: "Left Alt" },
  { token: "alt", label: "Alt", hint: "Generic Alt" },
  { token: "ctrl", label: "Ctrl", hint: "Control" },
  { token: "shift", label: "Shift", hint: "Shift" },
  { token: "space", label: "Space", hint: "空格" },
  { token: "enter", label: "Enter", hint: "回车" },
  { token: "esc", label: "Esc", hint: "取消" },
];

const fallbackConfig: AppConfig = {
  mappings: [
    {
      name: "Typeless 语音唤醒",
      enabled: true,
      mode: "hold",
      trigger: { all: ["mouse.x1"] },
      target: { keys: ["alt_r"] },
    },
  ],
};

function App() {
  const [config, setConfig] = useState<AppConfig>(fallbackConfig);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState<string[]>(["Ready. Default mapping: Side 1 -> Right Alt."]);
  const [notice, setNotice] = useState("Mapping starts automatically.");

  const selected = config.mappings[selectedIndex] ?? config.mappings[0];
  const jsonPreview = useMemo(() => JSON.stringify(config, null, 2), [config]);

  useEffect(() => {
    let stopped = false;

    async function bootstrap() {
      const api = window.pywebview?.api;
      if (!api) return;
      const loaded = await api.get_config();
      if (stopped) return;
      setConfig(loaded);
      const started = await api.start_mapping(loaded);
      if (stopped) return;
      setRunning(started.ok);
      setNotice(started.ok ? "Listening. Hold Side 1 to test Typeless." : started.error ?? "Auto start failed.");
    }

    bootstrap();
    return () => {
      stopped = true;
    };
  }, []);

  useEffect(() => {
    const timer = window.setInterval(async () => {
      const api = window.pywebview?.api;
      if (!api) return;
      const status = await api.get_status();
      setRunning(status.running);
      setLogs(status.log.length ? status.log.slice(-7) : logs);
    }, 700);
    return () => window.clearInterval(timer);
  }, [logs]);

  function updateSelected(next: Partial<Mapping>) {
    setConfig((current) => ({
      mappings: current.mappings.map((mapping, index) =>
        index === selectedIndex ? { ...mapping, ...next } : mapping,
      ),
    }));
  }

  function toggleTrigger(token: string) {
    const current = selected.trigger.all;
    const next = current.includes(token) ? current.filter((item) => item !== token) : [...current, token];
    updateSelected({ trigger: { all: next.length ? next : current } });
  }

  function setTarget(token: string) {
    updateSelected({ target: { keys: [token] } });
  }

  function addMapping() {
    setConfig((current) => ({
      mappings: [
        ...current.mappings,
        {
          name: `Rule ${current.mappings.length + 1}`,
          enabled: true,
          mode: "hold",
          trigger: { all: ["mouse.x2"] },
          target: { keys: ["alt_r"] },
        },
      ],
    }));
    setSelectedIndex(config.mappings.length);
  }

  async function saveAndRestart() {
    const api = window.pywebview?.api;
    if (!api) return;
    const saved = await api.save_config(config);
    if (!saved.ok) {
      setNotice(saved.error ?? "Save failed.");
      return;
    }
    const started = await api.start_mapping(config);
    setRunning(started.ok);
    setNotice(started.ok ? "Saved and restarted." : started.error ?? "Start failed.");
  }

  async function stopMapping() {
    const api = window.pywebview?.api;
    if (!api) return;
    await api.stop_mapping();
    setRunning(false);
    setNotice("Stopped.");
  }

  return (
    <main className="app">
      <section className="sidebar">
        <div className="brand">
          <img src="./logo.svg" alt="" />
          <div>
            <strong>KeyFlow</strong>
            <span>Mapper</span>
          </div>
        </div>

        <div className={running ? "status running" : "status"}>
          <i />
          <div>
            <strong>{running ? "Listening" : "Stopped"}</strong>
            <span>{notice}</span>
          </div>
        </div>

        <div className="rule-list">
          <div className="section-label">Rules</div>
          {config.mappings.map((mapping, index) => (
            <button
              className={index === selectedIndex ? "rule-card active" : "rule-card"}
              key={`${mapping.name}-${index}`}
              onClick={() => setSelectedIndex(index)}
              type="button"
            >
              <span>{mapping.name}</span>
              <small>
                {mapping.trigger.all.join(" + ")} {"->"} {mapping.target.keys.join(" + ")}
              </small>
            </button>
          ))}
          <button className="ghost-button" onClick={addMapping} type="button">
            New rule
          </button>
        </div>
      </section>

      <section className="content">
        <header className="topbar">
          <div>
            <p className="kicker">Typeless Voice Trigger</p>
            <h1>Mouse side button to Right Alt.</h1>
            <span>Auto-start is on. Hold your mouse side button and watch the activity log.</span>
          </div>
          <div className="top-actions">
            <button className="secondary" onClick={stopMapping} type="button">
              Stop
            </button>
            <button className="primary" onClick={saveAndRestart} type="button">
              Save & Start
            </button>
          </div>
        </header>

        <section className="workspace">
          <div className="panel editor">
            <div className="field-row">
              <label>
                Rule name
                <input
                  value={selected.name}
                  onChange={(event) => updateSelected({ name: event.target.value })}
                />
              </label>
              <label className="toggle">
                <input
                  checked={selected.enabled}
                  onChange={(event) => updateSelected({ enabled: event.target.checked })}
                  type="checkbox"
                />
                <span>Enabled</span>
              </label>
            </div>

            <div className="mode-picker">
              <button
                className={selected.mode === "hold" ? "mode active" : "mode"}
                onClick={() => updateSelected({ mode: "hold" })}
                type="button"
              >
                <strong>Hold mode</strong>
                <span>Hold Right Alt while the trigger is held.</span>
              </button>
              <button
                className={selected.mode === "tap" ? "mode active" : "mode"}
                onClick={() => updateSelected({ mode: "tap" })}
                type="button"
              >
                <strong>Tap mode</strong>
                <span>Send the target key once when the trigger appears.</span>
              </button>
            </div>

            <div className="device-area">
              <MouseDiagram selected={selected.trigger.all} onToggle={toggleTrigger} />
              <div className="picker-panel">
                <div className="section-label">Trigger</div>
                <div className="choice-grid">
                  {triggerOptions.map((option) => (
                    <button
                      className={selected.trigger.all.includes(option.token) ? "choice active" : "choice"}
                      key={option.token}
                      onClick={() => toggleTrigger(option.token)}
                      type="button"
                    >
                      <strong>{option.label}</strong>
                      <span>{option.hint}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="target-panel">
              <div>
                <div className="section-label">Target</div>
                <h2>{labelFor(selected.target.keys[0], targetOptions)}</h2>
              </div>
              <div className="target-grid">
                {targetOptions.map((option) => (
                  <button
                    className={selected.target.keys[0] === option.token ? "target active" : "target"}
                    key={option.token}
                    onClick={() => setTarget(option.token)}
                    type="button"
                  >
                    <strong>{option.label}</strong>
                    <span>{option.token}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <aside className="panel diagnostics">
            <div className="section-label">Test</div>
            <ol>
              <li>Confirm the status says Listening.</li>
              <li>Open Typeless and keep this app running.</li>
              <li>Hold your mouse side button.</li>
              <li>Check the log for Mouse down and Pressed target.</li>
            </ol>

            <div className="log-card">
              <div className="section-label">Activity</div>
              {logs.map((line, index) => (
                <p key={`${line}-${index}`}>{line}</p>
              ))}
            </div>

            <details>
              <summary>Config preview</summary>
              <pre>{jsonPreview}</pre>
            </details>
          </aside>
        </section>
      </section>
    </main>
  );
}

function MouseDiagram({ selected, onToggle }: { selected: string[]; onToggle: (token: string) => void }) {
  return (
    <div className="mouse-card">
      <div>
        <div className="section-label">Mouse</div>
        <h2>Mouse trigger</h2>
      </div>
      <div className="mouse-body" aria-label="鼠标按键示意">
        <button
          className={selected.includes("mouse.left") ? "mouse-left active" : "mouse-left"}
          onClick={() => onToggle("mouse.left")}
          type="button"
        />
        <button
          className={selected.includes("mouse.right") ? "mouse-right active" : "mouse-right"}
          onClick={() => onToggle("mouse.right")}
          type="button"
        />
        <button
          className={selected.includes("mouse.middle") ? "mouse-wheel active" : "mouse-wheel"}
          onClick={() => onToggle("mouse.middle")}
          type="button"
        />
        <button
          className={selected.includes("mouse.x1") ? "side-one active" : "side-one"}
          onClick={() => onToggle("mouse.x1")}
          type="button"
        >
          S1
        </button>
        <button
          className={selected.includes("mouse.x2") ? "side-two active" : "side-two"}
          onClick={() => onToggle("mouse.x2")}
          type="button"
        >
          S2
        </button>
      </div>
    </div>
  );
}

function labelFor(token: string, options: Array<{ token: string; label: string }>) {
  return options.find((option) => option.token === token)?.label ?? token;
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
