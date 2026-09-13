import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Shield, Eye, MessageSquare, FolderPen, Check } from 'lucide-react'
import type { GlobalSettings } from '../../../../shared/global-settings-types'
import { ACCESS_AGENTS, applyAccessLevel, currentAccessLevel, type AccessAgent, type AccessLevel } from '../../../../shared/kotoba-agent-access'

export function KotobaAgentAccess({ settings, updateSettings }: { settings: GlobalSettings; updateSettings: (updates: Partial<GlobalSettings>) => void | Promise<void> }): React.JSX.Element {
  const { i18n } = useTranslation()
  const ja = i18n.language.startsWith('ja')
  const text = (en: string, japanese: string) => ja ? japanese : en
  const initial = ACCESS_AGENTS.includes(settings.defaultTuiAgent as AccessAgent) ? settings.defaultTuiAgent as AccessAgent : 'codex'
  const [agent, setAgent] = useState<AccessAgent | 'pi'>(initial)
  const [chosen, setChosen] = useState<AccessLevel | null>(null)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState('')
  const current = agent === 'pi' ? 'custom' : currentAccessLevel(settings, agent)
  const selected = chosen ?? (current === 'custom' ? null : current)
  const choices = [
    { id: 'plan', icon: Eye, title: text('Plan', '計画'), detail: text('Explore first. Keep edits restricted while reviewing the approach.', 'まず調査と計画。方針を確認する間は編集を制限します。') },
    { id: 'ask', icon: MessageSquare, title: text('Ask for approval', '承認を求める'), detail: text('Use the agent’s approval rules before making changes.', '変更前にエージェントの承認ルールを適用します。') },
    { id: 'workspace', icon: FolderPen, title: text('Workspace editing', 'ワークスペースの編集'), detail: text('Allow project edits while retaining command and escalation checks.', 'プロジェクトの編集を許可し、コマンドと権限拡張の確認を維持します。') }
  ] as const
  async function save() {
    if (agent === 'pi' || !selected || saving) return
    setSaving(true)
    setStatus('')
    try {
      const update = applyAccessLevel(settings, agent, selected, navigator.platform.startsWith('Win') ? 'powershell' : 'posix')
      await updateSettings(update)
      setChosen(null)
      setStatus(text('Saved for new sessions. Existing sessions retain their own permissions.', '新しいセッションに適用しました。既存のセッションの権限は変わりません。'))
    } catch {
      setStatus(text('Could not save. Check custom launch arguments and inline configuration, then try again.', '保存できませんでした。起動引数とインライン設定を確認して再試行してください。'))
    } finally { setSaving(false) }
  }
  return (
    <section aria-labelledby="kotoba-access-title" className="rounded-2xl border border-border/70 bg-card/40 p-5 space-y-5">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-primary/10 p-2.5 text-primary"><Shield className="size-5" /></div>
          <div><h2 id="kotoba-access-title" className="text-base font-semibold">{text('Agent access', 'エージェントのアクセス')}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{text('Choose what each agent may do when it starts.', 'エージェント起動時に許可する操作を選択します。')}</p></div>
        </div>
        <select aria-label={text('Agent for access settings', 'アクセス設定のエージェント')} value={agent} disabled={saving}
          onChange={event => { setAgent(event.target.value as AccessAgent | 'pi'); setChosen(null); setStatus('') }}
          className="h-9 min-w-40 rounded-lg border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <option value="codex">Codex</option><option value="claude">Claude Code</option><option value="opencode">OpenCode</option><option value="pi">Pi</option>
        </select>
      </div>
      {agent === 'pi' ? <p className="text-sm text-muted-foreground">{text('Pi does not provide built-in approval levels. Configure its extensions or execution environment directly. Kotoba does not claim to sandbox Pi or other unsupported agents.', 'Pi には組み込みの承認レベルがありません。拡張機能または実行環境で設定してください。Kotoba は Pi や未対応エージェントのサンドボックスを提供しません。')}</p> : <>
        <div role="radiogroup" aria-label={text('Access level', 'アクセスレベル')} className="grid gap-3 lg:grid-cols-3">
          {choices.map(choice => <label key={choice.id} className={`relative cursor-pointer rounded-xl border p-4 transition-colors motion-reduce:transition-none ${selected === choice.id ? 'border-primary/60 bg-primary/8' : 'border-border hover:bg-muted/50'}`}>
            <input type="radio" name="kotoba-agent-access" value={choice.id} checked={selected === choice.id} disabled={saving} onChange={() => { setChosen(choice.id); setStatus('') }} className="sr-only peer" />
            <span className="absolute inset-0 rounded-xl peer-focus-visible:ring-2 peer-focus-visible:ring-ring pointer-events-none" />
            <div className="flex items-center justify-between"><choice.icon className="size-4 text-muted-foreground" />{selected === choice.id && <Check className="size-4 text-primary" />}</div>
            <div className="mt-3 text-sm font-semibold">{choice.title}</div><p className="mt-1 text-xs leading-relaxed text-muted-foreground">{choice.detail}</p>
          </label>)}
        </div>
        <div className="rounded-lg bg-muted/40 p-3 text-xs leading-relaxed text-muted-foreground">
          {agent === 'codex' ? text('Codex: Plan uses a read-only sandbox with no escalation. Approval mode allows individually approved escalation. Workspace editing uses the workspace-write sandbox. Host restrictions still apply.', 'Codex：計画は読み取り専用で権限拡張を行いません。承認モードは個別承認で拡張できます。編集モードは workspace-write サンドボックスを使用します。実行環境の制限にも従います。') : agent === 'claude' ? text('Claude Code: maps to Plan, Default, and Accept Edits. These are tool approval modes, not an operating-system sandbox; existing allow/deny rules still apply.', 'Claude Code：Plan・Default・Accept Edits に対応します。OS のサンドボックスではなくツールの承認モードです。既存の許可・拒否ルールにも従います。') : text('OpenCode: applies permission rules to its built-in Plan and Build agents. Planning blocks edits and shell commands; editing still asks for shell and external-directory access. Custom agents and administrator policies may differ.', 'OpenCode：組み込みの Plan・Build に権限ルールを適用します。計画では編集とシェルを拒否し、編集モードでもシェルと外部フォルダーのアクセスには承認を求めます。独自エージェントや管理者ポリシーでは異なる場合があります。')}
        </div>
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <p className="text-xs text-muted-foreground">{current === 'custom' ? text('Current: custom / agent defaults', '現在：カスタム・エージェントの既定値') : text('Current: ', '現在：') + choices.find(choice => choice.id === current)?.title}</p>
          <button type="button" disabled={!selected || saving || selected === current} onClick={() => void save()} className="h-9 rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none">{saving ? text('Saving…', '保存中…') : text('Apply access level', 'アクセスレベルを適用')}</button>
        </div>
      </>}
      <p className="text-xs text-muted-foreground">{text('Per-agent defaults for new chats and terminal launches. Running sessions keep their existing permissions. Direct terminal commands and plugins are not governed by these controls.', 'エージェントごとの新しいチャット・ターミナル起動の既定値です。実行中のセッションの権限は変わりません。手入力のターミナルコマンドやプラグインは対象外です。')}</p>
      <p role="status" className="text-sm min-h-5">{status}</p>
    </section>
  )
}
