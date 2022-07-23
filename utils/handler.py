import asyncio
import datetime
import html
import json
import logging
import re
import traceback

import aiohttp
import requests as requests
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, DispatcherHandlerStop

import utils.const as const
from utils.myClass import MyContext, auto_delete, TenancyManager, TenancyGroup

delete_after = 50  # delete after 50 seconds


def help_command(update: Update, context: MyContext) -> None:
    to_delete = not isPrivateChat(update)
    context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                         reply_to_message_id=update.effective_message.message_id,
                         parse_mode=ParseMode.HTML,
                         text='Hi! {}!欢迎使用本bot！\n'.format(update.effective_user.mention_html()) + \
                              '本bot可用来查询租户的存活情况。如出现错误请联系技术支持 @locuser \n'
                              '/set - 设置租户名\n\t设置默认组：/set 租户名1 租户名2 ..\n\t设置指定组：/set 组名 租户名1 租户名2 ...\n'
                              '/add - 添加租户名\n\t添加到默认组：/add 租户名1 租户名2 ...\n\t添加到指定组：/add 组名 租户名1 租户名2 ...\n'
                              '/rm - 删除指定租户名（空格或换行分隔多个租户名）\n删除默认组的租户名：/rm 租户名1 租户名2 ...'
                              '\n\t删除指定组的租户名：/rm 组名 租户名1 租户名2 ...\n'
                              '/group - 添加组名\n\t用法：/group 组名 组名2 ...\n'
                              '/getgroups - 查看已添加的组名\n'
                              '/get - 获取已经储存的租户名情况\n\t查询全部组：/get 租户名1 租户名2 ...\n\t查询指定组：/get 组名 租户名1 租户名2 ...\n'
                              '/del - 删除指定组名\n\t删除默认组：/del 组名1 组名2 ...\n\t删除指定组：/del 组名 组名2 ...\n'
                              '/delall - 删除全部组名和租户名\n'
                              '\n⭐/oracle - <b><i>使用交互键盘查询oracle存活情况</i></b>\n'
                              '⭐/check - <b><i>检查租户存活情况</i></b>\n\t'
                              '查询默认组：/check\n\t临时查询租户名（不进行保存）：/check 租户名1 租户名2 ...\n\t查询指定组：/check 组名1 组名2 ...'
                              '\n⭐支持直接添加邮件地址，取@前的部分作为租户名进行添加\n')


def set_command(update: Update, context: MyContext) -> None:
    """
    设置租户名，用法：
    设置默认组：/set 租户名1 租户名2 ...
    设置指定组：/set 组名 租户名1 租户名2 ...
    :param update:
    :param context:
    :return:
    """
    to_delete = not isPrivateChat(update)
    if context.user_data.get('tenancy_manager') is None:
        context.user_data['tenancy_manager'] = TenancyManager()

    if len(context.args) < 1:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='设置默认组： /set 租户名1 租户名2 ...\n设置指定组： /set 组名 租户名1 租户名2 ...\n设置指定组的时候请使用 /getgroups '
                                  '查看确保组名已经存在，若不存在请使用 /group 组名1 组名2 ... 来添加。')
        return
    group_name = context.args[0]
    if group_name not in context.user_data['tenancy_manager']:
        group_name = '_default'
        tenancy_list = set(context.args)
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id, text='将使用默认组_default。')
        if group_name not in context.user_data['tenancy_manager']:
            context.user_data['tenancy_manager'][group_name] = TenancyGroup()

    elif len(context.args) > 1:
        tenancy_list = set(context.args[1:])
    else:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='对于组 {} 未指定需要设置的租户名。'.format(group_name))
        return
    invalid_tenancies = context.user_data['tenancy_manager'][group_name].set_tenancies(tenancy_list)
    if group_name == '_default':
        get_cmd = '/get'
    else:
        get_cmd = f'<code>/get {group_name}</code>'
    texts = []
    if len(invalid_tenancies) < len(tenancy_list):
        texts.append('添加成功！使用 {} 来查看来查看设置的租户名租户名'.format(get_cmd))
    if len(invalid_tenancies) > 0:
        texts.append('以下租户名不符合规范：\n<code>{}</code>\n租户名应该仅包含小写字母和数字，且以小写字母开头，长度在2-25。'.format(invalid_tenancies))
    context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                         reply_to_message_id=update.effective_message.message_id, parse_mode=ParseMode.HTML,
                         text='\n'.join(texts))


