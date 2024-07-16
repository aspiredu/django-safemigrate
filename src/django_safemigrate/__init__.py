from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum


class SafeEnum(Enum):
    always = "always"
    before_deploy = "before_deploy"
    after_deploy = "after_deploy"


@dataclass
class Safe:
    safe: SafeEnum
    delay: timedelta | None = None

    @classmethod
    def always(cls):
        return cls(safe=SafeEnum.always)

    @classmethod
    def before_deploy(cls):
        return cls(safe=SafeEnum.before_deploy)

    @classmethod
    def after_deploy(cls, *, delay: timedelta = None):
        return cls(safe=SafeEnum.after_deploy, delay=delay)
