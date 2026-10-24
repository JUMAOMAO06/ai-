# ai-
具身智能的条件之一

## 代码

`code/` 下是本项目的测试代码与配置说明：

- `rover_ctl.py` — PC 侧串口控制（多通道：行走 / 回转 / 臂 / 斗）
- `cam_grab.py` — 从图传流抓单帧
- `loop_daemon*.py` — 抓图 + 帧差过滤 + 收文本 + 发指令的本地循环（v3 最全）
- `live_stamp.py` — 抓图上烧帧号与时间戳，方便 agent 对齐
- `say_loop.py` — 常驻"嘴"：写文本就让 TTS 念出来
- `voice_in.py` — 麦克风 + VAD 断句 + 转写
- `make_dial.py` — 生成 A4 角度刻度盘（视觉量角器）
- `nrf24.py` / `esp32_reference.py` — ESP32 上的 nRF24L01 与电机控制参考
- `README.md` — 接线表、实测标定数据、踩过的坑

硬件：ESP32 DevKit V1 + nRF24L01+ + 1:64 遥控挖掘机（拆掉原厂射频，用 LC116 H 桥接管）。
