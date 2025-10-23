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
from roles_src.role_agent import (
    _agentspeak_literal_to_python,
    _python_to_agentspeak_literal,
    _agentspeak_tuple_of_literals_to_python_list,
    _python_list_to_agentspeak_tuple_of_literals,
)


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


@actions.add(".printbeliefs", 0)
def _printbeliefs(agent, term, intention):
    """
    Prints the agent's current beliefs to the console.

    Args:
        agent (Agent): The agent executing the action.
        term (Literal): The action term.
        intention (Intention): The intention executing the action.
    """
    print(agent.beliefs)
    yield


@actions.add(".send", 3)
def _send(agent, term, intention):
    """
    Sends a message to one or more agents.

    This action handles various message types (illocutionary forces) such as
    achieving goals, telling beliefs, or managing roles.

    The action term is structured as: .send(Receiver, Ilf, Content).

    Args:
        agent (Agent): The agent executing the action.
        term (Literal): The action term, containing receiver, illocutionary force, and content.
        intention (Intention): The intention executing the action.
    """
    receivers = agentspeak.grounded(term.args[0], intention.scope)
    if not agentspeak.is_list(receivers):
        receivers = [receivers]
    receiving_agents = []
    for receiver in receivers:
        if agentspeak.is_atom(receiver):
            receiving_agents.append(agent.env.agents[receiver.functor])
        else:
            receiving_agents.append(agent.env.agents[receiver])

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
        trigger = agentspeak.Trigger.addition
    else:
        raise agentspeak.AslError("unknown illocutionary force: %s" % ilf)

    if ilf.functor in ["tellHow", "askHow", "untellHow"]:
        message = agentspeak.Literal("plain_text", (term.args[2],), frozenset())
    else:
        message = agentspeak.freeze(term.args[2], intention.scope, {})

    if ilf.functor in ["updateRole"]:
        list_of_roles_literal_cons_cells = agentspeak.freeze(
            term.args[2], intention.scope, {}
        )

        python_tuple_of_roles_literals = _python_list_to_agentspeak_tuple_of_literals(
            list_of_roles_literal_cons_cells
        )

        python_list_of_roles = _agentspeak_tuple_of_literals_to_python_list(
            python_tuple_of_roles_literals
        )

        if len(python_list_of_roles) != 2:
            raise agentspeak.AslError(
                "updateRole expects a list with exactly two roles: [old_role, new_role]"
            )

        old_role_literal = _python_to_agentspeak_literal(python_list_of_roles[0])
        new_role_literal = _python_to_agentspeak_literal(python_list_of_roles[1])

        message = agentspeak.Literal(
            "updateRole", (old_role_literal, new_role_literal), frozenset()
        )

        for receiver in receiving_agents:
            receiver.call(trigger, goal_type, message, agentspeak.runtime.Intention())
        yield

    elif ilf.functor in ["tellRole"]:
        beliefs_to_send = []
        plans_to_send = []
        queried_role = agentspeak.freeze(term.args[2], intention.scope, {})
        python_queried_role = _agentspeak_literal_to_python(queried_role)

        for belief_group in agent.beliefs.values():
            for belief_literal in belief_group:
                for annotation in belief_literal.annots:
                    if annotation.functor == "role":
                        if annotation.args and isinstance(annotation.args[0], tuple):
                            python_tuple_of_literals = annotation.args[0]
                            current_python_list_of_py_objs = (
                                _agentspeak_tuple_of_literals_to_python_list(
                                    python_tuple_of_literals
                                )
                            )
                            if python_queried_role in current_python_list_of_py_objs:
                                beliefs_to_send.append(str(belief_literal) + ".")
                        elif annotation.terms and isinstance(
                            annotation.terms[0], agentspeak.AstList
                        ):
                            python_tuple_of_literals = annotation.terms[0].terms
                            current_python_list_of_py_objs = (
                                _agentspeak_tuple_of_literals_to_python_list(
                                    python_tuple_of_literals
                                )
                            )
                            if python_queried_role in current_python_list_of_py_objs:
                                beliefs_to_send.append(str(belief_literal) + ".")

        message = agentspeak.Literal("plain_text", (str(beliefs_to_send),), frozenset())
        for receiver in receiving_agents:
            receiver.call(
                roles_src.Trigger.addition,
                roles_src.RoleGoalType.tellRole,
                message,
                agentspeak.runtime.Intention(),
            )
        for plan_list in agent.plans:
            for plan in agent.plans[plan_list]:
                if plan.annotation is not None:
                    for annot in plan.annotation.annotations:
                        if annot.functor == "role":
                            if (
                                isinstance(annot, Literal)
                                and annot.args
                                and isinstance(annot.args[0], tuple)
                            ):
                                python_tuple_of_literals = annot.args[0]
                                current_python_list_of_py_objs = (
                                    _agentspeak_tuple_of_literals_to_python_list(
                                        python_tuple_of_literals
                                    )
                                )
                                if (
                                    python_queried_role
                                    in current_python_list_of_py_objs
                                ):
                                    strplan = agentspeak.runtime.plan_to_str(plan)
                                    message = agentspeak.Literal(
                                        "plain_text", (strplan,), frozenset()
                                    )
                                    for receiver in receiving_agents:
                                        receiver.call(
                                            agentspeak.Trigger.addition,
                                            agentspeak.GoalType.tellHow,
                                            message,
                                            agentspeak.runtime.Intention(),
                                        )
                            else:

                                python_tuple_of_literals = annot.terms[0].terms

                                current_python_list_of_py_objs = (
                                    _agentspeak_tuple_of_literals_to_python_list(
                                        python_tuple_of_literals
                                    )
                                )
                                if (
                                    python_queried_role
                                    in current_python_list_of_py_objs
                                ):
                                    strplan = agentspeak.runtime.plan_to_str(plan)
                                    message = agentspeak.Literal(
                                        "plain_text", (strplan,), frozenset()
                                    )
                                    for receiver in receiving_agents:
                                        receiver.call(
                                            agentspeak.Trigger.addition,
                                            agentspeak.GoalType.tellHow,
                                            message,
                                            agentspeak.runtime.Intention(),
                                        )

        yield
    else:
        tagged_message = message.with_annotation(
            agentspeak.Literal("source", (agentspeak.Literal(agent.name),))
        )

        for receiver in receiving_agents:
            receiver.call(
                trigger, goal_type, tagged_message, agentspeak.runtime.Intention()
            )
        yield
