#!/bin/bash
#
# automatically configure check_oracle_bot by docker-compose
# Only test on Ubuntu 20.04 LTS Ubuntu 22.04 LTS

BOT_PATH="/opt/check_oracle"
BOT_CONTAINER_NAME="check_oracle_bot"
BOT_IMAGE="techfever/check_oracle_bot"
BOT_IMAGE_TAG="latest"

DC_URL="https://raw.githubusercontent.com/tech-fever/check_oracle_bot/main/docker-compose.yml"
CONFIG_URL="https://raw.githubusercontent.com/tech-fever/check_oracle_bot/main/conf.ini.example"

red='\033[0;31m'
green='\033[0;32m'
yellow='\033[0;33m'
plain='\033[0m'
export PATH=$PATH:/usr/local/bin



pre_check() {
    # check root
    [[ $EUID -ne 0 ]] && echo -e "${red}错误: ${plain} 必须使用root用户运行此脚本！\n" && exit 1
    ## China_IP
    if [[ -z "${CN}" ]]; then
        if [[ $(curl -m 10 -s https://ipapi.co/json | grep 'China') != "" ]]; then
            echo "根据ipapi.co提供的信息，当前IP可能在中国，可能无法完成脚本安装，建议手动安装。"
            read -e -r -p "是否选用中国镜像完成安装? [Y/n] " input
            case $input in
            [yY][eE][sS] | [yY])
                echo "使用中国镜像"
                CN=true
                ;;

            [nN][oO] | [nN])
                echo "不使用中国镜像"
                ;;
            *)
                echo "使用中国镜像"
                CN=true
                ;;
            esac
        fi
    fi

    if [[ -z "${CN}" ]]; then
      Get_Docker_URL="https://get.docker.com"
      Get_Docker_Argu=" "
      GITHUB_URL="github.com"
    else
      Get_Docker_URL="https://get.daocloud.io/docker"
      Get_Docker_Argu=" -s docker --mirror Aliyun"
      GITHUB_URL="github.com"
    fi
}

install_base() {
    (command -v curl >/dev/null 2>&1 && command -v wget >/dev/null 2>&1 && command -v getenforce >/dev/null 2>&1) ||
        (install_soft curl wget)
}

install_soft() {
    # Arch官方库不包含selinux等组件
    (command -v yum >/dev/null 2>&1 && yum makecache && yum install $* selinux-policy -y) ||
        (command -v apt >/dev/null 2>&1 && apt update && apt install $* selinux-utils -y) ||
        (command -v pacman >/dev/null 2>&1 && pacman -Syu $*) ||
        (command -v apt-get >/dev/null 2>&1 && apt-get update && apt-get install $* selinux-utils -y)
}