def add_command(update: Update, context: MyContext) -> None:
    """
    添加租户名到组，用法：
    添加到默认组：/add 租户名1 租户名2 ...
    添加到指定组：/add 组名 租户名1 租户名2 ...
    :param update: 
    :param context: 
    :return: 
    """
    to_delete = not isPrivateChat(update)
    if context.user_data.get('tenancy_manager') is None:
        context.user_data['tenancy_manager'] = TenancyManager()

    if len(context.args) < 1:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='添加指定租户名至默认组。\n用法： /add 租户名1 租户名2 ...\n添加指定租户名指定组： /add 组名 租户名1 租户名2 ...'
                                  '\n设置指定组的时候请使用 /getgroups 查看确保组名已经存在，若不存在请使用 /group 组名1 组名2 ... 来添加。')
        return
    group_name = context.args[0]
    if group_name not in context.user_data['tenancy_manager']:
        group_name = '_default'
        tenancy_list = set(context.args)
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id, text='将使用默认组_default。')
        if group_name not in context.user_data['tenancy_manager']:
            context.user_data['tenancy_manager'][group_name] = TenancyGroup()
    elif len(context.args) > 1:
        tenancy_list = set(context.args[1:])
    else:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='对于组 {} 未指定需要添加的租户名。'.format(group_name))
        return
    invalid_tenancies = context.user_data['tenancy_manager'][group_name].add_tenancies(tenancy_list)
    if group_name == '_default':
        get_cmd = '/get'
    else:
        get_cmd = f'<code>/get {group_name}</code>'
    texts = []
    if len(invalid_tenancies) < len(tenancy_list):
        texts.append('添加成功！使用 {} 来查看租户名'.format(get_cmd))
    if len(invalid_tenancies) > 0:
        texts.append('以下租户名不符合规范：\n<code>{}</code>\n租户名应该仅包含小写字母和数字，且以小写字母开头，长度在2-25。'.format(invalid_tenancies))
    context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                         reply_to_message_id=update.effective_message.message_id, parse_mode=ParseMode.HTML,
                         text='\n'.join(texts))


def add_group_command(update: Update, context: MyContext) -> None:
    """
    添加组，用法：
    /group 组名1 组名2 ...
    :param update: 
    :param context: 
    :return: 
    """
    to_delete = not isPrivateChat(update)
    if context.user_data.get('tenancy_manager') is None:
        context.user_data['tenancy_manager'] = TenancyManager()

    if len(context.args) < 1:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='添加指定组名，\n用法： /group 组名1 组名2 ...')
        return
    invalid_group_name = []
    for group in context.args:
        if re.fullmatch(r'^[\w\d\u4e00-\u9fa5]{1,20}$', group) is None:
            invalid_group_name.append(group)
            continue
        if group not in context.user_data['tenancy_manager']:
            newGroup = TenancyGroup()
            context.user_data['tenancy_manager'][group] = newGroup
    text = '添加组名成功！使用 /getgroups 查看已添加的组名。使用 /set 组名 租户名1 租户名2 ... 来添加租户名至指定组。'
    if len(invalid_group_name) > 0:
        text += '\n组名支持中文英文数字下划线，长度20以内。以下组名包含非法字符或长度不符合：\n<code>{}</code>'.format(' '.join(invalid_group_name))
        return

    context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                         reply_to_message_id=update.effective_message.message_id, text=text, parse_mode=ParseMode.HTML)


def get_group_list_command(update: Update, context: MyContext) -> None:
    """
    查看已添加的组名，用法：
    /getgroups
    :param update: 
    :param context: 
    :return: 
    """
    to_delete = not isPrivateChat(update)
    if context.user_data.get('tenancy_manager') is None or len(context.user_data['tenancy_manager']) == 0:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id, text='没有已经保存的租户名')
        return

    if len(context.user_data.get('tenancy_manager')) == 0:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='组不存在。请先添加组名。\n用法： /group 组名1 组名2 ...')
        return
    texts = ['已经添加的组有：']
    for group_name in context.user_data['tenancy_manager']:
        texts.append('<code>{}</code>'.format(group_name))

    context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                         reply_to_message_id=update.effective_message.message_id,
                         text='\n'.join(texts), parse_mode=ParseMode.HTML)


