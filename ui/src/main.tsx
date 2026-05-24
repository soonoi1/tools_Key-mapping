import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type MappingMode = "hold" | "tap";

type Mapping = {
  id: string;
  name: string;
  enabled: boolean;
  mode: MappingMode;
  trigger: string[];
  target: string[];
};

type Option = {
  token: string;
  label: string;
  group: "mouse" | "keyboard" | "system";
};

const triggerOptions: Option[] = [
  { token: "mouse.left", label: "鼠标左键", group: "mouse" },
  { token: "mouse.right", label: "鼠标右键", group: "mouse" },
  { token: "mouse.middle", label: "滚轮中键", group: "mouse" },
  { token: "mouse.x1", label: "侧键 1", group: "mouse" },
  { token: "mouse.x2", label: "侧键 2", group: "mouse" },
  { token: "alt", label: "Alt", group: "keyboard" },
  { token: "ctrl", label: "Ctrl", group: "keyboard" },
  { token: "shift", label: "Shift", group: "keyboard" },
  { token: "space", label: "Space", group: "keyboard" },
  { token: "tab", label: "Tab", group: "keyboard" },
  { token: "key.a", label: "A", group: "keyboard" },
  { token: "key.s", label: "S", group: "keyboard" },
  { token: "key.d", label: "D", group: "keyboard" },
  { token: "key.f", label: "F", group: "keyboard" },
];

const targetOptions: Option[] = [
  { token: "alt", label: "Alt", group: "system" },
  { token: "ctrl", label: "Ctrl", group: "system" },
  { token: "shift", label: "Shift", group: "system" },
  { token: "space", label: "Space", group: "system" },
  { token: "tab", label: "Tab", group: "system" },
  { token: "enter", label: "Enter", group: "system" },
  { token: "esc", label: "Esc", group: "system" },
  { token: "key.a", label: "A", group: "keyboard" },
  { token: "key.c", label: "C", group: "keyboard" },
  { token: "key.v", label: "V", group: "keyboard" },
];

const initialMappings: Mapping[] = [
  {
    id: crypto.randomUUID(),
    name: "Typeless 语音唤醒",
    enabled: true,
    mode: "hold",
    trigger: ["mouse.x1"],
    target: ["alt"],
  },
];

