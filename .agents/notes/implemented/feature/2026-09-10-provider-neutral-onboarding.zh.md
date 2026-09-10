# Agent Note: 提供方中立的首次运行设置

Status: implemented

[English](2026-09-10-provider-neutral-onboarding.md) | 中文

## Problem

首次运行凭据弹窗引导所有新用户使用 DeepSeek，但已安装的多提供方适配器支持其他原生 API。仅保存凭据不会激活尚未启用的提供方路由。

## Decision

引导选择器使用共享的可配置提供方目录，优先展示 OpenAI、Anthropic Claude、通过 Moonshot AI 接入的 Kimi 及 DeepSeek。已安装的适配器提供协议、端点和模型目录。OpenAI 使用 Responses，Anthropic 使用 Messages，Moonshot 使用 Chat Completions。自定义网关仍可从模型页面配置。Claude API 密钥与 Claude Code 订阅或 CLI 登录不同。

凭据编辑器先写入尚未启用的目录路由的凭据引用，再保存密钥。成功的设置写入在刷新就绪状态前进入共享镜像。凭据写入失败后编辑器允许重试；不会仅因密钥已保存就报告提供方可用。切换提供方会重新挂载编辑器并清空未保存的密钥。保存期间禁止切换。已有可用路由时跳过设置，稍后配置允许继续设置本地模型。

## Alternatives considered

**另建提供方实现。** 复用已安装的原生 SDK 适配器可以保留流式传输、工具回放、模型能力和现有凭据架构，无需维护重复的传输实现。

**只修改介绍文字。** 选择提供方必须激活对应路由，否则模型选择器仍无法提供其模型。

## Consequences

英文、日文和中文设置文案描述相同的工作流程。测试覆盖凭据隔离、无 DeepSeek 时的路由激活、切换、待完成写入，以及带日文参数和工具结果回放的原生协议工具流。认证测试需要对应提供方的密钥；本地测试服务器的检查不能证明账户访问权限或真实模型质量。