def rm_command(update: Update, context: MyContext) -> None:
    """
    删除指定组中的指定租户名，用法：
    删除默认组的租户名：/rm 租户名1 租户名2 ...
    删除指定组的租户名：/rm 组名 租户名1 租户名2 ...
    :param update: 
    :param context: 
    :return: 
    """
    to_delete = not isPrivateChat(update)
    if context.user_data.get('tenancy_manager') is None or len(context.user_data['tenancy_manager']) == 0:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id, text='没有已经保存的租户名')
        return

    if len(context.args) < 1:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='删除指定租户名。用法：\n删除默认组指定租户名: /rm 租户名1 租户名2 ...\n删除指定组指定租户名: /rm 组名 租户名1 租户名2 ...')
        return
    if context.user_data.get('tenancy_manager') is None:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='组不存在。请先添加组名。\n用法： /group 组名1 组名2 ...')
        return
    group_name = context.args[0]
    if group_name not in context.user_data['tenancy_manager']:
        group_name = '_default'
        tenancy_list = set(context.args)
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id, text='将使用默认组_default。')
        if group_name not in context.user_data['tenancy_manager']:
            context.user_data['tenancy_manager'][group_name] = TenancyGroup()
    elif len(context.args) > 1:
        tenancy_list = set(context.args[1:])
    else:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='对于组 {} 未指定需要删除的租户名。'.format(group_name))
        return
    context.user_data['tenancy_manager'][group_name].remove_tenancies(tenancy_list)

    if group_name == '_default':
        get_cmd = '/get'
    else:
        get_cmd = f'<code>/get {group_name}</code>'

    context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                         reply_to_message_id=update.effective_message.message_id, parse_mode=ParseMode.HTML,
                         text='删除指定租户名成功！使用 <code>{}</code> 查看默认已添加的租户名。'.format(get_cmd))


def del_all_command(update: Update, context: MyContext) -> None:
    """
    删除所有租户名和组，用法：
    /delall
    :param update: 
    :param context: 
    :return: 
    """
    to_delete = not isPrivateChat(update)
    if context.user_data.get('tenancy_manager') is None or len(context.user_data['tenancy_manager']) == 0:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id, text='没有已经保存的租户名')
        return

    if update.callback_query:
        if update.callback_query.data == 'confirm to del':
            context.user_data['tenancy_manager'].clear()
            context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id, text='删除全部租户名成功！')
        elif update.callback_query.data == 'cancel to del':
            context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id, text='取消删除！')
    else:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id, text='确定要删除全部组和租户名吗？',
                             reply_markup=InlineKeyboardMarkup(
                                 [[InlineKeyboardButton('确定', callback_data='confirm to del')],
                                  [InlineKeyboardButton('取消', callback_data='cancel to del')]]))


def del_command(update: Update, context: MyContext) -> None:
    """
    删除指定组的所有租户名，用法：
    删除默认组：/del
    删除指定组：/del 组名
    :param update: 
    :param context: 
    :return: 
    """
    to_delete = not isPrivateChat(update)
    if context.user_data.get('tenancy_manager') is None or len(context.user_data['tenancy_manager']) == 0:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id, text='没有已经保存的租户名')
        return

    if update.callback_query:
        if update.callback_query.data.startswith('confirm to del'):
            if len(update.callback_query.data.split()) == 3:
                context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                              message_id=update.effective_message.message_id, text='未知错误！请联系管理员！')
                return
            else:
                group_names = update.callback_query.data.split(' ')[3:]
            deleted, invalid = [], []
            for group in group_names:
                if context.user_data['tenancy_manager'].remove_group(group) is not None:
                    deleted.append(group)
                else:
                    invalid.append(group)
            texts = []
            if len(deleted) > 0:
                texts.append('已删除组： {}'.format(', '.join(deleted)))
            if len(invalid) > 0:
                texts.append('组 {} 不存在！'.format(', '.join(invalid)))
            context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id, text='\n'.join(texts))
        elif update.callback_query.data == 'cancel to del':
            context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id, text='取消删除！')
    elif context.user_data.get('tenancy_manager') is None:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id, text='没有数据，请勿重复操作！')
    else:
        group_names = ' '.join(context.args)
        if len(group_names) == 0:
            group_names = '_default'
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             text='确定要删除以下组以及其数据吗：\n{}'.format(group_names),
                             reply_markup=InlineKeyboardMarkup(
                                 [[InlineKeyboardButton('确定', callback_data='confirm to del {}'.format(group_names))],
                                  [InlineKeyboardButton('取消', callback_data='cancel to del')]]))


