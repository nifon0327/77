<?php
require 'vendor/autoload.php';
// 引入 PHPMailer 类
use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

$config = require 'config.php';

// 数据库配置
$host = $config['database']['host'];
$dbname = $config['database']['dbname'];
$username = $config['database']['username'];
$password = $config['database']['password'];

// 获取所有主播的 room_id 和 name
function getRoomInfo($pdo) {
    $stmt = $pdo->query("SELECT id,room_id, `name` FROM cb_room_list"); // 查询所有 room_id 和 name
    return $stmt->fetchAll(PDO::FETCH_ASSOC); // 返回包含 room_id 和 name 的数组
}

// 根据 room_id 获取对应的邮箱地址
function getEmailAddressesByRoomId($pdo, $roomId) {
    $stmt = $pdo->prepare("SELECT email FROM cb_email_list WHERE room_id = :room_id"); // 查询指定 room_id 的邮箱地址
    $stmt->execute(['room_id' => $roomId]);
    return $stmt->fetchAll(PDO::FETCH_COLUMN); // 返回邮箱地址数组
}

// 获取主播状态
function getStreamerInfo($url) {
    global $config;
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_VERBOSE, true); // 启用详细调试信息
    curl_setopt($ch, CURLOPT_CAINFO, $config['curl']['cacert_path']); // 添加指定的证书
    $response = curl_exec($ch);

    if ($response === false) {
        echo 'cURL 错误: ' . curl_error($ch); // 输出 cURL 错误信息
    }

    curl_close($ch);

    $data = json_decode($response, true);
    $return = [
        'online' => $data['data']['online'] ?? 0,
        'user_cover' => $data['data']['user_cover'] ?? '',
        'title' => $data['data']['title'] ?? '',
        'live_time' => $data['data']['live_time'] ?? '',
        'url' => $url,
    ];

    return $return;
}

// 发送邮件
function sendEmail($to, $subject, $message) {
    global $config;
    $mail = new PHPMailer(true);
    try {
        // 服务器设置
        $mail->isSMTP();                                         // 设置使用 SMTP
        $mail->Host       = $config['smtp']['host'];             // 设置 SMTP 服务器
        $mail->SMTPAuth   = true;                                // 启用 SMTP 身份验证
        $mail->Username   = $config['smtp']['username'];         // SMTP 用户名
        $mail->Password   = $config['smtp']['password'];         // SMTP 密码
        $mail->SMTPSecure = PHPMailer::ENCRYPTION_SMTPS;         // 启用 SSL 加密
        $mail->Port       = $config['smtp']['port'];             // TCP 端口

        // 收件人设置
        $mail->setFrom($config['smtp']['from_email'], $config['smtp']['from_name']);
        foreach ($to as $email) {
            $mail->addAddress($email);                           // 添加收件人
        }

        // 内容设置
        $mail->isHTML(true);                                      // 设置邮件格式为 HTML
        $mail->CharSet = 'UTF-8';                                 // 设置编码
        $mail->Subject = $subject;
        $mail->Body    = $message;

        $mail->send();                                           // 发送邮件
    } catch (Exception $e) {
        echo "邮件发送失败: {$mail->ErrorInfo}";                  // 错误处理
    }
}

// 记录日志到数据库
function logStatus($pdo, $roomId, $streamerName, $status) {
    $timestamp = date('Y-m-d H:i:s'); // 获取当前时间
    $logContent = "[$timestamp] 当前状态: " . ($status?'开播':'未开播');
    $stmt = $pdo->prepare("INSERT INTO cb_check_log (room_id, name, message) VALUES (:room_id, :name, :message)");
    $stmt->execute(['room_id' => $roomId, 'name' => $streamerName, 'message' => $logContent]);
}

// 获取主播的上次状态
function getLastStatus($pdo, $roomId) {
    $stmt = $pdo->prepare("SELECT `status` FROM cb_room_status WHERE room_id = :room_id");
    $stmt->execute(['room_id' => $roomId]);
    return $stmt->fetchColumn() ?: 0; // 如果没有记录，返回 0
}

