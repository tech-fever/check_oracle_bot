import asyncio
import datetime
import html
import json
import logging
import time
import traceback

import aiohttp
import requests as requests
from telegram import Update, ParseMode
from telegram.ext import CallbackContext, DispatcherHandlerStop

import utils.const as const
from utils.myClass import MyContext, auto_delete

delete_after = 30


def help_command(update: Update, context: MyContext) -> None:
    to_delete = not isPrivateChat(update)
    context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                         reply_to_message_id=update.effective_message.message_id,
                         text='欢迎使用本bot！\n'
                              '本bot可用来查询租户的存活情况。如出现错误请联系技术支持 @locuser \n'
                              '/check - 检查租户存活情况（需要先设定租户名）\n/set - 设定租户名（空格或换行分隔多个租户名）\n'
                              '/add - 添加租户名（空格或换行分隔多个租户名）\n/rm - 删除指定租户名（空格或换行分隔多个租户名）\n'
                              '/del - 删除全部租户名\n/get - 获取已经储存的租户名情况')


def set_command(update: Update, context: MyContext) -> None:
    to_delete = not isPrivateChat(update)
    if len(context.args) < 1:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id, text='用法： /set <租户名1> <租户名2> ...')
        return
    else:
        tenancy_list = set(context.args)
        context.user_data['tenancy_list'] = tenancy_list
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id, text='设置成功！')
        return


def add_command(update: Update, context: MyContext) -> None:
    to_delete = not isPrivateChat(update)
    if len(context.args) < 1:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='添加指定租户名。\n用法： /add <租户名1> <租户名2> ...')
        return
    if context.user_data.get('tenancy_list') is None:
        context.user_data['tenancy_list'] = set()
    context.user_data['tenancy_list'] |= set(context.args)
    context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                         reply_to_message_id=update.effective_message.message_id, text='添加租户名成功！使用 /get 查看已添加的租户名。')


def rm_command(update: Update, context: MyContext) -> None:
    to_delete = not isPrivateChat(update)
    if len(context.args) < 1:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='删除指定租户名。\n用法： /rm <租户名1> <租户名2> ...')
        return
    if context.user_data.get('tenancy_list') is None:
        context.user_data['tenancy_list'] = set()
    context.user_data['tenancy_list'] -= set(context.args)
    context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                         reply_to_message_id=update.effective_message.message_id, text='删除指定租户名成功！使用 /get 查看已添加的租户名。')


def del_command(update: Update, context: MyContext) -> None:
    to_delete = not isPrivateChat(update)
    for key in context.user_data:
        del context.user_data[key]
    context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                         reply_to_message_id=update.effective_message.message_id, text='删除全部租户名成功！')


def get_command(update: Update, context: MyContext) -> None:
    to_delete = not isPrivateChat(update)
    if 'tenancy_list' not in context.user_data or len(context.user_data['tenancy_list']) == 0:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id, text='请先私聊使用 /set 添加租户名。')
        return
    context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                         reply_to_message_id=update.effective_message.message_id,
                         text=f'您已添加的租户名：\n{" ".join(context.user_data["tenancy_list"])}')


