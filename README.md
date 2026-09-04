# SoundSticks 5 for Home Assistant

[English](README_EN.md) | 简体中文

Harman Kardon SoundSticks 5 的非官方 Home Assistant 本地集成。仓库包含两部分：

- `custom_components/soundsticks5`：通过 BLE GATT 控制灯光、EQ、音量、媒体动作和设备设置；
- `soundsticks5_audio`：可选的 Home Assistant App，通过主机 BlueZ 和 A2DP 唤醒音箱并播放 URL、本地文件或 TTS 音频。

本项目与 Harman Kardon 或 HARMAN International 没有隶属、授权、赞助或背书关系。当前协议主要来自普通版 SoundSticks 5、HK One 2.5.4 和一台测试设备；地区、SKU 和固件差异仍可能存在。

## 功能

- Home Assistant Bluetooth 自动发现，不保存历史 MAC/RPA；
- 灯光开关、`0..100` 亮度、六种灯效、速度、当前灯效颜色和单灯效颜色重置；
- 七段 App 刻度 EQ 与全零重置；
- 反馈音、自动关闭配置和剩余时间；
- BLE 媒体播放/暂停/上一曲/下一曲、绝对音量、曲名和歌手状态；
- GATT 串行访问、通知订阅、回读优先、超时/退避重试、诊断信息；
- 可选音频 App：经典蓝牙扫描、首次配对、trusted、连接/释放、自动重连、A2DP 唤醒；
- URL/HTTP 流/TTS/本地媒体，经 ffmpeg 解码后输出到 PulseAudio/BlueZ；
- 基本队列、暂停/继续/停止、播放完成事件和 WebSocket 实时状态；
- 中英文界面、HACS 元数据和 CI。

这里的 Lighting 只表示灯光，不是音箱电源。BLE 收到媒体命令 ACK 也不代表深度待机已经被唤醒。当前可靠的无物理操作唤醒路径是：此前已配对的经典蓝牙设备建立 A2DP/AVRCP 音频连接；音频 App 的 Wake 按钮就是利用这一行为。

## 安装

详细步骤见 [安装文档](docs/installation.md)。最简流程：

1. 用 HACS 自定义仓库安装，或把 `custom_components/soundsticks5` 复制到 `/config/custom_components/`。
2. 重启 Home Assistant。
3. 唤醒音箱，在“设置 → 设备与服务”接受 Bluetooth 发现，或手动添加 SoundSticks 5。
4. 只需 BLE 控制时到此结束；音频 App 完全可选。
5. 需要唤醒和播放时，将本仓库加入 Home Assistant App 仓库，安装 **SoundSticks Audio**，进行一次经典蓝牙配对，再在集成选项中启用后端（默认 `http://127.0.0.1:8099`）。

普通用户只需要一个由 HA 主机管理的蓝牙适配器。BLE 与经典蓝牙是两个独立协议层，但设计上允许共用同一个物理适配器。实际并发能力仍取决于适配器、BlueZ、代理类型和音箱状态。

## 实体

| 分组 | 实体 |
|---|---|
| Media | 媒体播放器：播放、暂停、上下曲、`0..100` 音量、URL/TTS（有 App 时） |
| Lighting | 灯光、主题、速度、当前主题颜色、颜色重置 |
| EQ | 125/250/500/1000/2000/4000/8000 Hz、EQ 重置 |
| Audio | A2DP 已连接、Wake、Release Bluetooth Audio、后端可用性 |
| Device settings | 反馈音、自动关闭、剩余时间 |
| Diagnostics | BLE 状态、RSSI、最近错误类型 |

完整说明和刻度映射见 [实体文档](docs/entities.md)。

## 安全与范围

没有任意 GATT 写接口，也不实现 OTA、固件传输、恢复出厂、解绑或未知命令。诊断会遮蔽 BLE 地址、API token、媒体 URL、曲名和歌手。附近设备的名称、地址和 manufacturer data 不会上传。

固件版本目前只在官方 App UI 中观察到，尚无安全、稳定且已确认的 BLE 查询，因此没有伪造一个 firmware 实体。重命名虽已有确认帧，但本版本没有提供实体，因为缺少同等可靠的读回与缓存语义。

## 状态

协议编码、解析、状态合并和 App API 有自动化测试。完整 HAOS App 安装、不同架构镜像、首次配对、同适配器 BLE+A2DP 并发、断流恢复及实际音频格式仍属于 **implemented but hardware validation required**，请见 [验证状态](docs/validation.md)。

协议证据和复现工具位于 [soundsticks5-protocol](https://github.com/neqq3/soundsticks5-protocol)。问题报告请附普通版/地区/SKU/固件、HA 安装类型和蓝牙路径，但不要公开设备序列号。

## 许可证

Apache License 2.0，见 [LICENSE](LICENSE)。
