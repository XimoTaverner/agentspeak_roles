import enum
import agentspeak


@enum.unique
class RoleGoalType(enum.Enum):
    role = "*"
    tellRole = "*?"


@enum.unique
class Trigger(enum.Enum):
    addition = "+"
    removal = "-"
    update = "+-"
