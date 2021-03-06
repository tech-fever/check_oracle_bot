class _CONST:
    class ConstError(TypeError):
        pass

    def __setattr__(self, key, value):
        if key in self.__dict__:
            raise self.ConstError("Can't change const.%s" % key)
        self.__dict__[key] = value


import sys

sys.modules[__name__] = _CONST()
_CONST.LIVE = 'live'
_CONST.DEAD = 'dead'
_CONST.VOID = 'void'
