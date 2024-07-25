from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum


class When(Enum):
    always = "always"
    before_deploy = "before_deploy"
    after_deploy = "after_deploy"


@dataclass
class Safe:
    when: When
    delay: timedelta | None = None

    @classmethod
    def always(cls):
        return cls(when=When.always)

    @classmethod
    def before_deploy(cls):
        return cls(when=When.before_deploy)

    @classmethod
    def after_deploy(cls, *, delay: timedelta = None):
        return cls(when=When.after_deploy, delay=delay)