def get_command(update: Update, context: MyContext) -> None:
    """
    获取指定组的租户名，用法：
    获取所有组：/get
    获取指定组：/get 组名1 组名2 ...
    :param update:
    :param context:
    :return:
    """
    to_delete = not isPrivateChat(update)
    if context.user_data.get('tenancy_manager') is None or len(context.user_data['tenancy_manager']) == 0:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='请先私聊使用 /set 添加租户名。\n或使用 /group 组名 组名 ... 添加组名。再使用 /get 来查看已添加的租户名。')
        return

    if len(context.args) > 0:
        group_names = context.args
    else:
        group_names = context.user_data['tenancy_manager'].get_group_names().split()
    texts = ['已添加的组名和组内租户名：']
    for group in group_names:
        texts.append('{}: <code>{}</code>'.format(group, context.user_data['tenancy_manager'][group].get_tenancies()))
    context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                         reply_to_message_id=update.effective_message.message_id,
                         text='\n'.join(texts), parse_mode=ParseMode.HTML)


def oracle_command(update: Update, context: MyContext) -> None:
    """
    生成 inline Keyboard ，每个按钮是一个组名，用于查询不同组的租户名账号状态，用法：
    /oracle
    :param update:
    :param context:
    :return:
    """
    to_delete = not isPrivateChat(update)
    if context.user_data.get('tenancy_manager') is None or len(context.user_data['tenancy_manager']) == 0:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='请先私聊使用 /set 添加租户名。或使用 /group 组名 组名 ... 添加组名。再使用 /get 来查看已添加的租户名。')
        return

    group_names = context.user_data.get('tenancy_manager').get_group_names().split()
    keyboard = [[InlineKeyboardButton(group, callback_data='check {}'.format(group))] for group in group_names]
    keyboard.append([InlineKeyboardButton('查看组内租户名详情', callback_data='get')])
    keyboard.append([InlineKeyboardButton('关闭菜单', callback_data='close')])
    context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                         reply_to_message_id=update.effective_message.message_id,
                         text='请选择要查询的组名：', reply_markup=InlineKeyboardMarkup(keyboard))


def oracle_callback(update: Update, context: MyContext) -> None:
    """
    /oracle 命令按下按钮后的回调函数
    :param update:
    :param context:
    :return:
    """
    to_delete = not isPrivateChat(update)
    if context.user_data.get('tenancy_manager') is None or len(context.user_data['tenancy_manager']) == 0:
        context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=update.effective_message.message_id,
                                      text='没有保存的租户组数据！')
        return

    if update.callback_query.data == 'close':
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.effective_message.message_id)
    elif update.callback_query.data == 'get':
        context.args = []
        get_command(update, context)
    elif update.callback_query.data.startswith('check'):
        group = update.callback_query.data.split()[1]
        if group in context.user_data['tenancy_manager']:
            tenancies = context.user_data['tenancy_manager'][group].get_tenancies()
            context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                                 parse_mode=ParseMode.HTML, text='{}: <code>{}</code>'.format(group, tenancies))
            context.args = [group]
            check_command(update, context)
        else:
            context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                          message_id=update.effective_message.message_id,
                                          text='请重新使用 /oracle 来查询。没有保存的租户组数据！ {} 组不存在！'.format(group))