function App() {
  const [mappings, setMappings] = useState<Mapping[]>(initialMappings);
  const [selectedId, setSelectedId] = useState(initialMappings[0].id);
  const [copied, setCopied] = useState(false);

  const selectedMapping = mappings.find((mapping) => mapping.id === selectedId) ?? mappings[0];
  const enabledCount = mappings.filter((mapping) => mapping.enabled).length;

  const generatedConfig = useMemo(
    () => ({
      mappings: mappings.map((mapping) => ({
        name: mapping.name,
        enabled: mapping.enabled,
        mode: mapping.mode,
        trigger: { all: mapping.trigger },
        target: { keys: mapping.target },
      })),
    }),
    [mappings],
  );

  const jsonPreview = useMemo(() => JSON.stringify(generatedConfig, null, 2), [generatedConfig]);

  function updateSelected(next: Partial<Mapping>) {
    setMappings((current) =>
      current.map((mapping) => (mapping.id === selectedMapping.id ? { ...mapping, ...next } : mapping)),
    );
  }

  function toggleTrigger(token: string) {
    const hasToken = selectedMapping.trigger.includes(token);
    const trigger = hasToken
      ? selectedMapping.trigger.filter((item) => item !== token)
      : [...selectedMapping.trigger, token];
    updateSelected({ trigger: trigger.length ? trigger : selectedMapping.trigger });
  }

  function setTarget(token: string) {
    updateSelected({ target: [token] });
  }

  function addMapping() {
    const mapping: Mapping = {
      id: crypto.randomUUID(),
      name: `新映射 ${mappings.length + 1}`,
      enabled: true,
      mode: "hold",
      trigger: ["mouse.x2"],
      target: ["alt"],
    };
    setMappings((current) => [...current, mapping]);
    setSelectedId(mapping.id);
  }

  function removeSelected() {
    if (mappings.length === 1) return;
    const next = mappings.filter((mapping) => mapping.id !== selectedMapping.id);
    setMappings(next);
    setSelectedId(next[0].id);
  }

  async function copyConfig() {
    await navigator.clipboard.writeText(jsonPreview);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  function downloadConfig() {
    const blob = new Blob([jsonPreview], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "mappings.json";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="app-shell">
      <section className="hero" aria-labelledby="page-title">
        <div className="hero-copy">
          <div className="brand-mark">
            <img src="/logo.svg" alt="KeyFlow Mapper logo" />
            <span>KeyFlow Mapper</span>
          </div>
          <p className="eyebrow">鼠标与键盘映射配置器</p>
          <h1 id="page-title">把不想按的键，交给更顺手的动作。</h1>
          <p className="hero-text">
            为 Typeless、AI 语音输入和高频快捷键设计。选择鼠标或键盘组合，映射成 Alt、Ctrl、
            Shift 或任意常用按键。
          </p>
          <div className="hero-actions">
            <button className="primary-action" type="button" onClick={downloadConfig}>
              导出 mappings.json
            </button>
            <button className="secondary-action" type="button" onClick={copyConfig}>
              {copied ? "已复制" : "复制配置"}
            </button>
          </div>
        </div>
        <div className="hero-card" aria-label="当前映射概览">
          <span className="pulse-dot" />
          <strong>{enabledCount} 条映射运行中</strong>
          <p>默认：按住鼠标侧键 1，即模拟按住 Alt。</p>
          <div className="route-preview">
            <span>Side 1</span>
            <i />
            <span>Alt</span>
          </div>
        </div>
      </section>

      <section className="workspace" aria-label="映射配置工作台">
        <aside className="panel mapping-list" aria-label="映射列表">
          <div className="panel-heading">
            <p className="eyebrow">Rules</p>
            <h2>映射方案</h2>
          </div>
          <div className="mapping-stack">
            {mappings.map((mapping) => (
              <button
                className={`mapping-item ${mapping.id === selectedMapping.id ? "active" : ""}`}
                key={mapping.id}
                type="button"
                onClick={() => setSelectedId(mapping.id)}
              >
                <span>{mapping.name}</span>
                <small>
                  {mapping.trigger.join(" + ")} {"->"} {mapping.target.join(" + ")}
                </small>
              </button>
            ))}
          </div>
          <button className="add-rule" type="button" onClick={addMapping}>
            新增映射
          </button>
        </aside>

        <section className="panel editor" aria-label="编辑当前映射">
          <div className="editor-topline">
            <label>
              映射名称
              <input
                value={selectedMapping.name}
                onChange={(event) => updateSelected({ name: event.target.value })}
              />
            </label>
            <label className="switch">
              <input
                checked={selectedMapping.enabled}
                type="checkbox"
                onChange={(event) => updateSelected({ enabled: event.target.checked })}
              />
              <span>启用</span>
            </label>
          </div>

          <div className="mode-grid" role="radiogroup" aria-label="映射模式">
            <button
              className={selectedMapping.mode === "hold" ? "selected" : ""}
              type="button"
              onClick={() => updateSelected({ mode: "hold" })}
            >
              <strong>按住映射</strong>
              <span>按住触发键时持续按住目标键，松开后释放。</span>
            </button>
            <button
              className={selectedMapping.mode === "tap" ? "selected" : ""}
              type="button"
              onClick={() => updateSelected({ mode: "tap" })}
            >
              <strong>点击映射</strong>
              <span>触发组合出现时，只点按一次目标键。</span>
            </button>
          </div>

          <div className="device-grid">
            <MousePicker selected={selectedMapping.trigger} onToggle={toggleTrigger} />
            <KeyboardPicker
              selected={selectedMapping.trigger}
              selectedTarget={selectedMapping.target[0]}
              onToggleTrigger={toggleTrigger}
              onTarget={setTarget}
            />
          </div>

          <div className="target-row">
            <label>
              映射目标
              <select value={selectedMapping.target[0]} onChange={(event) => setTarget(event.target.value)}>
                {targetOptions.map((option) => (
                  <option key={option.token} value={option.token}>
                    {option.label} ({option.token})
                  </option>
                ))}
              </select>
            </label>
            <div className="chips" aria-label="当前触发组合">
              {selectedMapping.trigger.map((token) => (
                <span key={token}>{token}</span>
              ))}
            </div>
            <button className="danger-action" type="button" onClick={removeSelected} disabled={mappings.length === 1}>
              删除
            </button>
          </div>
        </section>

        <aside className="panel output-panel" aria-label="配置输出">
          <div className="panel-heading">
            <p className="eyebrow">Output</p>
            <h2>生成配置</h2>
          </div>
          <pre>{jsonPreview}</pre>
          <div className="note-card">
            <strong>怎么用</strong>
            <p>
              点击导出后，把下载的 <code>mappings.json</code> 放到
              <code> release/config/ </code>目录，再启动 KeyMapperSDK.exe。
            </p>
          </div>
        </aside>
      </section>
    </main>
  );
}

function MousePicker({ selected, onToggle }: { selected: string[]; onToggle: (token: string) => void }) {
  const mouseButtons = triggerOptions.filter((option) => option.group === "mouse");

  return (
    <section className="device-card">
      <div>
        <p className="eyebrow">Mouse</p>
        <h3>鼠标按键</h3>
      </div>
      <div className="mouse-visual" aria-hidden="true">
        <button
          className={selected.includes("mouse.left") ? "active left-button" : "left-button"}
          aria-label="切换鼠标左键触发"
          type="button"
          onClick={() => onToggle("mouse.left")}
        />
        <button
          className={selected.includes("mouse.right") ? "active right-button" : "right-button"}
          aria-label="切换鼠标右键触发"
          type="button"
          onClick={() => onToggle("mouse.right")}
        />
        <button
          className={selected.includes("mouse.middle") ? "active wheel-button" : "wheel-button"}
          aria-label="切换鼠标中键触发"
          type="button"
          onClick={() => onToggle("mouse.middle")}
        />
        <button
          className={selected.includes("mouse.x1") ? "active side-one" : "side-one"}
          aria-label="切换鼠标侧键 1 触发"
          type="button"
          onClick={() => onToggle("mouse.x1")}
        />
        <button
          className={selected.includes("mouse.x2") ? "active side-two" : "side-two"}
          aria-label="切换鼠标侧键 2 触发"
          type="button"
          onClick={() => onToggle("mouse.x2")}
        />
      </div>
      <div className="option-grid">
        {mouseButtons.map((option) => (
          <TogglePill
            key={option.token}
            active={selected.includes(option.token)}
            label={option.label}
            token={option.token}
            onClick={() => onToggle(option.token)}
          />
        ))}
      </div>
    </section>
  );
}

function KeyboardPicker({
  selected,
  selectedTarget,
  onToggleTrigger,
  onTarget,
}: {
  selected: string[];
  selectedTarget: string;
  onToggleTrigger: (token: string) => void;
  onTarget: (token: string) => void;
}) {
  const keyboardButtons = triggerOptions.filter((option) => option.group === "keyboard");

  return (
    <section className="device-card">
      <div>
        <p className="eyebrow">Keyboard</p>
        <h3>键盘按键</h3>
      </div>
      <div className="keyboard-visual">
        {keyboardButtons.map((option) => (
          <button
            className={selected.includes(option.token) ? "keycap active" : "keycap"}
            key={option.token}
            type="button"
            onClick={() => onToggleTrigger(option.token)}
          >
            {option.label}
          </button>
        ))}
      </div>
      <div className="target-strip">
        {targetOptions.slice(0, 7).map((option) => (
          <button
            className={selectedTarget === option.token ? "target-chip active" : "target-chip"}
            key={option.token}
            type="button"
            onClick={() => onTarget(option.token)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </section>
  );
}

function TogglePill({
  active,
  label,
  token,
  onClick,
}: {
  active: boolean;
  label: string;
  token: string;
  onClick: () => void;
}) {
  return (
    <button className={active ? "toggle-pill active" : "toggle-pill"} type="button" onClick={onClick}>
      <span>{label}</span>
      <small>{token}</small>
    </button>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
