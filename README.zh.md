# Kotoba Studio

![Kotoba Studio — Voice. Code. 日本語 / English.](assets/brand/kotoba-banner.png)

**面向日语和英语的 AI 语音开发工作空间。**

[Windows 安装](python/voice/WINDOWS.md) · [本地模型](python/voice/README.md#local-language-models) · [架构](docs/architecture.zh.md)

Kotoba Studio 将语音、对话、代码、终端和模型接入整合到 Windows 桌面应用中。用日语或英语说话，检查转写，再选择本地模型或 API 提供方执行任务。底层使用完整的 DeepSeek Harness 智能体运行时。

[English](README.md) | 中文

## 工作空间

紧凑活动栏可打开对话、文件、接入设置、插件和本地模型。可调整宽度的语音面板位于工作区旁，终端在下方展开。右上角 English / 日本語 同时切换原生界面和核心对话控件，无需刷新会话。

| 工作流 | 当前功能 |
| --- | --- |
| 语音输入 | 本地 Whisper 转写；麦克风、系统音频、应用进程录音和音频导入 |
| 日语与英语 | 明确或自动选择语音语言；507 条日语界面翻译；术语提示和转写检查 |
| 原生本地模型 | 同梱 llama.cpp CPU 引擎运行 GGUF，也可连接 Ollama 和 LM Studio |
| 完整智能体框架 | 持久会话、工具、技能、子代理、工作流、智能体预设和 Cordis 插件 |
| 模型接入 | 提供方端点、凭据管理、模型发现和会话级模型选择 |
| 开发工作区 | 文件浏览、代码预览、持久 PowerShell 控制台和原有智能体工具界面 |
| 听写工作流 | OpenWhispr 衍生录音与常用短语；Unicode 边界匹配、撤销和确认后转交文本 |
| 可测量质量 | 转写延迟、实时因子、基于参考文本的日语 CER / 英语 WER 和智能体用量统计 |

**Ctrl+K** 打开命令面板。**Ctrl+Shift+V** 切换语音工作室。**Ctrl+J** 切换终端。**Ctrl+Shift+E** 打开代码浏览器。

<a id="run"></a>

## 在 Windows 上运行

构建或安装 `Kotoba-Studio-0.4.0-Setup.exe`。安装包包含 Python、Qt WebEngine、匹配的智能体运行时、录音助手和 CPU 推理引擎。模型权重需另行准备。构建和验证步骤见 [Windows 指南](python/voice/WINDOWS.md)。

1. 打开工作文件夹。
2. 在 **Routing** 配置提供方，或选择 **Configure later** 后打开 **Local models**。
3. 选择兼容的 GGUF 模型，启动并注册。在对话输入栏选择 **Kotoba Local**。
4. 在 **Voice Studio** 选择录音源、输入语言和语音模型。
5. 录音或导入音频，检查名字和数字后，再发送已确认的指令。

本地模型请求只发往回环地址。服务器不可用时报告错误，不自动切换云端，也不重放指令。智能体工具仍可按任务访问网络。录音保留在内存；提交的文本和会话由运行时保存到本机。API 提供方会收到明确发送给它的文本。

## 日本語で使う

右上の **English / 日本語** で表示言語を切り替えます。音声スタジオで録音元・言語・音声モデルを選択し、文字起こしの名前と数字を確認してから送信してください。会話本文やコードそのものは翻訳しません。日本語未対応の拡張機能の文言は英語で表示します。

**ローカルモデル** で GGUF を選択すると、同梱の CPU エンジンで実行できます。Ollama / LM Studio への接続も可能です。登録後、チャットでは **Kotoba Local** を選びます。アプリを再起動した後は推論エンジンを再度起動してください。モデルの重みはインストーラーに含まれません。

<a id="run-from-source"></a>

## 开发

```powershell
git clone https://github.com/jon-jc/japan-ai-harness.git
cd japan-ai-harness
pnpm install --frozen-lockfile
pnpm run build:official
python -m venv .venv
.venv/Scripts/python -m pip install -e "python/voice[test]"
.venv/Scripts/python -m pip install --no-deps -e python/sdk
.venv/Scripts/python python/voice/prepare_local_runtime.py
.venv/Scripts/python -m kotoba.workspace
```

未找到打包运行时时，开发应用使用已构建的检出版本 CLI。Windows 安装包需要匹配的原生运行时和录音助手，请参阅[打包指南](python/voice/WINDOWS.md)。运行 `python -m pytest python/voice/tests` 检查语音应用，运行 `pnpm run test:gui` 检查客户端界面。另见[开发指南](docs/development.zh.md)、[贡献指南](CONTRIBUTING.zh.md)和[集成检查](python/voice/INSPECTION.md)。

## 工程边界

这是未签名的开发预览版，尚未通过生产资格验证。语音和智能体质量取决于模型、录音、硬件和任务。小型 GGUF 集成测试不能证明日语准确率或工具使用可靠性。自动字幕一致率不能替代人工校验的参考文本。

尚未实现说话人分离、流式打断、托管 GPU 推理、GGUF 权重自动下载和全局光标粘贴。语音模型首次使用可能需要下载。未提供日语词条的扩展回退到英语。授权智能体访问工作目录前，请阅读[安全说明](SAFETY.zh.md)。

## 开源基础

Kotoba Studio 基于 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 分支，保留实际运行时和 Cordis 插件架构。语音工作流整合了 [OpenWhispr](https://github.com/OpenWhispr/openwhispr) 代码，本地推理使用 [llama.cpp](https://github.com/ggml-org/llama.cpp)。保留上游包标识和 API 提供方名称以维持兼容性与署名。

[MIT 许可证](LICENSE) · [第三方声明](THIRD_PARTY_NOTICES.md) · [同梱运行时许可证](python/voice/THIRD_PARTY_LICENSES)
