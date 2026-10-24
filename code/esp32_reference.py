"""ESP32 侧：nRF24L01 + 电机控制的 MicroPython 参考（从测试脚本整理）"""

# ===== nRF24L01（SPI1: SCK=18 MOSI=23 MISO=19 CSN=5 CE=33）=====
from machine import Pin, SPI
import time

def nrf_init():
    spi = SPI(1, baudrate=1000000, polarity=0, phase=0,
              sck=Pin(18), mosi=Pin(23), miso=Pin(19))
    cs = Pin(5, Pin.OUT, value=1)
    ce = Pin(33, Pin.OUT, value=0)
    return spi, cs, ce

# ===== 电机（LC116 双路 + 履带）：D25/D26 = 右轮，D27/D32 = 左轮 =====
# 实测极性：M1(D25 高) = 右轮后退；M2(D27 高) = 左轮前进
def motors():
    return {
        "m1a": machine.PWM(machine.Pin(25), freq=1000, duty=0),
        "m1b": machine.PWM(machine.Pin(26), freq=1000, duty=0),
        "m2a": machine.PWM(machine.Pin(27), freq=1000, duty=0),
        "m2b": machine.PWM(machine.Pin(32), freq=1000, duty=0),
    }
