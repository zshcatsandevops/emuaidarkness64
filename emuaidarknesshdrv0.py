#!/usr/bin/env python3
"""
MIPSEMU 1.0c - Darkness Revived (Fast3D Edition)
N64 Emulator with MIPS CPU Core & Basic Graphics Rendering
Python 3.13 | Tkinter GUI
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os, struct, json, time, threading
from pathlib import Path
from datetime import datetime


# ---------------- ROM Header ----------------
class ROMHeader:
    """N64 ROM Header Parser"""
    def __init__(self, data: bytes):
        self.raw_data = data[:0x40]
        self.parse()

    def parse(self):
        magic = struct.unpack('>I', self.raw_data[0:4])[0]
        if magic == 0x80371240:
            self.endian = 'big'
        elif magic == 0x40123780:
            self.endian = 'little'
            self.raw_data = self.swap_endian_n64(self.raw_data)
        elif magic == 0x37804012:
            self.endian = 'byteswap'
            self.raw_data = self.swap_endian_v64(self.raw_data)
        else:
            self.endian = 'unknown'

        self.clock_rate = struct.unpack('>I', self.raw_data[0x04:0x08])[0]
        self.boot_address = struct.unpack('>I', self.raw_data[0x08:0x0C])[0]
        self.release = struct.unpack('>I', self.raw_data[0x0C:0x10])[0]
        self.crc1 = struct.unpack('>I', self.raw_data[0x10:0x14])[0]
        self.crc2 = struct.unpack('>I', self.raw_data[0x14:0x18])[0]
        self.name = self.raw_data[0x20:0x34].decode('ascii', errors='ignore').strip('\x00')
        self.game_id = self.raw_data[0x3B:0x3F].decode('ascii', errors='ignore')
        self.cart_id = chr(self.raw_data[0x3F])

    def swap_endian_n64(self, data):
        result = bytearray(len(data))
        for i in range(0, len(data), 4):
            result[i:i+4] = data[i:i+4][::-1]
        return bytes(result)

    def swap_endian_v64(self, data):
        result = bytearray(len(data))
        for i in range(0, len(data), 2):
            result[i] = data[i+1]; result[i+1] = data[i]
        return bytes(result)


# ---------------- CPU Core ----------------
class MIPSCPU:
    """Simplified MIPS R4300i CPU Core"""
    def __init__(self, memory):
        self.memory = memory
        self.pc = 0xA4000040
        self.registers = [0] * 32
        self.hi = 0; self.lo = 0
        self.running = False
        self.instructions_executed = 0

    def reset(self):
        self.pc = 0xA4000040
        self.registers = [0]*32
        self.hi = self.lo = 0
        self.instructions_executed = 0

    def step(self):
        if not self.running: return
        try:
            instr = self.memory.read_word(self.pc)
            # Stub decode (expand later)
            self.pc += 4
            self.instructions_executed += 1
        except Exception as e:
            print(f"CPU Exception at {hex(self.pc)}: {e}")
            self.running = False


# ---------------- Memory ----------------
class Memory:
    def __init__(self):
        self.rdram = bytearray(8*1024*1024)
        self.rom = None; self.rom_size = 0
    def load_rom(self, rom_data: bytes):
        self.rom = rom_data; self.rom_size = len(rom_data)
    def read_word(self, addr:int) -> int:
        addr &= 0xFFFFFFFF
        if (0x10000000 <= addr < 0x1FBFFFFF) and self.rom:
            rom_addr = addr & 0x0FFFFFFF
            if rom_addr < self.rom_size-3:
                return struct.unpack('>I', self.rom[rom_addr:rom_addr+4])[0]
        if addr < len(self.rdram)-3:
            return struct.unpack('>I', self.rdram[addr:addr+4])[0]
        return 0
    def write_word(self, addr:int, value:int):
        addr &= 0x7FFFFF
        if addr < len(self.rdram)-3:
            struct.pack_into('>I', self.rdram, addr, value & 0xFFFFFFFF)


# ---------------- Graphics (stub) ----------------
class Fast3DStub:
    """Placeholder Fast3D parser (pretends to read triangles)"""
    def __init__(self):
        self.triangles = []
    def step(self):
        # Demo: one red triangle
        self.triangles = [[(300,200),(400,400),(200,400)]]


class VideoInterface:
    def __init__(self, canvas):
        self.canvas = canvas
        self.frame_count = 0
        self.mode = "fast3d"  # or "demo"
        self.fast3d = Fast3DStub()

    def render_frame(self, cpu_state):
        self.canvas.delete("all")
        screen_x, screen_y = 192, 114
        self.canvas.create_rectangle(screen_x, screen_y, screen_x+640, screen_y+480,
                                     fill="#000000", outline="#00ff88", width=2)

        if self.mode == "demo":
            # old bouncing balls (removed here for brevity)
            self.canvas.create_text(512, 300, text="Demo Mode", fill="white")
        elif self.mode == "fast3d":
            self.fast3d.step()
            for tri in self.fast3d.triangles:
                self.canvas.create_polygon(tri, fill="#ff0000", outline="white")

            self.canvas.create_text(512, 150, text="Fast3D Triangle Stub",
                                    font=("Arial",18), fill="#00ff88")

        self.frame_count += 1


# ---------------- Emulator ----------------
class MIPSEMU:
    def __init__(self, root):
        self.root = root
        self.root.title("MIPSEMU 1.0c - Fast3D Edition")
        self.memory = Memory()
        self.cpu = MIPSCPU(self.memory)
        self.canvas = tk.Canvas(root, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.video = VideoInterface(self.canvas)
        self.running = False

        # log
        self.log_text = scrolledtext.ScrolledText(root, height=6, bg="#0a0a0a", fg="#00ff00")
        self.log_text.pack(fill=tk.X)
        self.log("MIPSEMU 1.0c initialized")

    def log(self, msg): 
        t = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{t}] {msg}\n"); self.log_text.see(tk.END)

    def load_rom(self, path):
        data = Path(path).read_bytes()
        header = ROMHeader(data)
        self.memory.load_rom(data)
        self.cpu.reset()
        self.log(f"ROM loaded: {header.name} ({header.game_id})")

    def start(self):
        self.running = True; self.cpu.running = True
        threading.Thread(target=self.emu_loop, daemon=True).start()
        self.render_loop()

    def emu_loop(self):
        while self.running and self.cpu.running:
            self.cpu.step()
            time.sleep(1/60)

    def render_loop(self):
        if self.running:
            state = {'pc':self.cpu.pc,'instructions':self.cpu.instructions_executed,
                     'registers':self.cpu.registers[:8]}
            self.video.render_frame(state)
            self.root.after(16,self.render_loop)


def main():
    root = tk.Tk(); root.geometry("1024x768")
    app = MIPSEMU(root)
    # quick test buttons
    tk.Button(root,text="Open ROM",command=lambda: app.load_rom(filedialog.askopenfilename())).pack()
    tk.Button(root,text="Start",command=app.start).pack()
    root.mainloop()

if __name__=="__main__":
    main()
