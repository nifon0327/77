import time
import threading
import subprocess
import tkinter as tk
from tkinter import Toplevel, Label, Entry, Button, StringVar
from tkinter import ttk
from webbrowser import open as open_browser
from PIL import Image, ImageTk
from pystray import Icon, MenuItem as item, Menu
import pymysql
import re
import configparser

# 创建 ConfigParser 对象
config = configparser.ConfigParser()

# 使用 open 函数显式指定编码为 UTF-8
with open('config.ini', 'r', encoding='utf-8') as config_file:
    config.read_file(config_file)

# 自定义Text类，实现自动滚动
class AutoScrollText(tk.Text):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def insert(self, index, chars, *args):
        super().insert(index, chars, *args)
        self.see(tk.END)  # 自动滚动到最新信息

def get_db_connection():
    return pymysql.connect(
        host=config['database']['host'],
        user=config['database']['user'],
        password=config['database']['password'],
        database=config['database']['database']
    )

def run_script():
    global process, running
    if running:  # 如果已经在运行，则不再启动新的线程
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        output_text.insert(tk.END, f"{current_time} 提示: 脚本已经在运行。\n")
        return

    running = True
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    output_text.insert(tk.END, f"{current_time} 提示: 脚本开始运行，每分钟执行一次。\n")
    
    def task():
        while running:
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                # 直接使用绝对路径
                script_path = config['paths']['script_path']
                
                # 确保PHP在系统路径中，或者指定完整路径
                php_executable = config['paths']['php_executable']  # 或者 "C:\\path\\to\\php.exe"
                
                process = subprocess.Popen(
                    [php_executable, script_path],
                    startupinfo=startupinfo
                )
                process.wait()  # 等待子进程完成
                process = None  # 释放子进程资源
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                output_text.insert(tk.END, f"{current_time} 脚本已执行。\n")
            except FileNotFoundError as fnf_error:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                output_text.insert(tk.END, f"{current_time} 文件未找到错误: {fnf_error}\n")
            except Exception as e:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                output_text.insert(tk.END, f"{current_time} 脚本执行错误: {e}\n")
                print(f"Exception occurred: {e}")
            finally:
                if process is not None:
                    process.kill()  # 确保子进程被终止
                    process = None  # 释放子进程资源

            check_interval = int(config['setting']['check_interval'])  # 从配置文件读取检查间隔
            for _ in range(check_interval):
                if not running:
                    break
                time.sleep(1)  # 每次循环休眠1秒，总共休眠 check_interval 秒

    threading.Thread(target=task, daemon=True).start()

def stop_script():
    global running
    running = False
    if process:
        process.kill()  # 确保后台进程被杀死
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    output_text.insert(tk.END, f"{current_time} 提示: 脚本已停止。\n")

