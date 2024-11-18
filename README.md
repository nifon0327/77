# 开播监听应用

该应用程序是一个用于监控Bilibili直播间开播状态的桌面应用程序。它使用Tkinter创建用户界面，并通过托盘图标进行最小化管理。用户可以添加邮箱以接收开播通知，并通过托盘菜单快速打开直播间。

## 功能

- **自动运行脚本**：每分钟运行一次指定的PHP脚本。
- **添加邮箱**：用户可以添加邮箱地址以接收开播通知。
- **托盘图标**：应用程序可以最小化到系统托盘，并通过托盘菜单进行管理。
- **打开直播间**：通过托盘菜单快速打开指定的Bilibili直播间。

## 依赖

- Python 3.x
- Tkinter
- PIL (Pillow)
- Pystray
- PyMySQL

## 安装依赖

在运行该脚本之前，请确保安装了所有必要的Python库。可以使用以下命令安装：

```bash
pip install pillow pystray pymysql PyInstaller
```

## 配置文件

### config.ini

`config.ini` 文件用于存储应用程序的基本配置，例如数据库连接信息和其他应用程序设置。请确保根据您的环境正确配置此文件。

示例内容：
```ini
[database]
host = localhost
user = your_username
password = your_password
database = your_database

[settings]
check_interval = 60  # 检查间隔时间，以秒为单位
```

### sendMail/config.php

`sendMail/config.php` 文件用于配置邮件发送功能。请确保填写正确的SMTP服务器信息和发件人邮箱信息。

示例内容：
```php
<?php
return [
    'smtp_host' => 'smtp.example.com',
    'smtp_port' => 587,
    'smtp_user' => 'your_email@example.com',
    'smtp_pass' => 'your_email_password',
    'from_email' => 'your_email@example.com',
    'from_name' => 'Your Name'
];
?>
```

## 运行脚本

直接运行 `script.py` 文件即可启动应用程序：

```bash
python script.py
```

## 生成可执行文件

要将该Python脚本转换为Windows可执行文件，可以使用 `PyInstaller`。请按照以下步骤操作：

1. 安装PyInstaller：

   ```bash
   pip install pyinstaller
   ```

2. 生成可执行文件：

   在命令行中导航到脚本所在目录，并运行以下命令：

   ```bash
   pyinstaller --onefile --windowed --icon="项目路径\open.ico" script.py --noconsole
   ```

   - `--onefile` 选项将所有文件打包成一个可执行文件。
   - `--windowed` 选项确保应用程序在Windows上运行时不显示命令行窗口。
   - `--icon` 选项指定应用程序的图标。
   - `--noconsole` 选项确保应用程序在运行时不显示控制台窗口。
3. 生成的可执行文件将位于 `dist` 目录中。

4. **注意**：请确保 `config.ini` 文件与生成的可执行文件位于同一目录中，以便应用程序能够正确读取配置。

## 注意事项

- 确保PHP可执行文件在系统路径中，或者在脚本中指定完整路径。
- 数据库连接信息需要根据实际情况进行配置。
- 请确保所有图标文件路径正确无误。

## 许可证

该项目使用MIT许可证。详细信息请参阅LICENSE文件。

## check_bilibili.sql

`check_bilibili.sql` 是一个用于管理和初始化 Bilibili 数据库的 SQL 脚本。该脚本包含多个表的创建和配置，适用于 MySQL 数据库。以下是该脚本中包含的主要表结构：

### 表结构

1. **cb_check_log**
   - 用于记录检查日志。
   - 包含字段：`id`（主键），`name`，`room_id`，`message`，`create_time`。

2. **cb_email_list**
   - 用于存储电子邮件列表。
   - 包含字段：`id`（主键），`email`，`room_id`，`create_time`。

3. **cb_room_list**
   - 用于存储房间列表。
   - 包含字段：`id`（主键），`name`，`room_id`，`create_time`。

4. **cb_room_status**
   - 用于存储房间状态。
   - 包含字段：`id`（主键），`room_id`，`status`，`create_time`，`update_time`。
   - `room_id` 字段具有唯一索引。

### 使用说明

- 在执行该脚本之前，请确保已连接到 MySQL 数据库。
- 执行脚本将会删除现有的同名表并重新创建。
- 请根据需要修改表结构和字段。

### 注意事项

- 确保数据库的字符集和排序规则与脚本中的设置一致（`utf8mb4`）。
- 脚本中设置了 `AUTO_INCREMENT` 的初始值，请根据实际需求调整。

请根据您的实际需求和环境调整路径和配置。希望这个 `README.md` 文件对您有帮助！如果有其他问题，请随时告诉我。
