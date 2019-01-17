from enum import Enum


class Safe(Enum):
    always = "always"
    before_deploy = "before_deploy"
    after_deploy = "after_deploy"