install() {
    install_base

    echo -e "> 安装check_oracle_bot机器人"

    # check directory
    if [ ! -d "$BOT_PATH" ]; then
        mkdir -p $BOT_PATH
    else
        echo "您可能已经安装过check_oracle_bot机器人，重复安装会覆盖数据，请注意备份。"
        read -e -r -p "是否退出安装? [Y/n] " input
        case $input in
        [yY][eE][sS] | [yY])
            echo "退出安装"
            exit 0
            ;;
        [nN][oO] | [nN])
            echo "继续安装"
            ;;
        *)
            echo "退出安装"
            exit 0
            ;;
        esac
    fi
    chmod 777 -R $BOT_PATH

    # check docker
    command -v docker >/dev/null 2>&1
    if [[ $? != 0 ]]; then
        echo -e "正在安装 Docker"
        bash <(curl -sL ${Get_Docker_URL}) ${Get_Docker_Argu} >/dev/null 2>&1
        if [[ $? != 0 ]]; then
            echo -e "${red}下载脚本失败，请检查本机能否连接 ${Get_Docker_URL}${plain}"
            return 0
        fi
        systemctl enable docker.service
        systemctl start docker.service
        echo -e "${green}Docker${plain} 安装成功"
    fi

    # check docker compose
    command -v docker-compose >/dev/null 2>&1
    if [[ $? != 0 ]]; then
        echo -e "正在安装 Docker Compose"
        wget -t 2 -T 10 -O /usr/local/bin/docker-compose "https://${GITHUB_URL}/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" >/dev/null 2>&1
        if [[ $? != 0 ]]; then
            echo -e "${red}下载脚本失败，请检查本机能否连接 ${GITHUB_URL}${plain}"
            return 0
        fi
        chmod +x /usr/local/bin/docker-compose
        echo -e "${green}Docker Compose${plain} 安装成功"
    fi

    modify_bot_config 0

    if [[ $# == 0 ]]; then
        before_show_menu
    fi
}

modify_bot_config() {
    echo -e "> 修改check_oracle_bot机器人配置"

    # download docker-compose.yml
    wget -t 2 -T 10 -O /tmp/docker-compose.yml ${DC_URL} >/dev/null 2>&1

    if [[ $? != 0 ]]; then
        echo -e "${red}下载docker-compose.yml失败，请检查本机能否连接 ${DC_URL}${plain}"
        return 0
    fi

    # download conf.ini
    wget -t 2 -T 10 -O /tmp/conf.ini ${CONFIG_URL} >/dev/null 2>&1

    if [[ $? != 0 ]]; then
        echo -e "${red}下载config.yml失败，请检查本机能否连接 ${CONFIG_URL}${plain}"
        return 0
    fi

    # modify conf.ini
    ## modify v2board info
    read -e -r -p "> 请输入你的bot api：" input
    if [[ $input != "" ]]; then
        BOT_TOKEN=$input
    else
        echo -e "${red}输入为空，即将退出。请重新配置bot${plain}"
        return 0
    fi
    echo -e "> 注意：用户id不是username，可发送任意信息给 https://t.me/userinfobot 获取"
    read -e -r -p "> 请输入您的telegram账号id：" input
    DEVELOPER_CHAT_ID=$input
    if [[ $input == "" ]]; then
        echo -e "${yellow}输入为空，程序将不再发送错误信息给您${plain}"
    fi
    DEVELOPER_CHAT_ID=$(echo "$DEVELOPER_CHAT_ID" | sed -e 's/[]\/&$*.^[]/\\&/g')
    sed -i "s/BOT_TOKEN =/BOT_TOKEN = ${BOT_TOKEN}/g" /tmp/conf.ini
    sed -i "s/DEVELOPER_CHAT_ID =/DEVELOPER_CHAT_ID = ${DEVELOPER_CHAT_ID}/g" /tmp/conf.ini
    echo -e "> 当前bot api: ${green}${DEVELOPER_CHAT_ID}${plain}"
    echo -e "> 当前developer chat id: ${green}${DEVELOPER_CHAT_ID}${plain}"

    # replace conf.ini
    mv /tmp/conf.ini $BOT_PATH/conf.ini
    mv /tmp/docker-compose.yml $BOT_PATH/docker-compose.yml
    echo -e "bot配置 ${green}修改成功，请稍等重启生效${plain}"

    # show config
    show_config 0

    # restart check_oracle_bot
    restart_and_update 0

    if [[ $# == 0 ]]; then
        before_show_menu
    fi
}

start() {
    echo -e "> 检查check_oracle_bot状态"
    # check image exists
    docker images | grep $BOT_IMAGE >/dev/null 2>&1
    if [[ $? != 0 ]]; then
        echo -e "${red}镜像不存在，请先安装${plain}"
        return 0
    fi
    # check container is running
    docker ps -a | grep $BOT_CONTAINER_NAME >/dev/null 2>&1
    if [[ $? == 0 ]]; then
        echo -e "bot已启动，退出"
        return 0
    fi
    # start bot
    echo -e "> 开始启动bot"
    # start docker-compose
    cd $BOT_PATH && docker-compose up -d
    if [[ $? == 0 ]]; then
        echo -e "${green}启动成功${plain}"
    else
        echo -e "${red}启动失败，请稍后查看日志信息${plain}"
    fi

    if [[ $# == 0 ]]; then
        before_show_menu
    fi
}

stop() {
    echo -e "> 停止check_oracle_bot"

    cd $BOT_PATH && docker-compose down
    if [[ $? == 0 ]]; then
        echo -e "${green}停止成功${plain}"
    else
        echo -e "${red}停止失败，请稍后查看日志信息${plain}"
    fi

    if [[ $# == 0 ]]; then
        before_show_menu
    fi
}

restart_and_update() {
    echo -e "> 更新并重启check_oracle_bot"
    cd $BOT_PATH || exit
    docker-compose pull
    docker-compose down
    docker-compose up -d
    if [[ $? == 0 ]]; then
        echo -e "${green}重启成功${plain}"
    else
        echo -e "${red}重启失败，请稍后查看日志信息${plain}"
    fi

    if [[ $# == 0 ]]; then
        before_show_menu
    fi
}

show_log() {
    echo -e "> 获取check_oracle_bot日志"
    echo -e "> 按 ctrl + c 退出"
    cd $BOT_PATH && docker-compose logs -f

    if [[ $# == 0 ]]; then
        before_show_menu
    fi
}

show_config() {
    echo -e "> 查看check_oracle_bot配置"

    cd $BOT_PATH || exit

    # check image exists
    docker images | grep $BOT_IMAGE >/dev/null 2>&1
    if [[ $? == 0 ]]; then
        echo -e "${green}check_oracle_bot已安装${plain}"
    else
        echo -e "${red}check_oracle_bot未安装${plain}"
        return 0
    fi
    # check container is running
    docker ps | grep $BOT_CONTAINER_NAME >/dev/null 2>&1
    if [[ $? == 0 ]]; then
        echo -e "${green}bot已启动${plain}"
    else
        echo -e "${red}bot未启动${plain}"
    fi

    # check conf.ini exists
    if [[ -f $BOT_PATH/conf.ini ]]; then
        echo -e "${green}配置文件conf.ini存在${plain}"
    else
        echo -e "${red}配置文件conf.ini不存在${plain}"
        return 0
    fi
    # check docker-compose.yml exists
    if [[ -f $BOT_PATH/docker-compose.yml ]]; then
        echo -e "${green}配置文件docker-compose.yml存在${plain}"
    else
        echo -e "${red}配置文件docker-compose.yml不存在${plain}"
        return 0
    fi

    # show config
    BOT_TOKEN=$(cat conf.ini | grep "BOT_TOKEN" | awk -F ' ' '{print $3}')
    DEVELOPER_CHAT_ID=$(cat conf.ini | grep "DEVELOPER_CHAT_ID" | awk -F ' ' '{print $3}')

    echo -e "
    bot token：${green}${BOT_TOKEN}${plain}
    DEVELOPER_CHAT_ID：${green}${DEVELOPER_CHAT_ID}${plain}
    "
    if [[ $# == 0 ]]; then
        before_show_menu
    fi
}

uninstall() {
    echo -e "> 卸载check_oracle_bot"

    cd $BOT_PATH && docker-compose down
    rm -rf $BOT_PATH
    docker rmi -f "${BOT_IMAGE}:${BOT_IMAGE_TAG}" > /dev/null 2>&1
    clean_all

    if [[ $# == 0 ]]; then
        before_show_menu
    fi
}

before_show_menu() {
    echo && echo -n -e "${yellow}* 按回车返回主菜单 *${plain}" && read temp
    show_menu
}

clean_all() {
    clean_all() {
    if [ -z "$(ls -A ${BOT_PATH})" ]; then
        rm -rf ${BOT_PATH}
    fi
}
}

show_menu() {
    echo -e "
    ${green}check_oracle_bot Docker安装管理脚本${plain}
    ${green}1.${plain}  安装check_oracle_bot
    ${green}2.${plain}  修改check_oracle_bot配置
    ${green}3.${plain}  启动check_oracle_bot
    ${green}4.${plain}  停止check_oracle_bot
    ${green}5.${plain}  重启并更新check_oracle_bot
    ${green}6.${plain}  查看check_oracle_bot日志
    ${green}7.${plain}  查看check_oracle_bot配置
    ${green}8.${plain}  卸载check_oracle_bot
    ————————————————
    ${green}0.${plain}  退出脚本
    "
    echo && read -ep "请输入选择 [0-8]: " num

    case "${num}" in
    0)
        exit 0
        ;;
    1)
        install
        ;;
    2)
        modify_bot_config
        ;;
    3)
        start
        ;;
    4)
        stop
        ;;
    5)
        restart_and_update
        ;;
    6)
        show_log
        ;;
    7)
        show_config
        ;;
    8)
        uninstall
        ;;
    *)
        echo -e "${red}请输入正确的数字 [0-8]${plain}"
        ;;
    esac
}

pre_check
show_menu