from telegram.ext import PicklePersistence, Updater, ContextTypes, CommandHandler, MessageHandler, Filters

from utils import handler
from utils.get_config import GetConfig
from utils.myClass import MyContext


def main():
    # Bot config
    bot_token = config['TELEBOT']['bot_token']
    base_url = None if len(config['TELEBOT']['base_url']) == 0 else config['TELEBOT']['base_url']
    base_file_url = None if len(config['TELEBOT']['base_file_url']) == 0 else config['TELEBOT']['base_file_url']

    # Start the bot
    my_persistence = PicklePersistence(filename='./utils/my_file')
    updater = Updater(token=bot_token, persistence=my_persistence, use_context=True, base_url=base_url,
                      base_file_url=base_file_url, context_types=ContextTypes(context=MyContext))
    # PS：use_context is by default False in v12, and True in v13
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    dispatcher.bot_data['developer_chat_id'] = int(config['DEVELOPER']['developer_chat_id'])
    dispatcher.bot_data['group_enabled_command'] = {'/start', '/help', '/check'}
    dispatcher.bot_data['group_banned_command'] = {'/set', '/add', '/get'}

    # handlers that are forbidden in groups
    group_banned_handlers = MessageHandler(filters=Filters.chat_type.group & Filters.command,
                                           callback=handler.pre_check_group_banned_cmd)
    group_delete_handlers = MessageHandler(filters=Filters.chat_type.group & Filters.command,
                                           callback=handler.post_check_group_banned_cmd)
    dispatcher.add_handler(group_banned_handlers, -1)
    dispatcher.add_handler(group_delete_handlers, 1)
    dispatcher.add_handler(CommandHandler('start', handler.help_command, run_async=True))
    dispatcher.add_handler(CommandHandler('help', handler.help_command, run_async=True))
    dispatcher.add_handler(CommandHandler('set', handler.set_command))
    dispatcher.add_handler(CommandHandler('add', handler.add_command))
    dispatcher.add_handler(CommandHandler('rm', handler.rm_command))
    dispatcher.add_handler(CommandHandler('del', handler.del_command))
    dispatcher.add_handler(CommandHandler('get', handler.get_command, run_async=True))
    dispatcher.add_handler(CommandHandler('check', handler.check_command, run_async=True))
    dispatcher.add_error_handler(handler.error_handler, run_async=True)
    # on different commands - answer in Telegram

    # start the bot using polling
    updater.start_polling()
    # runs the bot until a termination signal is send
    updater.idle()


if __name__ == '__main__':
    config = GetConfig()
    main()
