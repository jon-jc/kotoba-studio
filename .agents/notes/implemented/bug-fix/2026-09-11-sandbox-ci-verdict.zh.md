# Agent Note: 沙箱 CI 结果

Status: implemented

[English](2026-09-11-sandbox-ci-verdict.md) | 中文

## Problem

macOS 一致性测试拒绝引导界面提供商选择器的 1px 中性边框。沙箱 shell 步骤关闭自动退出后，可能用成功的摘要匹配覆盖测试命令的失败状态。

## Decision

选择器使用主题规定的 0.5px 中性边框。两个沙箱步骤均在检查摘要前明确返回失败命令的退出状态。成功命令仍须报告全部预期文件通过且无跳过。语音拉取请求任务也运行主题和 shell 结果回归测试。[仅在 master 运行的沙箱矩阵](../process/2026-07-21-serial-cross-platform-ci-reference.zh.md)保持启用。

文档图片越界测试夹具在 Windows 上通过目录联接指向外部目录，在 POSIX 上使用目录符号链接。这保留了真实路径越界拒绝测试，同时不要求 Windows 文件符号链接权限。

## Alternatives considered

**删除 macOS 检查**会隐藏可复现的样式缺陷并失去平台覆盖。**仅信任摘要**可能接受报告文件通过但在清理期间失败的命令。

## Consequences

shell 回归测试以受控命令结果执行两个工作流脚本，包括非零退出状态配合通过摘要，以及零退出状态配合跳过文件。Linux/macOS 使用 Bash，Windows 安装 Git Bash 时使用它；托管 Linux 提供必需的拉取请求证据。真实隔离继续由合并后保持不变的内核矩阵验证。
