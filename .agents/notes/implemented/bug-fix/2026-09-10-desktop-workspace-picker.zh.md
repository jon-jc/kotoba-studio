# Agent Note: 嵌入式桌面工作区选择

Status: implemented

[English](2026-09-10-desktop-workspace-picker.md) | 中文

## Problem

独立 Harness 进程启动的原生文件夹选择器可能出现在 Qt 桌面窗口后面，使工作区选择看起来没有响应。折叠侧栏的新建会话图标也靠在按钮左侧，未与其他图标居中对齐。

## Decision

[桌面启动](../../../../python/voice/src/kotoba/workspace.py) 提供[配置覆盖层](../../../../python/voice/assets/desktop-workspace.patch.yml)，禁用自动目录选择器，并只组合一个浏览后端及其匹配的客户端界面。两个工作区入口都使用已有文件夹浏览器，日语文本由品牌语言字典提供。桌面语言桥接会在延迟到达的 Host 设置快照切换语言时重新应用原生界面的明确选择，并在卸载时释放订阅。新建会话控件的图标在与相邻侧栏控件相同的 36 像素按钮中居中。

## Alternatives considered

独立 Windows 选择器的前台激活依赖操作系统焦点策略，且仍是没有桌面父窗口的对话框。仅供桌面的文件夹操作会绕过工作区注册流程。在自动选择器旁组合浏览界面也不可行，因为两者会占用同一个单注册目录交互插槽。

## Consequences

桌面文件夹选择保持在聊天窗口内，并使用已有 Harness 工作区 API。独立启动的浏览器和无界面配置保留各自设置。[Windows 验证器](../../../../python/voice/verify_windows.py) 针对打包可执行文件检查展开与折叠入口、实测图标中心、日语路径注册和日语选择器文本。选择器单元测试继续覆盖列表、取消和错误。[Windows 指南](../../../../python/voice/WINDOWS.md#workspace-selection) 说明用户操作。
