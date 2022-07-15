from telegram.ext import CallbackContext


def auto_delete(context):
    try:
        context.job.context.delete()
    except BaseException as e:
        print(e)


class MyContext(CallbackContext):
    def send_message(self, to_delete=True, delete_after=30, *args, **kwargs):
        message = self.bot.send_message(*args, **kwargs)
        if to_delete:
            self.job_queue.run_once(auto_delete, delete_after, context=message)
        return message

    def edit_message(self, to_delete: bool, delete_after=30, *args, **kwargs):
        message = self.bot.edit_message_text(*args, **kwargs)
        if to_delete:
            self.job_queue.run_once(auto_delete, delete_after, context=message)
        return message
