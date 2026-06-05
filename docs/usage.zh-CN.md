# KoKonna CLI 中文使用指南

本文档说明如何安装、配置和使用 `kokonna` 命令行工具来管理 KoKonna 墨水屏相框。

## 安装

推荐使用 `pipx` 安装，便于隔离依赖和后续升级：

```bash
pipx install .
kokonna --version
kokonna --help
```

也可以安装到当前用户环境：

```bash
pip install --user .
```

开发调试时可使用可编辑安装：

```bash
pip install -e .[test]
pytest
```

## 配置 API Key

相框设置页面会显示设备 API Key。首次使用前保存一次：

```bash
kokonna config set-key <API_KEY>
```

配置文件默认写入：

```text
~/.kokonna/config.json
```

如果只想临时执行一次命令，也可以使用环境变量：

```bash
export KOKONNA_API_KEY=***
kokonna device info --human
```

如需查看当前配置状态：

```bash
kokonna config show
```

该命令只会显示遮罩后的 key，不会打印完整 API Key。

## 常用命令

查看设备状态：

```bash
kokonna device info
kokonna device info --human
kokonna device info --json
```

上传图片到相框：

```bash
kokonna image upload ./photo.jpg
kokonna image upload ./photo.jpg --name sunset.jpg
```

列出相框图库：

```bash
kokonna image list
kokonna image list --human
```

切换当前显示图片：

```bash
kokonna image display 123
kokonna image display-by-name sunset.jpg
```

下载相框中的图片：

```bash
kokonna image download 123
kokonna image download 123 -o shot.jpg
```

删除图片：

```bash
kokonna image delete 123
```

## Skill 安装

推荐使用 `npx skills add` 安装：

```bash
npx skills add nixihz/kokonna-skill --skill kokonna --copy -y
```

该命令会把 `kokonna` skill 安装到当前项目的 agent skills 目录。安装后可验证：

```bash
npx skills list --json
```

如果希望安装到用户级全局 skills 目录：

```bash
npx skills add nixihz/kokonna-skill --skill kokonna --copy -g -y
```

如果正在本地开发本仓库，也可以从当前目录安装：

```bash
npx skills add . --skill kokonna --copy -y
```

## 安全说明

- 仓库中不应提交真实 API Key、token、密码或私钥。
- 示例中使用的 `***`、`<API_KEY>`、`test-key-123` 等都是占位符或测试假值。
- `kokonna config show` 会遮罩 API Key，适合用于排查配置状态。
- 下载图片接口的 API Key 由 KoKonna OpenAPI 设计放在 URL 路径中，CLI 会自动处理，使用者无需手动拼接下载 URL。

## 常见问题

如果提示 API Key 未配置：

```text
error: API key not configured...
```

请执行：

```bash
kokonna config set-key <API_KEY>
```

如果提示找不到设备或 robot：

```text
error: can not find robot ...
```

通常表示 API Key 错误、相框重置过，或当前 key 不属于该设备。

如果提示请求过于频繁：

```text
error: Too many requests, please try again later.
```

请等待约一分钟后再重试。KoKonna OpenAPI 对单个设备 key 有请求频率限制。
