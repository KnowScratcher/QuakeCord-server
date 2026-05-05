from discord import Embed
import time
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server environments
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import io
import discord
from dependencies import sample_rate, basePath
import os
from .buffer import get_quake_buffer

def to_intensity(pga: float, pgv: float) -> str:
    if (pga < 0.8):
        return "0"
    if (pga <= 2.5):
        return "1"
    if (pga <= 8):
        return "2"
    if (pga <= 25):
        return "3"
    if (pga <= 80):
        return "4"
    if (pgv <= 15):
        return "4"
    if (pgv <= 30):
        return "5弱"
    if (pgv <= 50):
        return "5強"
    if (pgv <= 80):
        return "6弱"
    if (pgv <= 140):
        return "6強"
    return "7"


def build_warning_embed(warning_data: dict) -> Embed:
    warnings = warning_data["warnings"]
    pga_values = [float(warnings[station]["pga"]) for station in warnings]
    pgv_values = [float(warnings[station]["pgv"]) for station in warnings]
    warning = Embed(title="地震警告", color=0xff0000, description="以下是目前所有警告站點資訊")
    warning.add_field(name="📊 觸發站點數量", value=str(len(warnings)), inline=True)
    warning.add_field(name="⚡ 震度", value=to_intensity(
        max(pga_values), max(pgv_values)), inline=True)
    warning.add_field(name="📈 PGA (gal)", value=max(pga_values), inline=True)
    warning.add_field(name="📈 PGV (kine)", value=max(pgv_values), inline=True)
    warning.add_field(
        name="⏰ 觸發演算法", value=f"{'🟩' if warning_data['prev_result'][0] else'🟥'} TPSEM-INT\n{'🟩' if warning_data['prev_result'][1] else'🟥'} R-STA-LTA\n{'🟩' if warning_data['prev_result'][2] else'🟥'} C-STA-LTA", inline=False)
    warning.set_footer(text=f"{warning_data['time']}\nTPSEM 系統自動發送")
    return warning


def build_end_embed() -> Embed:
    end_embed = Embed(title="地震偵測結束", color=0x00ff00, description="震動已經緩和")
    end_embed.set_footer(
        text=f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\nTPSEM 系統自動發送")
    return end_embed


def create_quake_plot(data_array):
    """
    Takes a numpy array of shape (N, 3) and returns a discord.File object.
    """
    # 1. Convert to numpy and transpose so we have 3 rows: x_data, y_data, z_data
    # Data shape changes from [[x,y,z], [x,y,z]] to [[x,x...], [y,y...], [z,z...]]
    data = np.array(data_array).T
    labels = ['EW', 'NS', 'Z']
    # Aesthetic colors for Discord Dark Mode
    colors = ['#ff6b6b', '#4ecdc4', '#45b7d1']

    FONT_PATH = os.path.join(basePath, "fonts", "NotoSansTC-Regular.ttf")
    zh_font = fm.FontProperties(fname=FONT_PATH)
    # 2. Create the figure with 3 subplots
    fig, axs = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    fig.suptitle('震波圖', fontproperties=zh_font, fontsize=16, color='white')
    fig.patch.set_facecolor('#2c2f33')  # Discord-ish background color

    for i in range(3):
        axs[i].plot(np.array(range(-500, len(data[i])-500)) /
                    sample_rate, data[i], color=colors[i], linewidth=1)
        axs[i].set_ylabel(labels[i], color='white')
        axs[i].set_facecolor('#23272a')
        axs[i].tick_params(colors='white')
        axs[i].grid(True, alpha=0.2)

    plt.xlabel('時間(秒)', fontproperties=zh_font, color='white')
    plt.tight_layout(rect=[0.0, 0.03, 1.0, 0.95])  # type: ignore

    # 3. Save to a BytesIO buffer instead of a physical file
    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)  # Free up memory

    # 4. Wrap it in a discord.File
    return discord.File(fp=buf, filename="quake_plot.png")


class DiscordMessageControl:
    def __init__(self, channels: list[discord.TextChannel]):
        self.channels: list = channels
        self.messages = []
        self.warnings = {}
        self.warning_lock = False

    async def init(self) -> None:
        self.messages.clear()

    async def send_warning(self):
        for i in self.channels:
            self.messages.append(await i.send(embed=build_warning_embed(self.warnings)))

    async def edit_warning(self):
        for m in self.messages:
            await m.edit(embed=build_warning_embed(self.warnings))

    async def send_plot(self) -> None:
        if self.warning_lock:
            self.warning_lock = False
            print(len(self.warnings["warnings"]), self.warnings)
            mx_client = max(self.warnings["warnings"], key=lambda station: max(float(self.warnings["warnings"][station]["pga"]), float(self.warnings["warnings"][station]["pgv"])), default="CHY")
            image = create_quake_plot(get_quake_buffer(mx_client))
            for i in self.channels:
                image.fp.seek(0)  # Ensure the buffer is at the beginning
                await i.send(file=image, embed=build_end_embed())
            self.messages.clear()
            # self.warnings.clear()

    async def add_warning(self, warning_stations: dict, result: list) -> None:
        self.warnings["prev_pgs"] = (max(float(warning_stations[station]["pga"]) for station in warning_stations), max(
            float(warning_stations[station]["pgv"]) for station in warning_stations))
        self.warnings["prev_result"] = result
        self.warnings["warnings"] = warning_stations
        self.warnings["time"] = time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime())
        print(self.warnings)
        if self.warning_lock:
            await self.edit_warning()
        else:
            await self.send_warning()
            self.warning_lock = True

    async def edit_warning_data(self, warning_stations: dict, result: list) -> None:
        self.warnings["prev_pgs"] = (max(float(warning_stations[station]["pga"]) for station in warning_stations), max(
            float(warning_stations[station]["pgv"]) for station in warning_stations))
        self.warnings["prev_result"] = [a or b for a,
                                       b in zip(self.warnings["prev_result"], result)]
        self.warnings["warnings"] = warning_stations
        print("edit ",self.warnings["warnings"])
        await self.edit_warning()