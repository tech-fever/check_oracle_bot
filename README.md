# 甲骨文账号存活情况检测机器人

| 命令       | 功能       | 群聊可用 |
|:---------|:---------|:-----|
| `/check` | 检查账号存活情况 | ✔️   |
| `/set`   | 设定租户名    | ❌    |
| `/help`  | 查看帮助     | ✔️   |
| `/start` | 启动机器人    | ✔️   |
| `/add`   | 添加租户名    | ❌    |
| `/del`   | 删除租户名    | ✔️   |
| `/get`   | 查看租户名    | ❌    |
| `/rm`    | 删除指定租户名  | ✔️   |

# 部署
克隆到本地，并复制一份配置文件。
```shell
mkdir -p /opt/bot/data/ && cd /opt/bot/
git clone https://github.com/tech-fever/check_oracle_bot.git
pip install -r requirements.txt
cp conf.ini.example conf.ini
```
编辑conf.ini
```shell
vim conf.ini
```
填入自己的bot token和自己的用户id （不是username）。
如果部署在国内服务器上需要对telegram bot api链接进行反代，并填入BASE_URL，如果是国外服务器则留空即可。
```ini
[TELEBOT]
# Set the bot token
BOT_TOKEN =
# Set proxy url (for mainland China servers only)
# If leave it empty, it will use the default value as below:
# base_url = https://api.telegram.org/bot
# base_file_url = https://api.telegram.org/file/bot
BASE_URL =
BASE_FILE_URL =

[DEVELOPER]
# Set the bot developer ID
DEVELOPER_CHAT_ID =
```
## 进程守护
```shell
cat <<'TEXT' > /etc/systemd/system/check_oracle_bot.service
[Unit]
Description=check_oracle_bot telegram utility daemon
After=network.target

[Install]
WantedBy=multi-user.target

[Service]
Type=simple
WorkingDirectory=/opt/bot/check_oracle_bot
ExecStart=/usr/bin/python3 main.py
Restart=always
```
开启进程
```shell
systemctl enable check_oracle_bot.service
systemctl start check_oracle_bot.service
```
