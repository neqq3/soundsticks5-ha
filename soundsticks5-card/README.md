# SoundSticks 5 自定义卡片

基于 Kimi 视觉稿迭代的 Home Assistant Lovelace 卡片。随 SoundSticks 5 集成打包，保留声音、灯光、EQ、设备设置及预设控制。

## 安装

新用户建议先阅读[完整入门指南](../docs/getting-started.md)，包含 HACS 安装、卡片资源注册、默认播放方式和故障排查。

1. 在 HA 安装并配置 `neqq3/soundsticks5-ha` 集成。
2. 重启 HA 并配置集成后，卡片资源自动注册；刷新浏览器。
3. 在仪表板中添加 SoundSticks 5 自定义卡片：

```yaml
type: custom:soundsticks5-lovelace-card
```

YAML 管理资源以及旧版迁移步骤见[入门指南](../docs/getting-started.md)。发布用 JS 和图片的唯一来源为 `custom_components/soundsticks5/frontend/`；本目录保留预览与测试工具。

卡片自动发现 SoundSticks 实体。图形编辑器支持自动、指定媒体实体、仅 BLE 三种播放方式，详见 [PLAYBACK.md](PLAYBACK.md)。可通过 `image` 配置覆盖产品图片路径。

## 预设

输入名称后点“保存当前”；在下拉框选择预设后点“应用”，可重复应用同一预设。保存、应用、删除由 SoundSticks 集成执行。此卡片不改变集成现有的覆盖、存储和执行规则。

## 本地预览与检查

在本目录执行：

```sh
node serve.cjs
node tools/card_smoke.js
node tools/playback_test.cjs
node tools/preset_test.cjs
```

预览地址为 `http://127.0.0.1:8769/`，支持 `?width=380` 和 `?width=640`。预览仅使用模拟数据。

## 素材及来源

主线由用户指定的 Kimi 稿迁入后持续修改。产品图为此前从 HK One App 提取的原始透明 PNG（510 × 360）；六种灯效卡片以 CSS 绘制。原始素材出处记录见 [assets/SOURCES.md](assets/SOURCES.md)。

本机部署脚本、凭据、部署记录和迁移清单不纳入源码提交。旧视觉方案留在本机作为备选，不与当前主线混合。