def add_email():
    def validate_email(email):
        return re.match(r"[^@]+@[^@]+\.[^@]+", email)

    def validate_name(name):
        return len(name.strip()) > 0

    def validate_room_id(room_id):
        return room_id.isdigit()

    def on_focus_out(event, entry, label, validator, message):
        value = entry.get()
        if not validator(value):
            label.config(text=message, fg='red')
        else:
            label.config(text='', fg='green')

    def on_room_id_focus_out(event):
        room_id = room_id_var.get()
        if validate_room_id(room_id):
            room_id_error.config(text='', fg='green')  # 清除错误提示
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT name FROM cb_room_list WHERE room_id=%s", (room_id,))
                        result = cursor.fetchone()
                        if result:
                            name_var.set(result[0])
                            name_entry.config(state='readonly')
                        else:
                            name_entry.config(state='normal')
                            name_var.set('')  # 清空名称
            except pymysql.MySQLError as err:
                print(f"数据库错误: {err}")
            except Exception as e:
                print(f"未知错误: {e}")
        else:
            room_id_error.config(text="房间号必须是数字", fg='red')

    def submit():
        email = email_var.get()
        name = name_var.get()
        room_id = room_id_var.get()
        
        if validate_email(email) and validate_name(name) and validate_room_id(room_id):
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        # 检查房间号和名称是否匹配
                        cursor.execute("SELECT name FROM cb_room_list WHERE room_id=%s", (room_id,))
                        result = cursor.fetchone()
                        
                        if result and result[0] != name:
                            output_text.insert(tk.END, f"提示: 输入的主播名称与记录不一致，请修改。\n")
                            return
                        
                        # 检查是否已经存在相同的邮箱和房间号
                        cursor.execute("SELECT id FROM cb_email_list WHERE email=%s AND room_id=%s", (email, room_id))
                        email_result = cursor.fetchone()
                        
                        if email_result:
                            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                            output_text.insert(tk.END, f"{current_time} 提示: 邮箱 {email} 已经与主播 {name} 关联。\n")
                            return
                        
                        # 插入新的房间号和名称
                        cursor.execute("SELECT id FROM cb_room_list WHERE name=%s AND room_id=%s", (name, room_id))
                        result = cursor.fetchone()
                        
                        if not result:
                            cursor.execute("INSERT INTO cb_room_list (name, room_id) VALUES (%s, %s)", (name, room_id))
                            conn.commit()
                            room_list_id = cursor.lastrowid
                        else:
                            room_list_id = result[0]
                        
                        # 插入新的邮箱
                        cursor.execute("INSERT INTO cb_email_list (email, room_id) VALUES (%s, %s)", (email, room_list_id))
                        conn.commit()
                
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                output_text.insert(tk.END, f"{current_time} 提示: 邮箱 {email} 已成功添加并与主播 {name} 关联。\n")
                dialog.destroy()
            except pymysql.MySQLError as err:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                output_text.insert(tk.END, f"{current_time} 数据库错误: {err}\n")
            except Exception as e:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                output_text.insert(tk.END, f"{current_time} 未知错误: {e}\n")
                import traceback
                output_text.insert(tk.END, f"{current_time} 详细错误信息: {traceback.format_exc()}\n")

    dialog = Toplevel(root)
    dialog.title("添加邮箱")
    dialog.configure(bg='#ffb6c1')
    dialog.iconbitmap(config['paths']['icon_path'])

    # 绑定回车键到 submit 函数
    dialog.bind("<Return>", lambda event: submit())

    # 在主体窗口正中显示
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    root_width = root.winfo_width()
    root_height = root.winfo_height()
    dialog_width = 300
    dialog_height = 250  # 增加高度以预留空间
    dialog.geometry(f"{dialog_width}x{dialog_height}+{root_x + (root_width - dialog_width) // 2}+{root_y + (root_height - dialog_height) // 2}")

    email_var = StringVar()
    name_var = StringVar()
    room_id_var = StringVar()

    Label(dialog, text="邮箱地址：", bg='#ffb6c1', fg='#8b0000').grid(row=0, column=0, padx=10, pady=5, sticky='e')
    email_entry = Entry(dialog, textvariable=email_var)
    email_entry.grid(row=0, column=1, padx=10, pady=5)
    email_error = Label(dialog, text="", bg='#ffb6c1')
    email_error.grid(row=1, column=1, sticky='w')
    email_entry.bind("<FocusOut>", lambda event: on_focus_out(event, email_entry, email_error, validate_email, "无效的邮箱格式"))

    Label(dialog, text="房间号：", bg='#ffb6c1', fg='#8b0000').grid(row=2, column=0, padx=10, pady=5, sticky='e')
    room_id_entry = Entry(dialog, textvariable=room_id_var)
    room_id_entry.grid(row=2, column=1, padx=10, pady=5)
    room_id_error = Label(dialog, text="", bg='#ffb6c1')
    room_id_error.grid(row=3, column=1, sticky='w')
    room_id_entry.bind("<FocusOut>", on_room_id_focus_out)

    Label(dialog, text="主播名称：", bg='#ffb6c1', fg='#8b0000').grid(row=4, column=0, padx=10, pady=5, sticky='e')
    name_entry = Entry(dialog, textvariable=name_var)
    name_entry.grid(row=4, column=1, padx=10, pady=5)
    name_error = Label(dialog, text="", bg='#ffb6c1')
    name_error.grid(row=5, column=1, sticky='w')
    name_entry.bind("<FocusOut>", lambda event: on_focus_out(event, name_entry, name_error, validate_name, "名称不能为空"))

    Button(dialog, text="提交", command=submit, bg='#ffb6c1', fg='#8b0000', width=12).grid(row=6, column=1, pady=20)

