"""nRF24L01+ 最小驱动（MicroPython）——只够验证 SPI 通不通 + 收发短指令。
接线（ESP32 DevKit V1）：
  SCK->D18  MOSI->D23  MISO->D19  CSN->D5  CE->D4  VCC->3.3V(独立)  GND->共地
"""
from machine import Pin, SPI
import time

R_REG = 0x00
W_REG = 0x20
R_RX_PAYLOAD = 0x61
W_TX_PAYLOAD = 0xA0
FLUSH_TX = 0xE1
FLUSH_RX = 0xE2
NOP = 0xFF

CONFIG = 0x00
EN_AA = 0x01
EN_RXADDR = 0x02
SETUP_AW = 0x03
SETUP_RETR = 0x04
RF_CH = 0x05
RF_SETUP = 0x06
STATUS = 0x07
RX_ADDR_P0 = 0x0A
TX_ADDR = 0x10
RX_PW_P0 = 0x11


class NRF24:
    def __init__(self, sck=18, mosi=23, miso=19, csn=5, ce=4, channel=76):
        self.spi = SPI(1, baudrate=4_000_000, polarity=0, phase=0,
                       sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso))
        self.cs = Pin(csn, Pin.OUT, value=1)
        self.ce = Pin(ce, Pin.OUT, value=0)
        self.channel = channel
        time.sleep_ms(50)
        # 上电后必须给足 100ms 才能配置
        self.write_reg(CONFIG, 0x08)   # PWR_UP=1, CRC 2字节
        time.sleep_ms(5)

    def _xfer(self, data):
        self.cs(0)
        r = self.spi.write_readinto(data, bytearray(len(data))) if False else None
        out = self.spi.write_readinto(data, buf := bytearray(len(data)))
        self.cs(1)
        return buf

    def status(self):
        self.cs(0)
        b = self.spi.read(1, NOP)
        self.cs(1)
        return b[0]

    def write_reg(self, reg, val):
        self.cs(0)
        self.spi.write(bytes([W_REG | reg, val]))
        self.cs(1)

    def read_reg(self, reg):
        self.cs(0)
        self.spi.write(bytes([R_REG | reg]))
        v = self.spi.read(1, NOP)
        self.cs(1)
        return v[0]

    def init_tx(self, payload_len=32):
        self.write_reg(RF_CH, self.channel)
        self.write_reg(RF_SETUP, 0x06)      # 1Mbps, 0dBm
        self.write_reg(EN_AA, 0x00)         # 关自动应答，先求通
        self.write_reg(EN_RXADDR, 0x00)
        self.write_reg(SETUP_RETR, 0x00)
        self.write_reg(RX_PW_P0, payload_len)
        addr = b"\xe7\xe7\xe7\xe7\xe7"
        self.cs(0); self.spi.write(bytes([TX_ADDR]) + addr); self.cs(1)
        self.write_reg(CONFIG, 0x0A)        # PWR_UP=1, PRIM_RX=0
        time.sleep_ms(5)

    def send(self, text):
        data = text.encode("utf-8")[:32]
        data = data + b"\x00" * (32 - len(data))
        self.ce(0)
        self.cs(0); self.spi.write(bytes([W_TX_PAYLOAD]) + data); self.cs(1)
        self.ce(1)
        time.sleep_ms(1)
        self.ce(0)
        time.sleep_ms(10)
        self.cs(0); self.spi.write(bytes([STATUS, 0x70])); self.cs(1)  # 清标志


def report():
    n = NRF24()
    lines = []
    lines.append("STATUS=0x%02X" % n.status())
    lines.append("CONFIG=0x%02X" % n.read_reg(CONFIG))
    lines.append("RF_CH=0x%02X" % n.read_reg(RF_CH))
    lines.append("RF_SETUP=0x%02X" % n.read_reg(RF_SETUP))
    lines.append("SETUP_AW=0x%02X" % n.read_reg(SETUP_AW))
    return "\n".join(lines)
