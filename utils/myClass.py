import re
import time
from typing import Union

from telegram.ext import CallbackContext

from utils import const


class MyContext(CallbackContext):
    def send_message(self, to_delete: bool = True, delete_after: int = 30, *args, **kwargs):
        message = self.bot.send_message(*args, **kwargs)
        if to_delete:
            self.job_queue.run_once(auto_delete, delete_after, context=message)
        return message

    def edit_message(self, to_delete: bool, delete_after=30, *args, **kwargs):
        message = self.bot.edit_message_text(*args, **kwargs)
        if to_delete:
            self.job_queue.run_once(auto_delete, delete_after, context=message)
        return message


class TenancyGroup:
    def __init__(self, tenancy_list=None, timestamp=-1, live_cnt=None, dead_cnt=None):
        if tenancy_list is None:
            tenancy_list = set()
        if live_cnt is None:
            live_cnt = set()
        if dead_cnt is None:
            dead_cnt = set()
        self.tenancy_list = set()
        self.add_tenancies(tenancy_list)
        self.timestamp = timestamp
        self.live_cnt = live_cnt
        self.dead_cnt = dead_cnt

    def add_tenancies(self, tenancy_list: Union[list, set]) -> str:
        tenancy_list = extract_tenancy_from_email(tenancy_list)
        valid, invalid = validate_tenancies(tenancy_list)
        self.tenancy_list |= set(valid)
        if len(invalid) > 0:
            return ' '.join(invalid)
        else:
            return ''

    def set_tenancies(self, tenancy_list: Union[list, set]) -> str:
        tenancy_list = extract_tenancy_from_email(tenancy_list)
        valid, invalid = validate_tenancies(tenancy_list)
        self.tenancy_list = set(valid)
        if len(invalid) > 0:
            return ' '.join(invalid)
        else:
            return ''

    def remove_tenancies(self, tenancies: list) -> None:
        self.tenancy_list -= set(tenancies)

    def get_tenancies(self) -> str:
        return ' '.join(self.tenancy_list)

    def check_tenancies(self) -> str:
        # TODO
        pass

    def merge_group(self, tenancy_group) -> None:
        self.tenancy_list |= tenancy_group.get_tenancy_list()

    def set_status(self, res) -> None:
        self.timestamp = int(time.time())
        self.live_cnt = res[const.LIVE]
        self.dead_cnt = res[const.DEAD]

    def update_status(self, res=None) -> (int, set, set):
        result = (self.timestamp, self.live_cnt, self.dead_cnt)
        if res is not None:
            self.set_status(res)
        return result

    def __getstate__(self):
        """return a dict for current state"""
        state = self.__dict__.copy()
        del state['timestamp']
        del state['live_cnt']
        del state['dead_cnt']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.timestamp = -1
        self.live_cnt = set()
        self.dead_cnt = set()
        return state


class TenancyManager(dict):
    def add_group(self, tenancy_group: TenancyGroup, group_name: str) -> None:
        if group_name in self:
            self[group_name].merge_group(tenancy_group)
        else:
            self[group_name] = tenancy_group

    def remove_group(self, group_name: str) -> None:
        if group_name in self:
            return self.pop(group_name, None)

    def get_group(self, group_name: str) -> TenancyGroup:
        if group_name in self:
            return self[group_name]

    def get_group_tenancy(self, group_name: str) -> str:
        if group_name in self:
            return self[group_name].get_tenancy_list()
        else:
            return ''

    def get_group_names(self) -> str:
        return ' '.join(self.keys())

    def get_group_tenancy_all(self) -> str:
        return ' '.join(group.get_tenancy_list() for group in self)

    def __getstate__(self):
        """return a dict for current state"""
        state = self.__dict__.copy()
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        return state


def auto_delete(context) -> None:
    try:
        context.job.context.delete()
    except BaseException as e:
        print(e)


def extract_tenancy_from_email(tenancy_list: Union[list, set]) -> set:
    tenancy_set = set()
    email_pattern = re.compile(
        r"""[\w!#$%&'*+/=?^_`{|}~-]+(?:\.[\w!#$%&'*+/=?^_`{|}~-]+)*@(?:[\w](?:[\w-]*[\w])?\.)+[\w](?:[\w-]*[\w])?""")
    for tenancy in tenancy_list:
        if email_pattern.fullmatch(tenancy):
            tenancy_set.add(tenancy.split('@')[0])
    return tenancy_set


def validate_tenancies(tenancy_list: Union[list, set]) -> (list, list):
    valid = list()
    invalid = list()
    for tenancy in tenancy_list:
        if not is_tenancy_valid(tenancy):
            invalid.append(tenancy)
        else:
            valid.append(tenancy)
    return valid, invalid


# according to https://docs.oracle.com/en-us/iaas/Content/General/Concepts/renamecloudaccount.htm
# tenancy name should be in the format of:
# maximum of 25 characters
# must start with a letter
# lowercase letters or numbers only
# No spaces or capital letters are allowed
def is_tenancy_valid(tenancy: str) -> bool:
    if re.fullmatch(r'^[a-z][a-z\d]{1,24}$', tenancy):
        return True
    else:
        return False