def check_command(update: Update, context: MyContext) -> None:
    to_delete = not isPrivateChat(update)
    if 'tenancy_list' not in context.user_data or len(context.user_data['tenancy_list']) == 0:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id, text='请先私聊使用 /set 添加租户名。')
        return
    reply_message = context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                                         reply_to_message_id=update.effective_message.message_id, text='稍等，检查中...')
    tenancies = context.user_data['tenancy_list']

    # res = {const.LIVE: set(), const.DEAD: set(), const.VOID: set()}
    # start = time.perf_counter()
    # for tenancy in tenancies:
    #     res[isTenancyAlive(tenancy)].add(tenancy)
    # end = time.perf_counter()
    # print("request time consuming : %.2fs" % (end - start))
    # print(res)
    # res.clear()

    res = {const.LIVE: set(), const.DEAD: set(), const.VOID: set()}
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    status_codes = loop.run_until_complete(isTenancyAlive_async(tenancies))
    loop.close()
    ind = 0
    for tenancy in tenancies:
        status_code = status_codes[ind]
        if status_code == requests.codes.ok or status_code == requests.codes.found:
            key = const.LIVE
        elif status_code == requests.codes.service_unavailable:
            key = const.DEAD
        else:
            key = const.VOID
        res[key].add(tenancy)
        ind += 1
    if 'timestamp' not in context.user_data:
        context.user_data['timestamp'] = -1
    if 'live_cnt' not in context.user_data:
        context.user_data['live_cnt'] = set()
    if 'dead_cnt' not in context.user_data:
        context.user_data['dead_cnt'] = set()
    last_timestamp = context.user_data['timestamp']
    last_dead_cnt = context.user_data['dead_cnt']
    last_live_cnt = context.user_data['live_cnt']
    context.user_data['timestamp'] = int(time.time())
    context.user_data['live_cnt'] = res[const.LIVE]
    context.user_data['dead_cnt'] = res[const.DEAD] | res[const.VOID]

    text = f'🟢正常账号数：{len(res[const.LIVE])}\n💀异常账号数：{len(res[const.DEAD]) + len(res[const.VOID])}\n'
    if len(res[const.DEAD]) + len(res[const.VOID]) > 0:
        text += f'异常账号包括：\n'
        if len(res[const.DEAD]) > 0:
            text += f'死亡账号数：{len(res[const.DEAD])}\n死亡账号列表：<code>{"<code> </code>".join(res[const.DEAD])}</code>\n'
        if len(res[const.VOID]) > 0:
            text += f'租户不存在：{len(res[const.VOID])}\n租户不存在列表：<code>{"<code> </code>".join(res[const.VOID])}</code>\n'
    else:
        text += f'恭喜！全部存活！🎉'

    if last_timestamp != -1:
        text += f'\n上次检查时间：{datetime.datetime.fromtimestamp(last_timestamp).strftime("%Y-%m-%d %H:%M:%S")}\n'
        text += f"正常账号数：{len(last_live_cnt)} -> {len(context.user_data['live_cnt'])}\n"
        text += f"死亡账号数：{len(last_dead_cnt)} -> {len(context.user_data['dead_cnt'])}\n"
        add_dead = context.user_data['dead_cnt'] - last_dead_cnt
        if len(add_dead) > 0:
            text += f'😭多死了几个：<code>{"<code> </code>".join(add_dead)}</code>\n'

    context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=reply_message.message_id,
                                  parse_mode=ParseMode.HTML, text=text)


def isTenancyAlive(tenancy: str):
    if len(tenancy) == 0:
        return False

    url = f'https://myservices-{tenancy}.console.oraclecloud.com/mycloud/cloudportal/gettingStarted'
    try:
        response = requests.head(url)
        if response.status_code == requests.codes.ok or response.status_code == requests.codes.found:
            return const.LIVE
        elif response.status_code == requests.codes.service_unavailable:
            return const.DEAD
        else:
            return const.VOID
    except requests.exceptions.RequestException as _:
        # print('Error:', e)
        return const.VOID


async def isTenancyAlive_async(tenancies):
    tasks = list()
    for tenancy in tenancies:
        url = f'https://myservices-{tenancy}.console.oraclecloud.com/mycloud/cloudportal/gettingStarted'
        tasks.append(fetch_async(url))
    return await asyncio.gather(*tasks)


async def fetch_async(url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.head(url) as resp:
                status_code = resp.status
                return status_code
        except aiohttp.ClientConnectorError as _:
            return 999


def pre_check_group_banned_cmd(update: Update, context: MyContext) -> None:
    if isPrivateChat(update) or update.effective_message.text is None:
        return
    cmd = update.effective_message.text.split()[0]
    if '@' in cmd:
        cmd = cmd.split('@')[0]

    if cmd in context.bot_data['group_banned_command']:
        context.send_message(True, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='请私聊使用该命令！')
        # print(f'{update.effective_user.username} tried to use {cmd} in group {update.effective_chat.title}')
        if canBotDeleteMessage(update, context):
            context.job_queue.run_once(auto_delete, delete_after, context=update.effective_message)
        raise DispatcherHandlerStop


def isPrivateChat(update: Update):
    return update.effective_chat.type == 'private'


# Delete all the command in groups
def post_check_group_banned_cmd(update: Update, context: MyContext) -> None:
    if isPrivateChat(update) or update.effective_message.text is None:
        return
    if canBotDeleteMessage(update, context):
        context.job_queue.run_once(auto_delete, delete_after + 5, context=update.effective_message)


def canBotDeleteMessage(update: Update, context: MyContext) -> bool:
    bot_chat_info = context.bot.get_chat_member(chat_id=update.effective_chat.id, user_id=context.bot.id)
    return bot_chat_info.can_delete_messages


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


def error_handler(update: object, context: CallbackContext) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096-character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f'An exception was raised while handling an update\n'
        f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )

    # Finally, send the message
    context.bot.send_message(chat_id=context.bot_data['developer_chat_id'], text=message, parse_mode=ParseMode.HTML)
