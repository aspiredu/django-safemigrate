from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Optional


class SafeEnum(Enum):
    always = "always"
    before_deploy = "before_deploy"
    after_deploy = "after_deploy"


@dataclass
class Safe:
    safe: SafeEnum
    delay: Optional[timedelta] = None

    @classmethod
    def always(cls):
        return cls(safe=SafeEnum.always)

    @classmethod
    def before_deploy(cls):
        return cls(safe=SafeEnum.before_deploy)

    @classmethod
    def after_deploy(cls, *, delay: timedelta = None):
        return cls(safe=SafeEnum.after_deploy, delay=delay)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return other.safe == self.safe and other.delay == self.delay
        raise TypeError()
