from telegram.ext import CallbackContext


def auto_delete(context):
    context.job.context.delete()


class MyContext(CallbackContext):
    def send_message(self, is_private: bool, delete_after=30, *args, **kwargs):
        message = self.bot.send_message(*args, **kwargs)
        if not is_private:
            self.job_queue.run_once(auto_delete, delete_after, context=message)
        return message
