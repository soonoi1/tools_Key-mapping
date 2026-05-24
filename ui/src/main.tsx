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
  { token: "mouse.left", label: "左键", hint: "点击常用，不建议默认占用" },
  { token: "mouse.right", label: "右键", hint: "可与侧键组合" },
  { token: "mouse.middle", label: "中键", hint: "滚轮按下" },
  { token: "mouse.x1", label: "侧键 1", hint: "推荐，用作 Typeless 唤醒" },
  { token: "mouse.x2", label: "侧键 2", hint: "备用侧键" },
  { token: "ctrl", label: "Ctrl", hint: "键盘组合" },
  { token: "shift", label: "Shift", hint: "键盘组合" },
  { token: "tab", label: "Tab", hint: "键盘组合" },
];

const targetOptions = [
  { token: "alt_r", label: "右 Alt", hint: "Typeless 推荐" },
  { token: "alt_l", label: "左 Alt", hint: "左侧 Alt" },
  { token: "alt", label: "Alt", hint: "系统默认 Alt" },
  { token: "ctrl", label: "Ctrl", hint: "控制键" },
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
  const [logs, setLogs] = useState<string[]>(["应用已就绪，默认使用鼠标侧键 1 触发右 Alt。"]);
  const [notice, setNotice] = useState("打开应用后会自动启动映射。");

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
      setNotice(started.ok ? "映射已自动启动。按住侧键 1 测试 Typeless。" : started.error ?? "自动启动失败。");
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
          name: `新映射 ${current.mappings.length + 1}`,
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
      setNotice(saved.error ?? "保存失败。");
      return;
    }
    const started = await api.start_mapping(config);
    setRunning(started.ok);
    setNotice(started.ok ? "已保存并重新启动映射。" : started.error ?? "启动失败。");
  }

  async function stopMapping() {
    const api = window.pywebview?.api;
    if (!api) return;
    await api.stop_mapping();
    setRunning(false);
    setNotice("映射已停止。");
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
            <strong>{running ? "正在监听" : "未运行"}</strong>
            <span>{notice}</span>
          </div>
        </div>

        <div className="rule-list">
          <div className="section-label">映射方案</div>
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
            新增映射
          </button>
        </div>
      </section>

      <section className="content">
        <header className="topbar">
          <div>
            <p className="kicker">Typeless Voice Trigger</p>
            <h1>把鼠标侧键变成右 Alt。</h1>
            <span>默认已自动启动。按住侧键 1 时，会持续发送键盘右侧 Alt。</span>
          </div>
          <div className="top-actions">
            <button className="secondary" onClick={stopMapping} type="button">
              停止
            </button>
            <button className="primary" onClick={saveAndRestart} type="button">
              保存并启动
            </button>
          </div>
        </header>

        <section className="workspace">
          <div className="panel editor">
            <div className="field-row">
              <label>
                映射名称
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
                <span>启用</span>
              </label>
            </div>

            <div className="mode-picker">
              <button
                className={selected.mode === "hold" ? "mode active" : "mode"}
                onClick={() => updateSelected({ mode: "hold" })}
                type="button"
              >
                <strong>按住触发</strong>
                <span>按下侧键时按住右 Alt，松开侧键时释放。</span>
              </button>
              <button
                className={selected.mode === "tap" ? "mode active" : "mode"}
                onClick={() => updateSelected({ mode: "tap" })}
                type="button"
              >
                <strong>点按触发</strong>
                <span>触发组合出现时，只发送一次目标键。</span>
              </button>
            </div>

            <div className="device-area">
              <MouseDiagram selected={selected.trigger.all} onToggle={toggleTrigger} />
              <div className="picker-panel">
                <div className="section-label">触发按键</div>
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
                <div className="section-label">映射目标</div>
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
            <div className="section-label">测试步骤</div>
            <ol>
              <li>确认右上角显示“正在监听”。</li>
              <li>打开 Typeless。</li>
              <li>按住鼠标侧键 1，不要点 App 内按钮。</li>
              <li>如果 Typeless 没反应，点“保存并启动”再测一次。</li>
            </ol>

            <div className="log-card">
              <div className="section-label">运行日志</div>
              {logs.map((line, index) => (
                <p key={`${line}-${index}`}>{line}</p>
              ))}
            </div>

            <details>
              <summary>配置预览</summary>
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
        <h2>选择鼠标动作</h2>
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
