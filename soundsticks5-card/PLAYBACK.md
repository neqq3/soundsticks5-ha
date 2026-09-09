# 播放源配置

在 HA 仪表板中编辑这张卡片，图形编辑器可选择播放控制方式和播放源实体。配置保存在仪表板中，所有浏览器共用。

- `entity`（指定媒体实体）：歌名、歌手、状态、上一首、播放、暂停、下一首全部来自指定实体。离线时禁用按钮，不切换目标。
- `auto`（默认）：所选播放源为 playing / paused 时使用它，否则回到 BLE。未指定播放源时，只接受与 BLE 媒体实体具有同一个 HA device_id 的唯一其他媒体实体；不会按名称猜测，多候选时回到 BLE。这不是音箱 AUX / 蓝牙输入检测。
- `ble`：全部播放信息及播放控制只用 SoundSticks BLE 媒体实体。

音箱音量始终使用 BLE 媒体实体。灯光、EQ 和设备设置继续使用 SoundSticks 集成。

指定播放源的配置示例（替换为自己的实体 ID）：

```yaml
type: custom:soundsticks5-lovelace-card
playback_mode: entity
playback_entity: media_player.your_speaker
```

可选 `media_player` 字段用于明确指定 **BLE** 媒体实体，不是 MA 播放源。原有其他实体覆盖配置继续有效。

指定模式不混用两个实体的歌名或歌手。缺少元数据时显示占位；播放器未声明支持的操作会禁用。

验证：`node tools/playback_test.cjs` 覆盖元数据、MA 暂停/恢复/切歌服务路由、BLE 音量、离线/能力限制、自动回退及多候选处理。已在 HAOS 上完成一次暂停和恢复播放测试。
