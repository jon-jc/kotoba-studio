# Subscription agents in Kotoba Studio

The Windows 0.11.2 build opens **Agents** as the main workspace. Kotoba hosts the full Orca desktop interface inside its own window, alongside the existing API Harness, English/Japanese voice tools, code viewer and messaging. There is one outer window and one system tray entry.

## Start a task

1. Open **Agent accounts** and connect the coding agent you use. Codex, Claude Code, OpenCode and Pi retain their own CLI installation, authentication, plan limits and supported providers. Follow the selected agent's setup instructions; Kotoba does not supply a subscription.
2. Add a Git project. Create a workspace/worktree for each task to isolate file edits. A worktree is a separate checkout, not a security sandbox.
3. Choose an agent for that task and enter its instruction. Other tasks can continue while you select a different row in the left sidebar. Splitting terminals is optional.
4. Review changes and terminal output in that task. Commit, branch and pull-request actions remain explicit upstream controls.
5. Use **Voice** to review English or Japanese speech. **Add to chat** inserts into an empty native chat composer without sending. If no compatible composer is available or it already contains text, the transcript stays in Voice. Use paste-at-cursor dictation for a terminal-based agent.

The selected local worktree becomes the root for Kotoba's Code viewer and voice-agent workspace. A running voice job retains its original workspace until completion. Remote worktrees never become local filesystem paths. **API chat** retains independent Harness sessions and workspace selection; it does not pretend to share a subscription-agent transcript. The Kotoba icon returns to Agents and expands its sidebar. Closing Code also returns to Agents.

## What comes from Orca

| Workflow | Implementation and setup |
| --- | --- |
| Agent accounts and sessions | Full native preload/main services, including account setup and switching; credentials and subscriptions remain provider-specific |
| Concurrent tasks | Upstream project/worktree/task state, terminal lifecycle, retained output and agent status |
| Changes and review | Upstream file editing, diffs, annotations, Git actions and pull-request controls |
| Automation and orchestration | Upstream task automation, worktree and agent-launch controls; availability follows agent and repository configuration |
| Browser and preview | Upstream browser/preview implementation and runtime resources; tools may need their own browser downloads |
| Plugins and skills | Upstream bundled plugin resources and plugin/skill management, plus the original Harness plugin system in API chat |
| Remote work | Upstream SSH/relay and paired-device implementation; requires explicit remote-host or external-service setup |
| Team communication | Kotoba's reviewed bilingual handoffs and LINE-first messaging, outside agent transcripts until explicitly transferred |

An upstream screen being retained does not establish that every external service has been tested. Provider sign-ins, paid agent turns, GitHub/Linear actions, SSH hosts and external account services need real configured accounts. No test sends a billed model request or publishes a pull request from the test workspace.

## Agent access

Open **Access → Agents** to select Codex, Claude Code or OpenCode and apply **Plan**, **Ask for approval**, or **Workspace editing** to new sessions. The panel explains the native mapping for each agent. Codex uses its sandbox and approval flags; Claude uses its tool approval modes; OpenCode uses permission rules for its built-in Plan and Build agents. Existing sessions retain their permissions. Pi and other unsupported agents use their own controls; this panel does not create an operating-system sandbox for them. Custom launch commands and provider policies can affect behavior.

The old global Yolo switch is removed. Existing exact bypass presets are reset to normal agent defaults; custom arguments remain available for explicit review. Orca Mobile navigation, pairing handlers, push startup and cloud relay startup are disabled in the embedded Kotoba runtime.

## Integration contract

Source: Orca 1.4.197, revision `8641b3af0970b030cebbc263233585cc1ef83a4b`, MIT, copyright Lovecast Inc. The git submodule remains unchanged. `prepare_fleet_source.py` applies exact, revision-checked changes in a disposable checkout; `prepare_fleet_runtime.py` builds and packages the native app with Orca's dependency closure and package checks.

The overlay isolates application data under Kotoba's `agent-workspace` directory, disables telemetry and Orca's local self-updater, removes its duplicate window controls and tray, applies Kotoba artwork, defaults to dark appearance, and preserves normal CLI launch approval defaults. Each CLI remains its own permission boundary. The outer **Access** button opens agent settings in Agents and Harness permissions in API chat; changing Harness access does not sandbox an external CLI.

