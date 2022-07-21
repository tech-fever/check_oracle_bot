import os
import time

from telegram.ext import PicklePersistence, Updater, ContextTypes, CommandHandler, MessageHandler, Filters, \
    CallbackQueryHandler

from utils import handler
from utils.get_config import GetConfig
from utils.myClass import MyContext, TenancyManager, TenancyGroup


def main():
    # TimeZone
    os.environ['TZ'] = 'Asia/Shanghai'
    time.tzset()
    # Bot config
    bot_token = config['TELEBOT']['bot_token']
    base_url = None if len(config['TELEBOT']['base_url']) == 0 else config['TELEBOT']['base_url']
    base_file_url = None if len(config['TELEBOT']['base_file_url']) == 0 else config['TELEBOT']['base_file_url']

    # Start the bot
    my_persistence = PicklePersistence(filename='./data/my_file')
    updater = Updater(token=bot_token, persistence=my_persistence, use_context=True, base_url=base_url,
                      base_file_url=base_file_url, context_types=ContextTypes(context=MyContext))
    # PS: use_context is by default False in v12, and True in v13
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    # initialize the tenancy groups
    for user_id, user_data in updater.dispatcher.user_data.items():
        if 'tenancy_manager' not in user_data:
            user_data['tenancy_manager'] = TenancyManager()

        if 'tenancy_list' in user_data:
            tenancy_list = user_data['tenancy_list'] if user_data.get('tenancy_list') else None
            timestamp = user_data['timestamp'] if user_data.get('timestamp') else None
            live_cnt = user_data['live_cnt'] if user_data.get('live_cnt') else None
            dead_cnt = user_data['dead_cnt'] if user_data.get('dead_cnt') else None
            default_tenancy_group = TenancyGroup(tenancy_list=tenancy_list,
                                                 timestamp=timestamp, live_cnt=live_cnt,
                                                 dead_cnt=dead_cnt)
            user_data['tenancy_manager'].add_group(tenancy_group=default_tenancy_group, group_name='_default')
            for keys in ['tenancy_list', 'timestamp', 'live_cnt', 'dead_cnt']:
                user_data.pop(keys, None)
    dispatcher.update_persistence()
    dispatcher.bot_data['developer_chat_id'] = int(config['DEVELOPER']['developer_chat_id'])
    dispatcher.bot_data['group_enabled_command'] = {'/start', '/help', '/check'}
    dispatcher.bot_data['group_banned_command'] = {'/group', '/set', '/add', '/rm', '/get', '/del', '/delall',
                                                   '/oracle', '/getgroups'}

    # handlers that are forbidden in groups
    group_banned_handlers = MessageHandler(filters=Filters.chat_type.groups & Filters.command,
                                           callback=handler.pre_check_group_banned_cmd)
    # group_delete_handlers = MessageHandler(filters=Filters.chat_type.groups & Filters.command,
    #                                        callback=handler.post_check_group_banned_cmd)
    dispatcher.add_handler(group_banned_handlers, -1)
    # dispatcher.add_handler(group_delete_handlers, 1)

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler(['start', 'help'], handler.help_command, run_async=True))
    dispatcher.add_handler(CommandHandler('set', handler.set_command))
    dispatcher.add_handler(CommandHandler('add', handler.add_command))
    dispatcher.add_handler(CommandHandler('group', handler.add_group_command))
    dispatcher.add_handler(CommandHandler('rm', handler.rm_command))
    dispatcher.add_handler(CommandHandler('delall', handler.del_all_command))
    dispatcher.add_handler(CommandHandler('del', handler.del_command))
    dispatcher.add_handler(CommandHandler('get', handler.get_command, run_async=True))
    dispatcher.add_handler(CommandHandler('check', handler.check_command, run_async=True))
    dispatcher.add_handler(CommandHandler('oracle', handler.oracle_command))
    dispatcher.add_handler(CommandHandler('getgroups', handler.get_group_list_command, run_async=True))
    dispatcher.add_error_handler(handler.error_handler, run_async=True)

    # on different buttons - answer in Telegram
    dispatcher.add_handler(CallbackQueryHandler(handler.button, run_async=True))

    # start the bot using polling
    updater.start_polling()
    # runs the bot until a termination signal is send
    updater.idle()


if __name__ == '__main__':
    config = GetConfig()
    main()
