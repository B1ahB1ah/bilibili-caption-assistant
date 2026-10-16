# B站字幕助手 · macOS

在一个 macOS 窗口里浏览 B站、识别当前视频、提取已有字幕，再把完整字幕和总结提示词一键复制给智能体。

## 功能

- 左侧菜单切换“浏览 B站”和“字幕与提示词”，保留网页浏览状态。
- 应用内登录 B站；打开视频后点击一键识别，支持 BV 号、视频链接、b23.tv 短链接及分P。
- 优先提取中文 AI 字幕，也可使用现有其他字幕轨道；导出 TXT/SRT，导入已有字幕 JSON。
- 提供重点摘要、深入解读、学习笔记三种提示词，附完整字幕和时间位置。
- 显示首尾覆盖与长空档提示。

应用本身不调用大模型、不自动生成总结，不需要模型 API Key。它提取的是 B站已有字幕；没有字幕时会报出具体状态，不下载音视频或自动转写，也不能保证所有视频都可提取。

## 构建与运行

要求 macOS 13 或更新版本、Apple Command Line Tools（Swift 编译器）、[uv](https://docs.astral.sh/uv/)。

```sh
xcode-select --install
# 已使用 Homebrew 时可安装 uv：
brew install uv
zsh build.sh
open "dist/B站字幕助手.app"
```

构建脚本使用本机架构：Apple Silicon 生成 arm64，Intel Mac 生成 x86_64。当前实际验证环境为 Apple Silicon；Intel 尚未实机验证。首次提取时 uv 会准备 Python 3.12 和依赖，需要网络。

可将 `dist/B站字幕助手.app` 拖入“应用程序”。当前构建使用临时本机签名，未取得 Apple Developer ID 公证；源码自行构建可避免下载预编译应用时的来源不明提示。

## 使用

1. 启动应用，在“浏览 B站”中正常登录自己的账号。
2. 搜索或打开视频，点击一键识别。
3. 在“字幕与提示词”查看字幕、覆盖提示，选择提示词模式并复制给智能体。
4. 需要时导出字幕；请在给第三方智能体发送字幕前自行确认内容。

应用内登录为默认方式。可选读取 Safari、Chrome、Edge、Firefox 或 Brave 的 B站会话；浏览器文件权限或 macOS 钥匙串授权可能影响读取，应用内登录不依赖这些文件。

## 隐私与限制

- WebKit 默认网站数据存储会保留本机的 B站网站登录状态，方便下次使用；仓库不含任何账号、Cookie 或会话数据。
- 提取时将所选 B站会话交给本机 Python 子进程，与 B站接口通信；不把会话发往大模型或项目作者。
- 浏览 B站时正常加载 B站网页及其资源。应用没有自建后端、遥测服务或云端账号同步。
- 自动字幕可能有错字、同音词和说话人混淆；覆盖检查不能证明逐字正确。
- B站接口、登录要求和风控可能变化；请只处理自己有权访问的内容，遵守平台规则和内容权利人的要求。

## 项目结构

```text
App.swift     SwiftUI / AppKit / WebKit 单窗口应用
Icon.swift    生成应用图标
extract.py    登录会话交接、字幕提取与格式转换
build.sh      构建、生成图标、临时签名
vendor/       固定版本的上游字幕模块与原许可证
```

## 来源与许可证

本项目采用 [MIT License](LICENSE)。`vendor/bilibili_ai_subtitle` 源自 [ccBilly-aipm/bilibili-ai-subtitle](https://github.com/ccBilly-aipm/bilibili-ai-subtitle)，固定提交 `2898964d19d7923908b4dc1f9c2623d50f79ce9f`；其 MIT 许可证完整保留于 [vendor/LICENSE](vendor/LICENSE)。详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

本仓库只包含通用字幕助手 App。个人晨读自动化、备忘录、音频、视频字幕和私人网站配置不属于本开源项目。
