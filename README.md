# KeyFlow Mapper

KeyFlow Mapper 是一个面向普通用户的键盘/鼠标映射小工具。它由两部分组成：

- `key_mapper_sdk/`: Windows 全局键鼠监听与按键模拟引擎。
- `ui/`: 前端配置界面，用来可视化创建 `mappings.json`。

默认用途已经按 Typeless 语音输入配置好：

按住鼠标侧键 1 (`mouse.x1`) -> 模拟按住 `Alt`  
松开鼠标侧键 1 -> 释放 `Alt`

## 前端 UI

```powershell
cd ui
npm install
npm run dev
```

打开浏览器里的本地地址后，可以：

- 选择鼠标左键、右键、中键、侧键 1、侧键 2。
- 选择键盘上的 Alt、Ctrl、Shift、Space、Tab 和常用字母键。
- 设置 `hold` 或 `tap` 模式。
- 导出或复制 `mappings.json`。

## 运行映射引擎

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m key_mapper_sdk --check
.\.venv\Scripts\python -m key_mapper_sdk
```

## 打包 Windows exe

```powershell
.\build.ps1
```

打包产物会生成在 `release/`：

- `release/KeyMapperSDK.exe`
- `release/config/mappings.json`
- `release/KeyMapperSDK.zip`

## 配置格式

```json
{
  "mappings": [
    {
      "name": "Typeless voice trigger",
      "enabled": true,
      "mode": "hold",
      "trigger": {
        "all": ["mouse.x1"]
      },
      "target": {
        "keys": ["alt"]
      }
    }
  ]
}
```

## 常用 token

- 鼠标：`mouse.left`, `mouse.right`, `mouse.middle`, `mouse.x1`, `mouse.x2`
- 修饰键：`alt`, `ctrl`, `shift`
- 系统键：`space`, `tab`, `enter`, `esc`
- 字母键：`key.a`, `key.b`, `key.c`

## 模式

- `hold`: 触发键按住时按住目标键，触发键松开时释放目标键。
- `tap`: 触发组合出现时点按一次目标键。