// 更新主播的状态
function updateStatus($pdo, $roomId, $status) {
    $stmt = $pdo->prepare("INSERT INTO cb_room_status (room_id, `status`) VALUES (:room_id, :status)
                           ON DUPLICATE KEY UPDATE `status` = :status");
    $stmt->execute(['room_id' => $roomId, 'status' => $status]);
}

// 判断是否是节日的函数
function isHoliday() {
    $today = date('Y-m-d');
    // 这里添加2024年、2025年、2026年的节日
    $holidays = [
        // 2024年
        '2024-01-01' => '元旦',
        '2024-02-10' => '春节',
        '2024-05-01' => '劳动节',
        '2024-06-10' => '端午节',
        '2024-09-17' => '中秋节',
        '2024-10-01' => '国庆节',
        '2024-12-25' => '圣诞节',

        // 2025年
        '2025-01-01' => '元旦',
        '2025-01-29' => '春节',
        '2025-05-01' => '劳动节',
        '2025-06-01' => '端午节',
        '2025-09-07' => '中秋节',
        '2025-10-01' => '国庆节',
        '2025-12-25' => '圣诞节',

        // 2026年
        '2026-01-01' => '元旦',
        '2026-02-17' => '春节',
        '2026-05-01' => '劳动节',
        '2026-06-19' => '端午节',
        '2026-09-26' => '中秋节',
        '2026-10-01' => '国庆节',
        '2026-12-25' => '圣诞节',
    ];

    // 二十四节气
    $solarTerms = [
        // 2024年
        '2024-02-04' => '立春',
        '2024-02-19' => '雨水',
        '2024-03-05' => '惊蛰',
        '2024-03-20' => '春分',
        '2024-04-20' => '谷雨',
        '2024-05-05' => '立夏',
        '2024-05-21' => '小满',
        '2024-06-06' => '芒种',
        '2024-06-21' => '夏至',
        '2024-07-07' => '小暑',
        '2024-07-22' => '大暑',
        '2024-08-07' => '立秋',
        '2024-08-23' => '处暑',
        '2024-09-07' => '白露',
        '2024-09-23' => '秋分',
        '2024-10-08' => '寒露',
        '2024-10-23' => '霜降',
        '2024-11-07' => '立冬',
        '2024-11-22' => '小雪',
        '2024-12-07' => '大雪',
        '2024-12-21' => '冬至',
        '2025-01-05' => '小寒',
        '2025-01-20' => '大寒',

        // 2025年
        '2025-02-04' => '立春',
        '2025-02-19' => '雨水',
        '2025-03-05' => '惊蛰',
        '2025-03-20' => '春分',
        '2025-04-20' => '谷雨',
        '2025-05-05' => '立夏',
        '2025-05-21' => '小满',
        '2025-06-06' => '芒种',
        '2025-06-21' => '夏至',
        '2025-07-07' => '小暑',
        '2025-07-22' => '大暑',
        '2025-08-07' => '立秋',
        '2025-08-23' => '处暑',
        '2025-09-07' => '白露',
        '2025-09-23' => '秋分',
        '2025-10-08' => '寒露',
        '2025-10-23' => '霜降',
        '2025-11-07' => '立冬',
        '2025-11-22' => '小雪',
        '2025-12-07' => '大雪',
        '2025-12-21' => '冬至',
        '2026-01-05' => '小寒',
        '2026-01-20' => '大寒',

        // 2026年
        '2026-02-04' => '立春',
        '2026-02-19' => '雨水',
        '2026-03-05' => '惊蛰',
        '2026-03-20' => '春分',
        '2026-04-20' => '谷雨',
        '2026-05-05' => '立夏',
        '2026-05-21' => '小满',
        '2026-06-06' => '芒种',
        '2026-06-21' => '夏至',
        '2026-07-07' => '小暑',
        '2026-07-22' => '大暑',
        '2026-08-07' => '立秋',
        '2026-08-23' => '处暑',
        '2026-09-07' => '白露',
        '2026-09-23' => '秋分',
        '2026-10-08' => '寒露',
        '2026-10-23' => '霜降',
        '2026-11-07' => '立冬',
        '2026-11-22' => '小雪',
        '2026-12-07' => '大雪',
        '2026-12-21' => '冬至',
    ];

    if (isset($holidays[$today])) {
        return $holidays[$today]; // 返回节日名称
    } elseif (isset($solarTerms[$today])) {
        return $solarTerms[$today]; // 返回节气名称
    }
    return false; // 返回 false
}

// 主逻辑
try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname", $username, $password); // 创建数据库连接
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $roomInfos = getRoomInfo($pdo); // 获取所有 room_id 和 name

    foreach ($roomInfos as $roomInfo) {
        $id = $roomInfo['id'];
        $roomId = $roomInfo['room_id'];
        $streamerName = $roomInfo['name'];
        $streamerApiUrl = "https://api.live.bilibili.com/room/v1/Room/get_info?room_id=$roomId"; // 动态设置 API URL
        $emailTo = getEmailAddressesByRoomId($pdo, $id); // 获取对应 room_id 的邮箱地址
        $streamerInfo = getStreamerInfo($streamerApiUrl);
        $currentStatus = $streamerInfo['online'];
        logStatus($pdo, $roomId, $streamerName, $currentStatus); // 记录当前状态到数据库
        $lastStatus = getLastStatus($pdo, $roomId); // 从数据库获取上次状态
        $message = "
<div style='max-width:600px; margin:0 auto; font-family:Arial,sans-serif; background-color:#ffffff; padding:20px; border-radius:12px; box-shadow:0 2px 10px rgba(0,0,0,0.1);'>
    <div style='text-align:center; margin-bottom:25px;'>
        <h2 style='color:#00a1d6; margin:0;'>🎉 开播提醒 🎉</h2>
        <p style='font-size:18px; color:#333; margin:10px 0;'>您关注的主播 <strong style='color:#00a1d6;'>{$streamerName}</strong> 已开播！</p>
    </div>
    
    <div style='background-color:#f8f9fa; padding:15px; border-radius:8px; margin-bottom:20px;'>
        <div style='margin-bottom:12px;'>
            <span style='color:#666;'>📺 直播标题：</span>
            <span style='color:#333; font-weight:bold;'>{$streamerInfo['title']}</span>
        </div>
        <div style='margin-bottom:12px;'>
            <span style='color:#666;'>⏰ 开播时间：</span>
            <span style='color:#333;'>{$streamerInfo['live_time']}</span>
        </div>
    </div>

    <div style='text-align:center; margin:20px 0;'>
        <a href='https://live.bilibili.com/{$roomId}' style='display:inline-block; 
            background-color:#00a1d6; 
            color:#ffffff; 
            padding:12px 30px; 
            border-radius:25px; 
            text-decoration:none;
            font-weight:bold;
            transition: all 0.3s ease;'>
            👉 立即观看直播
        </a>
    </div>

    <div style='margin:20px 0;'>
        <a href='https://live.bilibili.com/{$roomId}' style='text-decoration:none; display:block;'>
            <img src='{$streamerInfo['user_cover']}' alt='直播间封面' 
                style='width:100%; border-radius:12px; display:block; box-shadow:0 4px 12px rgba(0,0,0,0.1);'>
        </a>
    </div>";

        $holidayName = isHoliday();
        if ($holidayName) {
            $solarTermsList = [
                '立春', '雨水', '惊蛰', '春分', '清明', '谷雨',
                '立夏', '小满', '芒种', '夏至', '小暑', '大暑',
                '立秋', '处暑', '白露', '秋分', '寒露', '霜降',
                '立冬', '小雪', '大雪', '冬至', '小寒', '大寒'
            ];
            if (in_array($holidayName, $solarTermsList)) {
                $message .= "<div style='background:linear-gradient(135deg, #f6f8ff 0%, #f1f5ff 100%); 
                    padding:15px; 
                    border-radius:10px; 
                    margin-top:20px;
                    border-left:4px solid #00a1d6;'>
                    <p style='color:#555; margin:0; font-size:15px;'>🌸 祝您{$holidayName}快乐，愿您在这个节气里身体健康，万事如意！</p>
                </div>";
            } else {
                $message .= "<div style='background:linear-gradient(135deg, #fff6f6 0%, #fff1f1 100%); 
                    padding:15px; 
                    border-radius:10px; 
                    margin-top:20px;
                    border-left:4px solid #ff6b6b;'>
                    <p style='color:#555; margin:0; font-size:15px;'>🎊 今天是{$holidayName}，别忘了祝主播{$streamerName}{$holidayName}快乐！</p>
                </div>";
            }
        }

        $message .= "</div>";
        $emailSubject = "主播 $streamerName 开播通知";
        if ($currentStatus > 0 && $lastStatus == 0) {
            sendEmail($emailTo, $emailSubject, $message); // 发送邮件到多个收件人
        }
        updateStatus($pdo, $roomId, $currentStatus); // 更新数据库中的状态
    }

} catch (PDOException $e) {
    echo "数据库连接失败: " . $e->getMessage(); // 错误处理
}
?>