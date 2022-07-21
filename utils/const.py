import sys


class _Const:
    class ConstError(TypeError):
        pass

    def __setattr__(self, key, value):
        if key in self.__dict__:
            raise self.ConstError("Can't change const.%s" % key)
        self.__dict__[key] = value


sys.modules[__name__] = _Const()
_Const.LIVE = 'live'
_Const.DEAD = 'dead'
_Const.VOID = 'void'
_Const.UNKNOWN = 'unknown'
