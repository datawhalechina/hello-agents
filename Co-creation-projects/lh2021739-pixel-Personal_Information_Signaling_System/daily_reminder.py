"""
每日提醒工具 - 晚上11:30弹出人物提醒写日报
显示美化窗口
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# 设置控制台编码为UTF-8（Windows）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import tkinter as tk
    from tkinter import messagebox
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    print("❌ 错误: tkinter 未安装（Python应该自带tkinter）")

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️  警告: Pillow 未安装，无法显示图片")
    print("💡 请运行: pip install Pillow")


class DailyReminder:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or Path(__file__).parent
        self.window = None
        self.canvas = None
        self.photo = None
        self.original_image = None
        
        # 窗口设置
        self.window_width = 160
        self.window_height = 160
        self.image_size = (150, 150)  # 图片大小适配窗口
        
    def load_image(self):
        """加载人物图片"""
        # 尝试多种可能的图片路径和格式
        image_paths = [
            self.base_dir / "assets" / "person.png",
            self.base_dir / "assets" / "person.jpg",
            self.base_dir / "assets" / "person.jpeg",
            self.base_dir / "assets" / "reminder.png",
            self.base_dir / "assets" / "reminder.jpg",
        ]
        
        for img_path in image_paths:
            if img_path.exists():
                try:
                    img = Image.open(img_path)
                    # 转换为RGBA模式以支持透明背景
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    # 调整图片大小
                    img = img.resize(self.image_size, Image.Resampling.LANCZOS)
                    self.original_image = img
                    return True
                except Exception as e:
                    print(f"⚠️  加载图片失败 {img_path}: {e}")
                    continue
        
        print("❌ 未找到人物图片文件")
        print("💡 请将图片放在 assets/ 目录下，命名为 person.png 或 person.jpg")
        return False
    
    def show_reminder(self):
        """显示提醒窗口"""
        if not TKINTER_AVAILABLE:
            self.show_system_notification()
            return
        
        if not PIL_AVAILABLE:
            try:
                messagebox.showerror("错误", "Pillow 未安装，无法显示图片\n请运行: pip install Pillow")
            except Exception:
                print("❌ 错误: Pillow 未安装，无法显示图片\n💡 请运行: pip install Pillow")
            return
        
        if not self.load_image():
            try:
                messagebox.showerror("错误", "未找到人物图片文件\n请将图片放在 assets/ 目录下\n支持的名称: person.png, person.jpg, reminder.png")
            except Exception:
                print("❌ 错误: 未找到人物图片文件\n💡 请将图片放在 assets/ 目录下")
            return
        
        # 创建主窗口
        self.window = tk.Toplevel()
        self.window.title("📝 写日报提醒")
        
        # 设置窗口属性
        self.window.attributes('-topmost', True)  # 置顶
        self.window.attributes('-alpha', 0.95)   # 半透明
        
        # 移除窗口边框（可选，创建无边框窗口）
        # self.window.overrideredirect(True)
        
        # 计算窗口位置（屏幕右下角）
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = screen_width - self.window_width - 20  # 距离右边20像素
        y = screen_height - self.window_height - 60  # 距离底部60像素（留出任务栏空间）
        
        self.window.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")
        
        # 设置窗口背景色
        self.window.configure(bg='#f0f0f0')
        
        # 创建画布
        self.canvas = tk.Canvas(
            self.window,
            width=self.window_width,
            height=self.window_height,
            bg='#f0f0f0',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 显示图片
        self.update_image()
        
        # 绑定点击事件
        self.canvas.bind('<Button-1>', self.on_click)
        self.window.bind('<Button-1>', self.on_click)
        
        # 淡入动画
        self.fade_in()
        
        # 窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def update_image(self):
        """更新显示的图片"""
        if not self.original_image:
            return
        
        # 转换为PhotoImage
        self.photo = ImageTk.PhotoImage(self.original_image)
        
        # 清除画布并重新绘制
        self.canvas.delete("image")
        x = (self.window_width - self.image_size[0]) // 2
        y = (self.window_height - self.image_size[1]) // 2  # 居中显示
        self.canvas.create_image(x, y, anchor=tk.NW, image=self.photo, tags="image")
    
    def fade_in(self):
        """淡入动画"""
        if not self.window:
            return
        
        alpha = 0.0
        step = 0.05
        
        def fade():
            nonlocal alpha
            if alpha < 0.95:
                alpha += step
                self.window.attributes('-alpha', alpha)
                self.window.after(20, fade)
        
        fade()
    
    def on_click(self, event=None):
        """点击事件处理"""
        self.on_close()
        self.start_write_report()
    
    def on_close(self):
        """关闭窗口"""
        # 淡出动画
        if self.window:
            alpha = 0.95
            def fade_out():
                nonlocal alpha
                if alpha > 0:
                    alpha -= 0.1
                    try:
                        self.window.attributes('-alpha', alpha)
                        self.window.after(30, fade_out)
                    except Exception:
                        pass
                else:
                    if self.window:
                        self.window.destroy()
            fade_out()
    
    def start_write_report(self):
        """启动写日报"""
        try:
            write_report_script = self.base_dir / "write_report.py"
            if not write_report_script.exists():
                error_msg = f"未找到 write_report.py\n路径: {write_report_script}"
                try:
                    messagebox.showerror("错误", error_msg)
                except Exception:
                    print(f"❌ {error_msg}")
                return
            
            # 使用subprocess启动写日报脚本，并传递--daily参数
            python_exe = sys.executable
            subprocess.Popen(
                [python_exe, str(write_report_script), "--daily"],
                cwd=str(self.base_dir),
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
        except Exception as e:
            error_msg = f"启动写日报失败: {e}"
            try:
                messagebox.showerror("错误", error_msg)
            except Exception:
                print(f"❌ {error_msg}")
    
    def show_system_notification(self):
        """显示系统通知（备选方案）"""
        try:
            from plyer import notification
            notification.notify(
                title="📝 写日报提醒",
                message="该写日报啦！点击通知打开写日报。",
                timeout=10
            )
        except Exception:
            print("📝 写日报提醒：该写日报啦！")


def main():
    """主函数"""
    base_dir = Path(__file__).parent
    
    # 检查今天是否已经提醒过（可选功能）
    # 这里可以添加检查逻辑，避免重复提醒
    
    reminder = DailyReminder(base_dir)
    reminder.show_reminder()
    
    # 运行tkinter主循环
    if TKINTER_AVAILABLE:
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        root.mainloop()


if __name__ == "__main__":
    main()

