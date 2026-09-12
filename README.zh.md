![Kotoba Studio — Voice. Code. 日本語 / English.](assets/brand/kotoba-banner.png)

# Kotoba Studio · ことば

**自然表达，清晰确认，与 AI 一起构建。**

[English](README.md) | 中文

面向日语和英语语音输入、AI 对话与开发工作的 Windows 桌面工作空间。从麦克风或应用程序捕获想法，将其变成可编辑的指令，再通过本地模型或云端 API 与智能体协作。

[开始使用](#run) · [语音与本地模型](python/voice/README.md) · [Windows 打包](python/voice/WINDOWS.md) · [日本語](#japanese)

## 从语音到行动，在同一个工作空间完成

说出任务、导入录音，或监听应用程序。Kotoba 在本地转录，先让你检查文本，再由你决定是否发送给智能体。确认姓名、数字和意图后，将审阅过的指令带入所选对话。

桌面集成持久对话、语音面板、文件浏览器、代码查看器和 PowerShell 控制台。模型连接和插件也在同一应用中管理。隐藏面板或切换界面语言时，转录草稿和终端输出会保留。

| 工作对象 | Kotoba 提供的能力 |
| --- | --- |
| 日语与英语 | 英语 Parakeet、日语 Kotoba-Whisper、可选 Whisper 模型和双语控件 |
| 音频来源 | 麦克风、系统音频、应用程序进程捕获和录音文件导入 |
| 本地 AI | 通过内置 llama.cpp CPU 引擎运行 GGUF；连接 Ollama 和 LM Studio |
| 云端 AI | 原生 OpenAI、Anthropic Claude、Kimi 和 DeepSeek API；自定义提供方与按会话选择模型 |
| 智能体工作空间 | 持久会话、文件与终端工具、技能、工作流、子智能体和 Cordis 插件 |
| 可重复的听写流程 | Windows 全局快捷键、光标位置粘贴、保存短语、撤销和经审阅的智能体草稿 |
| 可测量的结果 | 转录延迟、实时因子，以及针对所提供参考文本计算日语字符错误率和英语词错误率 |

### 多个智能体，独立会话

使用 **+ New agent** 或 **Ctrl+T** 打开另一个保留状态的聊天窗口。在各自输入栏选择提供商和模型：OpenAI、Claude、Kimi、DeepSeek 和本地路由可以并行工作。左侧聊天列表每次显示一个会话。选择聊天后，已审阅的语音输入将发送到该会话。列表显示模型、运行状态和后台完成提示，悬浮提示显示完整提供商与模型。双击列表项可命名任务。**Ctrl+Tab** 和 **Ctrl+Shift+Tab** 切换聊天。关闭视图后，已保存会话和运行中的智能体仍保留在主机上；丢弃包含未发送草稿的视图前需要确认。独立浏览器存储在重启后保留各视图的会话选择。共享工作目录的智能体可能编辑相同文件；存在冲突的任务请使用不同目录。

### 聊天与语音并排显示

在智能体工作区旁审阅语音草稿。截图展示审阅框中的示例草稿，尚未发送给提供方。

![Kotoba Studio 0.6.8 英语聊天与语音审阅面板](assets/screenshots/voice-workspace-en.png)

### 更清晰地查看代码

浏览文件、比较标签页，并在需要时搜索。再次点击 **Code**、使用 **Close Code** 或按 **Esc** 返回聊天，已打开的标签页会保留。

![Kotoba Studio 0.6.8 代码工作区、资源管理器、源码标签与关闭按钮](assets/screenshots/code-workspace-en.png)

<a id="run"></a>

## 在 Windows 上开始

桌面版本为 **Kotoba Studio 0.7.1**，是面向 Windows x64 的未签名开发预览版。从构建输出安装 `Kotoba-Studio-0.7.1-Setup.exe`。安装包包含桌面应用、智能体运行时、音频捕获助手和 CPU 推理引擎。语音与语言模型权重单独提供。构建和验证安装包的方法见 [Windows 指南](python/voice/WINDOWS.md)。

1. **选择文件夹。** 为任务指定智能体的工作目录。
2. **连接模型。** 在 **··· → Routing** 中配置 API 提供方，或选择 Configure later 后打开 Local models。注册本地模型后，在聊天输入框中选择 Kotoba Local。
3. **选择监听来源。** 打开 Voice Studio，选择音源、语音语言和转录模型。
4. **确认后再行动。** 录音或导入音频，修正转录，然后使用 **Add to chat** 将文本追加到可编辑的会话草稿。准备好后再发送。

Voice Studio 的 **Agent → Ask voice agent** 还提供独立的智能体会话，其模型选择与主聊天输入框相互独立。两种工作流见[桌面指南](python/voice/README.md)。

| 快捷键 | 操作 |
| --- | --- |
| `Ctrl+K` | 搜索工作空间命令 |
| `Ctrl+Shift+V` | 显示或隐藏 Voice Studio |
| `Ctrl+J` | 显示或隐藏终端 |
| `Ctrl+Shift+E` | 显示或隐藏代码页 |
| `Ctrl+F` | 搜索当前源文件 |
| `Ctrl+W` | 关闭当前源码标签页 |
| `Esc` | 关闭代码搜索，然后返回聊天 |
| `Ctrl+Shift+Space` | 开始或停止录音 |

关闭窗口后 Kotoba 保留在系统托盘；可从托盘菜单重新打开或退出。参阅[托盘行为与图标](python/voice/README.md#system-tray-and-windows-icons)。

<a id="japanese"></a>

## 日本語で使う

Kotoba Studio は、日本語・英語の音声入力から AI との作業へつなぐ Windows アプリです。右上の **English / 日本語** で、デスクトップと主要なチャット操作の表示言語を切り替えられます。会話本文やコードは翻訳しません。

音声スタジオで録音元と言語を選び、録音または音声ファイルの読み込みを行います。文字起こしの名前・数字・意図を確認し、必要に応じて修正してください。**チャットに追加** で会話の下書きに追加します。入力欄が未準備の場合はコピーします。確認してから送信してください。

**ローカルモデル** では GGUF ファイルを同梱の CPU エンジンで実行できます。Ollama / LM Studio への接続も可能です。モデルの重みは別途必要です。登録後、チャットのモデル選択で **Kotoba Local** を選びます。再起動後はローカルエンジンを起動し直してください。

![Kotoba Studio 0.6.8 の日本語インターフェースと音声レビュー](assets/screenshots/voice-workspace-ja.png)

上の画像は、送信前に確認するための入力例です。

## 听写与会议笔记

启用 **Desktop dictation**，通过 **Ctrl+Shift+Space** 向当前应用听写。打开 **Meetings & notes** 选择窗口并按需加入麦克风，保存带时间戳的转录、标记重点并保留可搜索的开发笔记。重点保留原文；AI 跟进从经审阅的草稿开始。模型、捕获边界、隐私和限制见[语音工作流指南](python/voice/VOICE.md)。

## 选择推理的位置

语音识别默认在本地运行，也可明确选择云端语音上传。原生 GGUF 模型也在你的电脑上运行；Ollama 和 LM Studio 连接只接受回环地址。本地连接失败时，不会悄悄回退到云端提供方或重放一次请求。智能体工具在使用时仍可能访问网络。

云端提供方会收到你提交的文本。智能体运行时在本地保存已提交文本和会话历史；捕获的音频保留在内存中。保存短语以未加密文本存储在本地。本地转录前需在音频设置中明确准备语音模型。模型生命周期和连接细节见[桌面指南](python/voice/README.md#local-language-models)。

## 依赖结果之前，先评估

模型质量取决于录音、所选模型、硬件和任务。使用人工审阅的参考文本测量日语 CER 和英语 WER；与自动字幕一致不等于真实准确率。小型 GGUF 冒烟测试只能证明集成连通，不能证明智能体工具调用可靠。

尚未实现说话人分离、流式打断、托管 GPU 推理和 GGUF 自动下载。缺少日语翻译的扩展会回退到英语。授予智能体工作目录访问权限前，请阅读 [SAFETY.md](SAFETY.zh.md)。

<a id="run-from-source"></a>

## 构建与贡献

从[桌面开发指南](python/voice/README.md#development)开始，其中介绍 Python 应用、匹配的智能体 SDK、本地语音评估和本地模型行为。[Windows 打包指南](python/voice/WINDOWS.md)介绍可安装的可执行文件。

底层智能体系统见[架构](docs/architecture.zh.md)、[开发](docs/development.zh.md)和[贡献](CONTRIBUTING.zh.md)。[集成检查](python/voice/INSPECTION.md)说明上游组件如何组合。

## 开源基础

Kotoba Studio 基于真实的 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 运行时和插件架构构建。音频捕获与保存短语的集成取自 [OpenWhispr](https://github.com/OpenWhispr/openwhispr)；本地原生推理使用 [llama.cpp](https://github.com/ggml-org/llama.cpp)。在兼容性、提供方选择和署名需要的地方保留上游标识。

[MIT 许可证](LICENSE) · [第三方声明](THIRD_PARTY_NOTICES.md) · [随包许可证](python/voice/THIRD_PARTY_LICENSES)