def open_stream(room_id, icon=None, item=None):
    url = f"https://live.bilibili.com/{room_id}"
    try:
        open_browser(url)
        print(f"打开直播间: {url}")
    except Exception as e:
        print(f"无法打开直播间: {url}, 错误: {e}")
    
# 确保 tray_icon 是全局变量
tray_icon = None

def minimize_to_tray():
    global tray_icon
    root.withdraw()  # 隐藏主窗口
    if tray_icon is not None:
        tray_icon.stop()  # 停止并销毁现有的托盘图标
    tray_icon_thread = threading.Thread(target=create_tray_icon, daemon=True)
    tray_icon_thread.start()  # 启动托盘图标线程

def create_tray_icon():
    try:
        icon_image = Image.open(config['paths']['icon_path'])
    except FileNotFoundError:
        print("图标文件未找到，请检查路径。")
        return

    def create_menu():
        # 创建二级菜单项列表
        streamer_menu_items = []
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT name, room_id FROM cb_room_list")
                    results = cursor.fetchall()
                    for name, room_id in results:
                        # 为每个主播创建一个二级菜单项
                        def open_stream_callback(room_id):
                            def callback():
                                open_stream(room_id)
                            return callback
                        
                        streamer_menu_items.append(item(name, open_stream_callback(room_id)))
        except pymysql.MySQLError as err:
            print(f"数据库错误: {err}")
        except Exception as e:
            print(f"未知错误: {e}")

        # 创建主菜单
        return Menu(
            item('显示', show_window),
            item('打开直播间', Menu(*streamer_menu_items)),  # 一级菜单项，包含二级菜单
            item('退出', exit_application)
        )

    global tray_icon
    tray_icon = Icon("name", icon_image, "柒月桜", menu=create_menu())

    # 设置托盘图标的点击事件
    tray_icon.run(setup=lambda icon: setattr(icon, 'visible', True))

def show_window(icon, item=None):
    print("显示窗口")
    icon.stop()
    root.after(0, root.deiconify)  # 恢复主窗口

def exit_application(icon, item=None):
    root.destroy()  # 关闭应用程序

def on_window_state_change(event=None):
    if root.state() == 'iconic':  # 窗口被最小化
        minimize_to_tray()

def on_start():
    output_text.insert(tk.END, "欢迎使用开播监听应用！\n")

# 创建主窗口
root = tk.Tk()
root.title("开播监听")
root.geometry("500x300+%d+%d" % ((root.winfo_screenwidth() - 500) / 2, (root.winfo_screenheight() - 300) / 2))
root.configure(bg='#ffb6c1')

# 在 add_email 函数外部，确保这些变量在全局范围内定义
room_id_var = StringVar()
name_var = StringVar()

root.resizable(True, True)
root.overrideredirect(True)

# 窗口移动功能
def start_move(event):
    root.x = event.x
    root.y = event.y

def stop_move(event):
    root.x = None
    root.y = None

def on_motion(event):
    deltax = event.x - root.x
    deltay = event.y - root.y
    x = root.winfo_x() + deltax
    y = root.winfo_y() + deltay
    root.geometry(f"+{x}+{y}")

title_bar = tk.Frame(root, bg='#ffb6c1', relief='raised', bd=2)
title_bar.pack(side=tk.TOP, fill=tk.X)
title_bar.bind("<ButtonPress-1>", start_move)
title_bar.bind("<ButtonRelease-1>", stop_move)
title_bar.bind("<B1-Motion>", on_motion)

icon_image = Image.open(config['paths']['icon_path'])
icon_photo = ImageTk.PhotoImage(icon_image)
icon_label = tk.Label(title_bar, image=icon_photo, bg='#ffb6c1')
icon_label.pack(side=tk.LEFT, padx=5)

title_label = tk.Label(title_bar, text="开播监听", bg='#ffb6c1', fg='#8b0000')
title_label.pack(side=tk.LEFT, padx=10)

process = None
running = False

close_button = tk.Button(title_bar, text='x', command=root.destroy, bg='#ffb6c1', fg='#8b0000', bd=0)
close_button.pack(side=tk.RIGHT, padx=5)

