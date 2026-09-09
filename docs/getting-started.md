# 第一次使用：集成与 Lovelace 卡片

本指南针对普通版 Harman Kardon SoundSticks 5。集成负责控制音箱；Lovelace 卡片负责仪表板界面。卡片随集成一起安装和更新。

## 1. 准备 Home Assistant 和音箱

- Home Assistant 最低版本：2025.12.2。
- HA 需要能建立 GATT 连接的本地蓝牙适配器或蓝牙代理；只转发广播的代理不够。
- 让音箱保持唤醒并处于蓝牙覆盖范围内。
- 此集成不传输音频。手机、电脑或其他音频方案负责向音箱播放音乐，Music Assistant 不是安装此集成的必需条件。

## 2. 安装 BLE 集成

在 HACS 的自定义仓库中添加：

```text
https://github.com/neqq3/soundsticks5-ha
```

类别选择 **Integration / 集成**，下载安装后重启 HA。在“设置 → 设备与服务”接受发现的 SoundSticks 5；也可以点击“添加集成”，搜索 SoundSticks 5。

不使用 HACS 时，将仓库的 `custom_components/soundsticks5` 目录复制为 `/config/custom_components/soundsticks5`，再重启并添加集成。

添加成功后，先在设备页确认能看到灯光、媒体、EQ 等实体。可执行“刷新全部状态”，检查是否读到音量、主题等值。

## 3. 安装自定义卡片

安装并配置集成后，卡片 JS 和图片已经包含在集成目录内，无需复制到 `www`。通常使用的界面管理资源模式下，集成会自动注册卡片，并在升级后更新资源版本。

刷新浏览器。进入要放置卡片的仪表板，点击编辑、添加卡片，选择“自定义：SoundSticks 5 (HK design)”。也可以使用手动卡片，填入：

```yaml
type: custom:soundsticks5-lovelace-card
```

设备详情页不会因为安装卡片而被替换，也不会自动创建专用仪表板。

如果希望打开 HA 就看到这张卡片，可以创建一个自己的仪表板并添加卡片，再在个人资料的仪表板选项中设为个人默认页；管理员也可以在“设置 → 仪表盘”中设置默认仪表板。参见 [HA 官方仪表板说明](https://www.home-assistant.io/dashboards/dashboards/#setting-a-default-dashboard)。

### 从旧版手动安装迁移

旧资源 `/local/soundsticks5-lovelace.js`（包括版本查询参数）会自动迁移到内置地址，并合并该卡片的重复资源；已有卡片配置保持有效。确认新卡片正常后，可自行删除旧的 `www/soundsticks5-lovelace.js`。旧图片若仍被自定义 `image` 配置引用，应保留。

### 使用 YAML 管理资源

集成不会改写你的 YAML 文件。在现有 `lovelace.resources` 列表中添加以下条目；若有旧版资源，替换它：

```yaml
lovelace:
  resources:
    - url: /soundsticks5/frontend/soundsticks5-lovelace.js
      type: module
```

重新加载资源并刷新浏览器。这个无版本地址不设置长期 HTTP 缓存。若自动注册失败，也可以在界面的资源页手动添加同一地址，类型为 JavaScript 模块。

## 4. 选择播放方式

只有一台音箱、希望先控制音量和灯光时，以上最简配置即可。默认会发现 SoundSticks 集成实体，播放方式为 `auto`。

### 使用 BLE 回传信息和播放控制

在卡片图形编辑器选择“仅 BLE”，或使用：

```yaml
type: custom:soundsticks5-lovelace-card
playback_mode: ble
```

歌曲信息取决于音箱实际回传。正在通过蓝牙播放也不保证 HA 一定收到歌名、歌手；没有时显示“暂无曲目信息”。

### 使用已有媒体播放器提供歌曲和播放控制

如果 MA 或其他集成中的对应播放器已经正确显示歌曲，在卡片编辑器选择“指定媒体实体”，再选中那台实际播放源：

```yaml
type: custom:soundsticks5-lovelace-card
playback_mode: entity
playback_entity: media_player.your_speaker
```

将示例 ID 换成自己的实体。歌名、歌手、状态和上一首／播放／暂停／下一首都使用它；**音箱音量、灯光、EQ 仍通过 SoundSticks 集成控制**。所选播放器不可用时禁用播放按钮，不改控其他设备。

### 自动模式

```yaml
type: custom:soundsticks5-lovelace-card
playback_mode: auto
playback_entity: media_player.your_speaker
```

所选播放源正在播放或暂停时使用它，否则回到 BLE。未指定播放源时，只接受同一个 HA 设备下唯一的其他媒体播放器；不同集成创建的设备可能无法自动关联，所以 MA 用户通常需要手动选择一次。

自动模式不识别音箱当前 AUX／蓝牙输入，也不会通过相似名称猜测播放源。完整规则见 [播放源配置](../soundsticks5-card/PLAYBACK.md)。当前主要验证的是单台音箱，不建议把多台音箱的自动识别当作已完整支持。

## 5. 保存和应用预设

1. 调好音量、灯效、EQ 等参数。
2. 在“场景预设”输入名称，点击“保存当前”。同名会覆盖。
3. 以后在下拉框选择预设，点击“应用”。只选择名称不会立即修改音箱。

预设保存的是音箱设置，不是歌曲、MA 队列或卡片布局。可以从自动化或开发者工具的“动作”调用：

```yaml
action: soundsticks5.save_preset
data:
  name: 夜间听歌
```

应用时将动作改为 `soundsticks5.apply_preset`；删除时改为 `soundsticks5.delete_preset`。这些动作目前操作第一个已加载的 SoundSticks 集成实例。应用会依次写入参数；中途失败可能只完成一部分。

## 6. 更新与常见问题

| 现象 | 检查方法 |
|---|---|
| 自定义元素不存在 | 确认集成已加载，刷新浏览器；检查资源列表或日志，必要时按上面的地址手动注册 |
| 卡片图片不显示 | 确认集成的 `frontend` 目录完整；访问 HA 的 `/soundsticks5/frontend/soundsticks5.png` 应能打开图片 |
| 更新后仍是旧界面 | 更新集成并重启 HA，再刷新浏览器；界面管理的资源版本会自动更新，无需重复添加 |
| 有声音但没有歌名 | 查看媒体实体的 `media_title`、`media_artist`；若正确数据在另一个播放器，配置“指定媒体实体” |
| 播放按钮禁用 | 检查指定播放器是否可用、是否声明支持该操作 |
| 灯光或音量无法控制 | 检查音箱是否唤醒、BLE 距离、适配器或代理是否能建立连接；必要时关闭占用连接的 App 后刷新状态 |

先用自己的环境验证灯光、音量、播放控制、一次预设保存和应用，再用于自动化。更多适配器和固件的验证范围见 [验证状态](validation.md)。
