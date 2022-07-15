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
# 关于bot
## bot token
首先你需要去 https://t.me/BotFather 找官方机器人，发送 `/newbot` 来新建一个机器人。然后发送 `/mybots` 获取 bot token。具体可以谷歌。

## 你的id
至于自己的id，是**一串数字**，不是你的@xxx，可以找 https://t.me/userinfobot （非官方，我也不知道是谁的机器人）获取。

# 手动部署
下面是以ubuntu为例，没有在CentOS上尝试过。
## 安装依赖
```shell
# 安装git
apt update && apt install git
# python环境
apt install gcc python3-pip -y
```

## 克隆项目
到本地，并复制一份配置文件。
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
# docker 部署
写了个一键脚本，仅在ubuntu上测试过，不保证可用性。
## 脚本部署
```shell
bash <(curl -sL https://raw.githubusercontent.com/tech-fever/check_oracle_bot/main/check_oracle.sh)
```
使用预览：
```bash

    check_oracle_bot Docker安装管理脚本
    1.  安装check_oracle_bot
    2.  修改check_oracle_bot配置
    3.  启动check_oracle_bot
    4.  停止check_oracle_bot
    5.  重启并更新check_oracle_bot
    6.  查看check_oracle_bot日志
    7.  查看check_oracle_bot配置
    8.  卸载check_oracle_bot
    ————————————————
    0.  退出脚本
    

请输入选择 [0-8]:
``` 
注：国内服务器自己解决DockerHub镜像下载慢的问题，我对国内有哪些镜像源也并不清楚  
再注：国内服务器还需要建立telegram bot api反代，然后手动填入BASE_URL

总之建议大家用国外服务器啦~~

# 鸣谢
感谢：
> [作者danuonuo](https://github.com/danuonuo)的[项目](https://github.com//OracleAccountHeplerBot)
