![Kotoba Studio — Voice. Code. 日本語 / English.](assets/brand/kotoba-banner.png)

# Kotoba Studio · ことば

**自然表达，清晰确认，与 AI 一起构建。**

[English](README.md) | 中文

[中文](#english) · [日本語](#japanese)

面向日语和英语语音输入、AI 对话与开发工作的 Windows 桌面工作空间。从麦克风或应用程序捕获想法，将其变成可编辑的指令，再通过本地模型或云端 API 与智能体协作。

[开始使用](#run) · [语音与本地模型](python/voice/README.md) · [Windows 打包](python/voice/WINDOWS.md) · [日本語](#japanese)

<a id="english"></a>

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

截图来自运行中的 0.7.3 应用，聊天和语音均已选择 **OpenAI → GPT-6 Astra**。提供商菜单仅显示已配置的提供商；旁边的模型菜单显示所选提供商的模型。聊天和语音草稿均为手动输入且未发送的示例，并非转写结果或生成的回答。

### 多个智能体，独立会话

使用 **+ New agent** 或 **Ctrl+T** 打开另一个保留状态的聊天窗口。在各自输入栏选择提供商和模型：OpenAI、Claude、Kimi、DeepSeek 和本地路由可以并行工作。左侧聊天列表每次显示一个会话。选择聊天后，已审阅的语音输入将发送到该会话。列表显示模型、运行状态和后台完成提示，悬浮提示显示完整提供商与模型。双击列表项可命名任务。**Ctrl+Tab** 和 **Ctrl+Shift+Tab** 切换聊天。关闭视图后，已保存会话和运行中的智能体仍保留在主机上；丢弃包含未发送草稿的视图前需要确认。独立浏览器存储在重启后保留各视图的会话选择。共享工作目录的智能体可能编辑相同文件；存在冲突的任务请使用不同目录。

![Kotoba Studio 0.7.3：左侧的独立智能体列表](assets/screenshots/agents-workspace-en.png)

### 聊天与语音并排显示

在智能体工作区旁审阅语音草稿。截图展示审阅框中的示例草稿，尚未发送给提供方。

![Kotoba Studio 0.7.3 英语聊天与语音审阅面板](assets/screenshots/voice-workspace-en.png)

### 更清晰地查看代码

浏览文件、比较标签页，并在需要时搜索。再次点击 **Code**、使用 **Close Code** 或按 **Esc** 返回聊天，已打开的标签页会保留。

![Kotoba Studio 0.7.3 代码工作区、资源管理器、源码标签与关闭按钮](assets/screenshots/code-workspace-en.png)

<a id="run"></a>

## 在 Windows 上开始

桌面版本为 **Kotoba Studio 0.8.0**，是面向 Windows x64 的未签名开发预览版。从构建输出安装 `Kotoba-Studio-0.8.0-Setup.exe`。安装包包含桌面应用、智能体运行时、音频捕获助手和 CPU 推理引擎。语音与语言模型权重单独提供。构建和验证安装包的方法见 [Windows 指南](python/voice/WINDOWS.md)。

1. **选择文件夹。** 为任务指定智能体的工作目录。
2. **连接模型。** 在 **··· → Routing** 中配置 API 提供方，或选择 Configure later 后打开 Local models。注册本地模型后，在聊天输入框中选择 Kotoba Local。
3. **选择监听来源。** 打开 Voice Studio，选择音源、语音语言和转录模型。
4. **确认后再行动。** 录音或导入音频，修正转录，然后使用 **Add to chat** 将文本追加到可编辑的会话草稿。准备好后再发送。

Voice Studio 的 **Agent → Ask voice agent** 还提供独立的智能体会话，其模型选择与主聊天输入框相互独立。两种工作流见[桌面指南](python/voice/README.md)。

| 快捷键 | 操作 |
| --- | --- |
| `Ctrl+T` / `Ctrl+Tab` | 新建智能体 / 切换聊天 |
| `Ctrl+K` | 搜索工作空间命令 |
| `Ctrl+Shift+V` | 显示或隐藏 Voice Studio |
| `Ctrl+J` | 显示或隐藏终端 |
| `Ctrl+Shift+E` | 显示或隐藏代码页 |
| `Ctrl+F` | 搜索当前源文件 |
| `Ctrl+W` | 关闭当前源码标签页 |
| `Esc` | 关闭代码搜索，然后返回聊天 |
| `Ctrl+Shift+Space` | 开始或停止录音 |

关闭窗口后 Kotoba 保留在系统托盘；可从托盘菜单重新打开或退出。参阅[托盘行为与图标](python/voice/README.md#system-tray-and-windows-icons)。

## 听写与会议笔记

启用 **Desktop dictation**，通过 **Ctrl+Shift+Space** 向当前应用听写。打开 **Meetings & notes** 选择窗口并按需加入麦克风，保存带时间戳的转录、标记重点并保留可搜索的开发笔记。重点保留原文；AI 跟进从经审阅的草稿开始。模型、捕获边界、隐私和限制见[语音工作流指南](python/voice/VOICE.md)。

## 英日团队交接

从 **··· → Team handoffs** 管理原文、术语、英文和日文摘要以及经过审核的决定和行动项。复制会议到交接，准备给所选语音智能体的明确请求，然后导入 JSON 回复进行审核。通过复制或导出双语 Markdown 分享。交接保存在本机；翻译使用手动请求与导入流程，没有远程团队同步。参见[交接流程](python/voice/WINDOWS.md#englishjapanese-team-handoffs)。

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

---

<a id="japanese"></a>

## 日本語 — 声から、開発へ。

Kotoba Studio は、日本語と英語の音声入力、AI エージェント、開発作業を一つにまとめた Windows デスクトップアプリです。ローカルモデルやクラウド API を選び、複数のエージェントを独立したチャットで動かせます。音声で伝えた内容は、送信前に確認・編集できます。

### 複数のエージェントを、左の一覧で管理

左側の一覧から、作業したいチャットを選びます。チャットごとに下書きとモデルを管理し、別のエージェントはバックグラウンドで実行を続けられます。実行中・完了の状態も一覧で確認できます。

**＋ 新しいエージェント** または **Ctrl+T** でチャットを追加し、ワークスペースとモデルを選択してください。検索、名前のダブルクリックによる変更、**Ctrl+Tab** での切り替えに対応しています。**履歴とワークスペース** から保存済みの会話を開き、**エージェントに戻る** で一覧に戻れます。同じファイルへの編集が競合しそうな場合は、作業フォルダーを分けてください。

![Kotoba Studio 0.7.3：日本語のエージェント一覧と送信前の下書き](assets/screenshots/agents-workspace-ja.png)

### 音声を確認して、次のアクションへ

**音声** を開き、マイク、システム音声、アプリの音声、または音声ファイルを選びます。ローカルで文字起こしを行う前に、**音声設定 → モデルを準備** でモデルをダウンロードしてください。英語は NVIDIA Parakeet、日本語は Kotoba-Whisper が初期設定です。ほかの Whisper モデルも選べます。

名前・数字・意図を確認して修正し、**チャットに追加** で選択中の会話の下書きに入れます。内容を確認してから送信してください。デスクトップ音声入力を有効にすると、**Ctrl+Shift+Space** でカーソル位置に入力できます。会議とノートの機能では、時刻付きの文字起こし、重要箇所、検索できるメモを残せます。詳しくは[音声ワークフロー](python/voice/VOICE.md)をご覧ください。

![Kotoba Studio 0.7.3：日本語の音声スタジオと会議後のタスク整理の入力例](assets/screenshots/voice-workspace-ja.png)

### コードとツールを、同じアプリで

ファイル一覧、ソースコードのタブ、検索、PowerShell ターミナルを利用できます。**コード** を再度クリックするか、**コードを閉じる** または **Esc** で会話に戻れます。Harness のツール、権限、スキル、ワークフロー、サブエージェント、Cordis プラグインも利用できます。

![Kotoba Studio 0.7.3：日本語のコード画面と Python ソースのタブ](assets/screenshots/code-workspace-ja.png)

画像は 0.7.3 の実際のアプリ画面です。会話と音声エージェントには **OpenAI → GPT-6 Astra** を選択しています。プロバイダーの一覧には設定済みの接続先のみを表示し、隣のモデル一覧からその接続先のモデルを選べます。チャットと音声欄の文章は手入力した未送信の例であり、文字起こし結果や AI の生成結果ではありません。

### 英語と日本語のチームで引き継ぐ

**··· → チームの引き継ぎ** で、原文・用語・両言語の要約・決定事項・担当者をまとめられます。会議からコピーし、選択した音声エージェントへの依頼を確認して送信した後、JSON の応答を未確認の下書きとして取り込みます。共有はコピーまたは Markdown の書き出しで行います。データはこの端末に保存され、自動翻訳や遠隔同期はありません。

### Windows で始める

現在のデスクトップ版は **0.8.0**、Windows x64 向けの未署名の開発者プレビューです。[Windows パッケージ作成ガイド](python/voice/WINDOWS.md)に従って `Kotoba-Studio-0.8.0-Setup.exe` を作成できます。インストーラーには、デスクトップアプリ、エージェントの実行環境、音声キャプチャー、CPU 推論エンジンが含まれます。モデルの重みは別途ダウンロードするか、手元のファイルを登録してください。

1. **作業フォルダーを選ぶ。** エージェントが作業するフォルダーを指定します。
2. **モデルを接続する。** **··· → 接続** で OpenAI、Anthropic Claude、Kimi、DeepSeek、またはカスタムの接続先を設定します。ローカルで使う場合は **ローカル AI** で GGUF モデルを登録してエンジンを起動し、会話の入力欄で **Kotoba Local** を選びます。Ollama と LM Studio にも接続できます。
3. **会話または音声入力を始める。** チャットごとにモデルを選びます。ローカル録音の前に音声モデルを準備し、文字起こしを確認してから送信してください。

| ショートカット | 操作 |
| --- | --- |
| `Ctrl+T` / `Ctrl+Tab` | エージェントを追加 / チャットを切り替え |
| `Ctrl+K` | コマンドを検索 |
| `Ctrl+Shift+V` | 音声スタジオを表示・非表示 |
| `Ctrl+Shift+E` / `Ctrl+J` | コード / ターミナルを表示・非表示 |
| `Ctrl+F` / `Ctrl+W` | コード内を検索 / ソースのタブを閉じる |
| `Ctrl+Shift+Space` | 録音を開始・停止 |

ウィンドウを閉じると、Kotoba はシステムトレイで動作を続けます。トレイのメニューから再表示・終了できます。更新をインストールする前に終了してください。アプリの再起動後は、ローカルエンジンを起動し直す必要があります。右上の **English / 日本語** は表示言語の切り替えです。会話本文やコードは翻訳しません。

### ローカル処理と、利用上の制約

音声処理はローカルモードで起動します。クラウドでの文字起こしは明示的に選ぶ設定で、クラウドのプロバイダーには送信した内容が渡ります。GGUF モデルは同梱の llama.cpp CPU エンジンで実行し、Ollama と LM Studio はループバック接続に対応します。ローカル処理の失敗時に、クラウドへ自動で切り替えることはありません。エージェントのツールは権限に応じてネットワークを利用できます。

ノート、文字起こし、保存したフレーズ、会話履歴はローカルに暗号化せず保存されます。精度は音声、ハードウェア、タスクによって変わります。日本語の CER・英語の WER は、人が確認した参照文で評価してください。自動字幕を正解として扱わないでください。話者分離、ストリーミング中の割り込み、アプリが管理する GPU 推論、GGUF の自動ダウンロードは未実装です。日本語訳がない拡張機能は英語で表示されます。[デスクトップガイド](python/voice/README.md)と[アクセス権限の説明](SAFETY.zh.md)も参照してください。

### 開発・拡張・貢献

[デスクトップ開発](python/voice/README.md#development)、[アーキテクチャ](docs/architecture.zh.md)、[貢献ガイド](CONTRIBUTING.zh.md)から始められます。Kotoba は [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) の実際の実行環境とプラグイン機構を基盤とし、[OpenWhispr](https://github.com/OpenWhispr/openwhispr) の音声キャプチャー・音声入力の実装を取り入れています。ローカル推論には [llama.cpp](https://github.com/ggml-org/llama.cpp) を使用しています。詳しくは[統合内容の調査](python/voice/INSPECTION.md)をご覧ください。

[MIT ライセンス](LICENSE) · [第三者ライセンス表記](THIRD_PARTY_NOTICES.md) · [同梱ライセンス](python/voice/THIRD_PARTY_LICENSES)
