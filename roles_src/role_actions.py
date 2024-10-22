from __future__ import print_function, division

import agentspeak
import agentspeak.optimizer
import agentspeak.runtime
from agentspeak.stdlib import actions
from scipy.optimize import linprog
import math
import threading
from collections import deque
import roles_src
from agentspeak import Literal


class RoleActions(agentspeak.Actions):
    def __init__(self, parent=None, actions={}, variadic_actions={}):
        self.parent = parent
        self.actions = actions
        self.variadic_actions = variadic_actions

    def add(self, functor, arity=None, f=None):
        def _add(f):
            if arity is None:
                self.variadic_actions[functor] = f
            else:
                self.actions[(functor, arity)] = f
            return f

        if f is None:
            return _add
        else:
            return _add(f)


actions = RoleActions(actions.parent, actions.actions, actions.variadic_actions)

lock = threading.Lock()
taxi_queue = deque()


@actions.add(".send", 3)
def _send(agent, term, intention):
    # Find the receivers: By a string, atom or list of strings or atoms.
    receivers = agentspeak.grounded(term.args[0], intention.scope)
    if not agentspeak.is_list(receivers):
        receivers = [receivers]
    receiving_agents = []
    for receiver in receivers:
        if agentspeak.is_atom(receiver):
            receiving_agents.append(agent.env.agents[receiver.functor])
        else:
            receiving_agents.append(agent.env.agents[receiver])

    # Illocutionary force.
    ilf = agentspeak.grounded(term.args[1], intention.scope)
    if not agentspeak.is_atom(ilf):
        return
    if ilf.functor == "tell":
        goal_type = agentspeak.GoalType.belief
        trigger = agentspeak.Trigger.addition
    elif ilf.functor == "untell":
        goal_type = agentspeak.GoalType.belief
        trigger = agentspeak.Trigger.removal
    elif ilf.functor == "achieve":
        goal_type = agentspeak.GoalType.achievement
        trigger = agentspeak.Trigger.addition
    elif ilf.functor == "unachieve":
        goal_type = agentspeak.GoalType.achievement
        trigger = agentspeak.Trigger.removal
    elif ilf.functor == "tellHow":
        goal_type = agentspeak.GoalType.tellHow
        trigger = agentspeak.Trigger.addition
    elif ilf.functor == "untellHow":
        goal_type = agentspeak.GoalType.tellHow
        trigger = agentspeak.Trigger.removal
    elif ilf.functor == "askHow":
        goal_type = agentspeak.GoalType.askHow
        trigger = agentspeak.Trigger.addition
    elif ilf.functor == "addRole":
        goal_type = roles_src.RoleGoalType.role
        trigger = agentspeak.Trigger.addition
    elif ilf.functor == "delRole":
        goal_type = roles_src.RoleGoalType.role
        trigger = agentspeak.Trigger.removal
    elif ilf.functor == "updateRole":
        goal_type = roles_src.RoleGoalType.role
        trigger = roles_src.Trigger.update
    elif ilf.functor == "tellRole":
        goal_type = roles_src.RoleGoalType.tellRole
        trigger = roles_src.Trigger.addition
    else:
        raise agentspeak.AslError("unknown illocutionary force: %s" % ilf)

    # TODO: askOne, askAll
    # Prepare message. The message is either a plain text or a structured message.
    if ilf.functor in ["tellHow", "askHow", "untellHow"]:
        message = agentspeak.Literal("plain_text", (term.args[2],), frozenset())
    else:
        message = agentspeak.freeze(term.args[2], intention.scope, {})

    if ilf.functor in ["updateRole"]:
        message = agentspeak.Literal(
            "updateRole",
            tuple(
                (term.args[2]),
            ),
            frozenset(),
        )
        # Broadcast.
        for receiver in receiving_agents:
            receiver.call(trigger, goal_type, message, agentspeak.runtime.Intention())
        yield

    elif ilf.functor in ["tellRole"]:
        beliefs_to_send = []
        plans_to_send = []
        for belief in agent.beliefs:
            belief_iterator = next(iter(agent.beliefs[belief]))
            annots = belief_iterator.annots
            for annot in annots:
                if annot.functor in ["role"]:
                    if term.args[2] in annot.args:
                        beliefs_to_send.append(
                            agentspeak.freeze(belief_iterator, intention.scope, {})
                        )
        for plan_list in agent.plans:
            for plan in agent.plans[plan_list]:
                if plan.annotation is not None:
                    for annot in plan.annotation.annotations:
                        for arg in annot.terms:
                            if term.args[2].__str__() == arg.__str__():
                                plans_to_send.append(
                                    agentspeak.freeze(plan, intention.scope, {})
                                )
        message = (beliefs_to_send, plans_to_send)
        for receiver in receiving_agents:
            receiver.call(trigger, goal_type, message, agentspeak.runtime.Intention())
        yield
    else:
        tagged_message = message.with_annotation(
            agentspeak.Literal("source", (agentspeak.Literal(agent.name),))
        )

        # Broadcast.
        for receiver in receiving_agents:
            receiver.call(
                trigger, goal_type, tagged_message, agentspeak.runtime.Intention()
            )
        yield