def check_command(update: Update, context: MyContext) -> None:
    """
    查询租户名的状态，用法：
    临时检查： /check 租户名1 租户名2
    检查组： /check 组名1 组名2
    检查默认组： /check
    :param update:
    :param context:
    :return:
    """
    to_delete = not isPrivateChat(update)
    if context.user_data.get('tenancy_manager') is None or len(context.user_data['tenancy_manager']) == 0:
        context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                             reply_to_message_id=update.effective_message.message_id,
                             text='请先私聊使用 /set 添加租户名或用 /group 添加组名。')
        return

    if len(context.args) == 0:
        group_names = {'_default'}
    else:
        group_names = set(context.args)
    not_in_group = set()
    for group in group_names:
        if group not in context.user_data['tenancy_manager']:
            not_in_group.add(group)

    if len(not_in_group) > 0:
        group_names -= not_in_group
        group_names.add('_临时租户名')
    for group in group_names:
        if group != '_临时租户名':
            tenancies = context.user_data['tenancy_manager'][group].get_tenancies().split()
        else:
            tenancies = not_in_group
            group = '_临时租户名'
            context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                                 text='以下名字不属于组名：\n{}\n将作为临时租户名进行查询。'.format(' '.join(tenancies)))
        reply_message = context.send_message(to_delete=to_delete, chat_id=update.effective_chat.id,
                                             reply_to_message_id=update.effective_message.message_id, text='稍等，检查中...')

        res = {const.LIVE: set(), const.DEAD: set(), const.VOID: set(), const.UNKNOWN: set()}
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
            elif status_code == 999:
                key = const.VOID
            else:
                key = const.UNKNOWN
            res[key].add(tenancy)
            ind += 1
        if group != '_临时租户名':
            tenancy_group = context.user_data['tenancy_manager'][group]
            last_timestamp, last_live_cnt, last_dead_cnt = tenancy_group.update_status(res)
        else:
            last_timestamp = -1
        texts = []
        if group == '_default':
            texts.append('默认组的查询结果')
        else:
            texts.append('分组 <b>{}</b> 查询结果'.format(group))
        texts.append('🟢正常账号数：{}'.format(len(res[const.LIVE])))
        texts.append('🔴异常账号数：{}\n'.format(len(res[const.DEAD]) + len(res[const.VOID])))
        if len(res[const.DEAD]) + len(res[const.VOID]) > 0:
            texts.append('异常账号包括：')
            if len(res[const.DEAD]) > 0:
                texts.append(
                    '死亡账号数量：{}\n死亡账号列表：<code>{}</code>'.format(len(res[const.DEAD]), " ".join(res[const.DEAD])))
            if len(res[const.VOID]) > 0:
                texts.append(
                    '租户名不存在：{}\n租户名不存在列表：<code>{}</code>'.format(len(res[const.VOID]), " ".join(res[const.VOID])))
            if len(res[const.UNKNOWN]) > 0:
                texts.append(
                    '未知状态数：{}\n未知状态列表：<code>{}</code>'.format(len(res[const.UNKNOWN]), " ".join(res[const.UNKNOWN])))
        else:
            texts.append('恭喜！暂无异常账号🎉')

        if last_timestamp != -1:
            texts.append(f'\n上次检查时间：{datetime.datetime.fromtimestamp(last_timestamp).strftime("%Y-%m-%d %H:%M:%S")}')
            texts.append(f"正常账号数量：{len(last_live_cnt)} -> {len(tenancy_group.live_cnt)}")
            texts.append(f"死亡账号数量：{len(last_dead_cnt)} -> {len(tenancy_group.dead_cnt)}")
            add_dead = tenancy_group.dead_cnt - last_dead_cnt
            if len(add_dead) > 0:
                texts.append(f'😭增加死亡数：<code>{" ".join(add_dead)}</code>\n')

        context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=reply_message.message_id,
                                      parse_mode=ParseMode.HTML, text='\n'.join(texts))


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


def button(update: Update, context: MyContext) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    if query.data == 'close' or query.data == 'get' or query.data.startswith('check'):
        oracle_callback(update, context)
    elif query.data == 'confirm to del' or query.data == 'cancel to del':
        del_all_command(update, context)
    elif query.data.startswith('confirm to del '):
        del_command(update, context)


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
        f'<code>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
        '</code>\n\n'
        f'<code>context.chat_data = {html.escape(str(context.chat_data))}</code>\n\n'
        f'<code>context.user_data = {html.escape(str(context.user_data))}</code>\n\n'
        f'<code>{html.escape(tb_string)}</code>'
    )

    # Finally, send the message
    context.bot.send_message(chat_id=context.bot_data['developer_chat_id'], text=message, parse_mode=ParseMode.HTML)