The host uses a user-restricted Windows named pipe for a fixed set of commands: snapshot, draft, add project and navigation. Both the pipe client and embedded window must belong to the owned runtime process. Replies carry a per-launch nonce. No arbitrary JavaScript command is accepted. API-key environment variables are removed from the child environment; explicit agent sign-in remains available. Runtime output is not saved by the bridge. Closing to tray keeps work running; quitting stops the owned process tree.

The packaged artifact is checked for native terminal process ownership, dependency resolution, daemon boot, CLI resources and bundled plugins. Focused Python tests exercise bundle path confinement, reply admission, disconnected-state recovery, project context and native UI behavior. A hidden Windows smoke opens the real packaged window, adds a disposable Git project, reads its selected worktree and rejects an unavailable chat draft. These checks do not substitute for signed-installer, clean-machine or live-provider qualification.

## 日本語

Windows 版 0.11.2 は **エージェント** を中心に起動します。Orca の完全なデスクトップ実装を Kotoba の同じウィンドウに組み込み、API チャット、日英の音声入力、コード、メッセージ機能を併用できます。

**エージェントのアカウント** で Codex、Claude Code、OpenCode、Pi などの設定を行ってください。各 CLI が対応するログイン、サブスクリプション、認証情報、利用上限に従います。Git プロジェクトを追加し、タスクごとに作業ツリーを作成すると変更を分離できます。作業ツリー自体はセキュリティ上のサンドボックスではありません。

タスクは左の一覧から切り替え、分割表示は任意です。変更差分、レビュー、ターミナル、プラグイン、SSH などは上流の実装を利用します。リモート接続、外部サービス、アカウント機能には個別の設定が必要です。実際の有料モデル呼び出しや外部への公開操作は自動テストでは実施していません。

選択したローカル作業ツリーはコード・音声画面にも反映されます。処理中の音声ジョブは元の作業場所を保持します。音声は確認後、空のネイティブチャット下書きに挿入し、自動送信しません。対応する入力欄がない場合や既存の下書きがある場合、音声画面にテキストを保持します。ターミナル形式ではカーソル位置への貼り付けを利用してください。API チャットは独立した Harness セッションと作業場所を維持します。

各 CLI の権限はそのエージェントが管理します。**アクセス** は現在の画面に対応する設定を開きます。名前付きパイプと埋め込みウィンドウは所有プロセスを検証し、プロファイルは Kotoba 内に分離します。テレメトリーと上流アプリの自動更新は無効です。固定ソースと MIT ライセンスを保持し、インストーラーには実行環境と必要なライセンスを含めます。署名、クリーン環境、実際の提供元との接続検証は別途必要です。

### エージェントのアクセス

**アクセス → エージェント** で Codex・Claude Code・OpenCode の **計画／承認を求める／ワークスペースの編集** を設定できます。新しいセッションに適用され、既存のセッションの権限は変わりません。各エージェントの実装と制限は設定画面に表示します。Pi など未対応のエージェントは独自の権限設定を使用します。以前の Yolo スイッチと Orca Mobile は削除しました。

## Workspace layout

The left rail keeps Agents, API chat, Voice, Code and Terminal in a fixed order. Messages and Handoffs sit below a divider; Accounts, Access and Settings stay at the bottom. The header contains the current surface, project picker, command search and language. The embedded workspace no longer repeats the same actions in a second toolbar. Settings → Connections separates subscription accounts, API keys and local models. Voice can close without discarding its draft. Ctrl+K opens the command center.

### ワークスペースのレイアウト

左側にエージェント・API 会話・音声・コード・ターミナルを固定配置し、その下にメッセージと引き継ぎをまとめました。アカウント・アクセス・設定は最下部にあります。ヘッダーには現在の画面、プロジェクト、コマンド検索、表示言語だけを表示します。「設定 → 接続」でサブスクリプション、API キー、ローカルモデルを管理できます。音声パネルを閉じても下書きは保持されます。
