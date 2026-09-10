---
description: "此分支的 Kotoba Studio 侧栏与对话品牌呈现。"
kind: "package-reference"
---

# @deepseek-ai/dsh-client-ui-brand-official

[English](README.md) | 中文

## 概述

此分支在侧栏与空白对话首屏使用 Kotoba Studio 图标和跨语言不变的产品名称。为保持插件兼容性，保留上游包标识。所有客户端构建配置均使用这些填充和日语语言包。提供方名称、模型 ID、许可证和来源署名保持原样。

## 目录

- [使用本包](#use-this-package)
- [理解实现](#understand-the-implementation)
- [进一步探索](#further-exploration)
- [模型体验](#model-experience)
- [已知限制与延期工作](#known-limitations-and-deferred-work)
- [开发备注](#dev-note)

<a id="use-this-package"></a>
## 使用本包

在浏览器插件列表中挂载现有包。三个填充分别占据 `sidebar.brand.mark`、`sidebar.brand.name` 和 `conversation.hero.brand.mark`。如需其他品牌，请用占据相同槽位的插件替换本包。浏览器标题由 `DSH_CLIENT_TITLE` 单独配置；此分支的官方标题和本地化回退名称均为 Kotoba Studio。

日语语言包覆盖对话、输入框、工作区、模型选择、模型设置和通用控件。其他扩展词条回退到英语。原生语言选择器无需刷新即可切换浏览器语言；消息、草稿、代码和模型回复保持原文。

<a id="understand-the-implementation"></a>
## 理解实现

主题服务管理用户的浅色/深色偏好。本插件注册成对的中性炭灰与柔和玉绿色令牌、日语语言包以及桌面语言监听器；各项注册随插件一起释放。

两个侧栏声明都存在后，图标和名称一起注册。对话声明存在后，首屏图标独立注册。声明或插件 fiber 撤销时，各组填充随之撤销。两种激活顺序都受支持，侧栏可用性不依赖对话加载。[浏览器入口](src/client/index.ts) 注册[图形](src/client/Brand.tsx)；node 入口没有副作用。

<a id="further-exploration"></a>
## 进一步探索

- [侧栏](../ui-sidebar/README.zh.md) 声明侧栏槽位。
- [对话](../ui-conversation/README.zh.md) 声明首屏槽位。
- [桌面品牌](../../../python/voice/README.md) 说明原生程序和安装器图标。

<a id="dev-note"></a>
## 开发备注

不发布 invariant companion：本包不保留可变状态，所有填充均通过所属槽位 effect 撤销。

<a id="model-experience"></a>
## 模型体验

无；本包仅提供浏览器呈现，不向模型请求添加内容。

#### KV Cache 影响

无；本包不组装或发送提供方请求。

<a id="known-limitations-and-deferred-work"></a>
## 已知限制与延期工作

- 仅提供一组填充。浏览器标题和原生可执行文件图标由其他模块管理。显式省略本插件的配置仍可使用上游回退图形。