maximize_button = tk.Button(title_bar, text='□', command=lambda: root.state('zoomed') if root.state() == 'normal' else root.state('normal'), bg='#ffb6c1', fg='#8b0000', bd=0)
maximize_button.pack(side=tk.RIGHT, padx=5)

minimize_button = tk.Button(title_bar, text='-', command=minimize_to_tray, bg='#ffb6c1', fg='#8b0000', bd=0)
minimize_button.pack(side=tk.RIGHT, padx=5)

style = ttk.Style()
style.theme_use('default')

style.element_create("Pink.Vertical.TScrollbar.trough", "from", "clam")
style.element_create("Pink.Vertical.TScrollbar.thumb", "from", "clam")
style.element_create("Pink.Vertical.TScrollbar.arrow", "from", "clam")

style.layout("Pink.Vertical.TScrollbar",
             [('Vertical.Scrollbar.trough',
               {'children': [('Vertical.Scrollbar.uparrow', {'side': 'top', 'sticky': 'n'}),
                             ('Vertical.Scrollbar.thumb', {'unit': '1', 'sticky': 'nswe'}),
                             ('Vertical.Scrollbar.downarrow', {'side': 'bottom', 'sticky': 's'})],
                'sticky': 'ns'})])

style.configure("Pink.Vertical.TScrollbar", 
                troughcolor='#ffb6c1',  # 使用现有的粉色
                background='#ffb6c1', 
                arrowcolor='#8b0000',
                bordercolor='#ff69b4',  # 增加边框颜色
                lightcolor='#ffb6c1', 
                darkcolor='#ff69b4')

style.map("Pink.Vertical.TScrollbar",
          background=[('active', '#ffb7c5')])

background_image = Image.open(config['paths']['background_image_path']).convert("RGBA")
alpha = 77
background_image.putalpha(alpha)

canvas = tk.Canvas(root, bg='#ffb6c1')
canvas.pack(fill="both", expand=True)
background_photo = ImageTk.PhotoImage(background_image)
canvas_image = canvas.create_image(0, 0, image=background_photo, anchor="nw")

btn_run = tk.Button(canvas, text="运行脚本", command=run_script, bg='#ffb6c1', fg='#8b0000')
btn_stop = tk.Button(canvas, text="停止脚本", command=stop_script, bg='#ffb6c1', fg='#8b0000')
btn_add_email = tk.Button(canvas, text="添加邮箱", command=add_email, bg='#ffb6c1', fg='#8b0000')

btn_run_window = canvas.create_window(0, 0, anchor='nw', window=btn_run)
btn_stop_window = canvas.create_window(0, 0, anchor='nw', window=btn_stop)
btn_add_email_window = canvas.create_window(0, 0, anchor='nw', window=btn_add_email)

def resize_background_and_buttons(event):
    new_width = canvas.winfo_width()
    new_height = canvas.winfo_height()
    resized_image = background_image.resize((new_width, new_height), Image.LANCZOS)
    new_background_photo = ImageTk.PhotoImage(resized_image)
    canvas.itemconfig(canvas_image, image=new_background_photo)
    canvas.image = new_background_photo

    button_width = btn_run.winfo_reqwidth()
    button_spacing = 40
    total_button_width = 3 * button_width + 2 * button_spacing
    start_x = (new_width - total_button_width) / 2
    button_y = 0.85 * new_height
    canvas.coords(btn_run_window, start_x, button_y)
    canvas.coords(btn_stop_window, start_x + button_width + button_spacing, button_y)
    canvas.coords(btn_add_email_window, start_x + 2 * (button_width + button_spacing), button_y)

root.update_idletasks()
resize_background_and_buttons(None)

root.bind("<Configure>", resize_background_and_buttons)

text_frame = tk.Frame(root, bg='#ffb6c1', bd=0)
text_frame.place(relx=0.05, rely=0.2, relwidth=0.9, relheight=0.6)

output_text = AutoScrollText(text_frame, bg=None, bd=0, fg='#8b0000')
output_text.configure(highlightthickness=0, relief='flat')

scrollbar = ttk.Scrollbar(text_frame, command=output_text.yview, style="Pink.Vertical.TScrollbar")
output_text.config(yscrollcommand=scrollbar.set)

scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

root.bind("<Unmap>", on_window_state_change)

# 显示欢迎消息
on_start()

root.mainloop()