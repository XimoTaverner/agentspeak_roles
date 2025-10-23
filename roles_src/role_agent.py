import collections
import agentspeak.parser
from agentspeak.runtime import Agent, Intention, AslError

import agentspeak
import agentspeak.runtime
import roles_src
from agentspeak import Literal
from agentspeak.parser import parse_literal
import ast
import re

LOGGER = agentspeak.get_logger(__name__)


def _agentspeak_tuple_of_literals_to_python_list(agentspeak_tuple_of_literals):
    """
    Converts an AgentSpeak tuple of Literals (representing a list)
    to a Python list of their Python representations (e.g., strings).

    Args:
        agentspeak_tuple_of_literals (tuple): A tuple of AgentSpeak Literal objects.

    Returns:
        list: A Python list containing the string representation of each literal's functor.
    """
    python_list = []
    for item_literal in agentspeak_tuple_of_literals:
        python_list.append(_agentspeak_literal_to_python(item_literal))
    return python_list


def _python_list_to_agentspeak_tuple_of_literals(python_list_of_py_objs):
    """
    Converts a Python list of Python objects (e.g., strings)
    to a tuple of AgentSpeak Literals.

    Args:
        python_list_of_py_objs (list): A Python list of objects to convert.

    Returns:
        tuple: A tuple of AgentSpeak Literal objects.
    """
    agentspeak_literals = []
    for py_obj in python_list_of_py_objs:
        agentspeak_literals.append(_python_to_agentspeak_literal(py_obj))
    return tuple(agentspeak_literals)


def _agentspeak_literal_to_python(literal):
    """
    Converts an AgentSpeak Literal to its Python representation.
    Assumes that roles are simple atoms (strings).

    Args:
        literal (Literal): The AgentSpeak Literal to convert.

    Returns:
        str: The string representation of the literal's functor.
    """
    if isinstance(literal, agentspeak.Literal) and literal.functor is not None:
        return literal.functor
    return str(literal)


def _python_to_agentspeak_literal(py_obj):
    """
    Converts a Python object to an AgentSpeak Literal.
    Assumes that roles are strings that will become AgentSpeak atoms.

    Args:
        py_obj (object): The Python object to convert.

    Returns:
        Literal: An AgentSpeak Literal object.
    """
    if isinstance(py_obj, str):
        return agentspeak.Literal(py_obj)
    return agentspeak.Literal(str(py_obj))


class RoleAgent(Agent):
    """
    An agent that extends the base `agentspeak.runtime.Agent` with capabilities
    for managing and using roles. Roles are used to dynamically control which
    plans are applicable.
    """

    def __init__(self, env, name, beliefs=None, rules=None, plans=None, roles=None):
        """
        Initializes the RoleAgent.

        Args:
            env (Environment): The agent's environment.
            name (str): The name of the agent.
            beliefs (dict, optional): Initial beliefs. Defaults to None.
            rules (dict, optional): Initial rules. Defaults to None.
            plans (dict, optional): Initial plans. Defaults to None.
            roles (dict, optional): Initial roles. Defaults to None.
        """
        super().__init__(env, name, beliefs, rules, plans)
        # self.roles = collections.defaultdict(lambda: set()) if roles is None else roles

    def call(self, trigger, goal_type, term, calling_intention, delayed=False):
        """
        Overrides the base `call` method to intercept and handle goals related
        to role management and to filter applicable plans based on the agent's
        current roles.

        Args:
            trigger (Trigger): The trigger type (addition, removal, update).
            goal_type (GoalType): The type of goal (belief, achievement, role, etc.).
            term (Literal): The literal representing the goal or belief.
            calling_intention (Intention): The intention that initiated this call.
            delayed (bool, optional): Whether the intention should be delayed. Defaults to False.

        Returns:
            bool: True if the call was handled, False otherwise.

        Raises:
            AslError: If an unexpected literal type or unknown illocutionary force is encountered.
        """
        if goal_type == agentspeak.GoalType.belief:
            if trigger == agentspeak.Trigger.addition:
                self.add_belief(term, calling_intention.scope)
            else:
                found = self.remove_belief(term, calling_intention)
                if not found:
                    return True

        if (
            goal_type == roles_src.RoleGoalType.tellRole
            and trigger == roles_src.Trigger.addition
        ):
            self._tell_role(term, calling_intention)
            return True

        frozen = agentspeak.freeze(term, calling_intention.scope, {})

        if not isinstance(frozen, agentspeak.Literal):
            raise AslError("expected literal")

        for intention_stack in self.intentions:
            if not intention_stack:
                continue
            intention = intention_stack[-1]

            if not intention.waiter or not intention.waiter.event:
                continue
            event = intention.waiter.event

            if event.trigger != trigger or event.goal_type != goal_type:
                continue

            if agentspeak.unifies_annotated(event.head, frozen):
                intention.waiter = None

        if (
            goal_type == agentspeak.GoalType.achievement
            and trigger == agentspeak.Trigger.removal
        ):
            self._unachieve(term)
            return True

        if (
            goal_type == agentspeak.GoalType.tellHow
            and trigger == agentspeak.Trigger.addition
        ):
            self._tell_how(term)
            return True

        if (
            goal_type == agentspeak.GoalType.askHow
            and trigger == agentspeak.Trigger.addition
        ):
            return self._ask_how(term)

        if (
            goal_type == agentspeak.GoalType.tellHow
            and trigger == agentspeak.Trigger.removal
        ):
            self._untell_how(term)
            return True

        if (
            goal_type == roles_src.RoleGoalType.role
            and trigger == agentspeak.Trigger.addition
        ):
            self.add_role_to_beliefs(term, calling_intention)
            return True

        if (
            goal_type == roles_src.RoleGoalType.role
            and trigger == agentspeak.Trigger.removal
        ):
            self.remove_role_from_beliefs(term, calling_intention)
            return True

        if (
            goal_type == roles_src.RoleGoalType.role
            and trigger == roles_src.Trigger.update
        ):
            old_role_literal = term.args[0]
            new_role_literal = term.args[1]
            self.remove_role_from_beliefs(old_role_literal, calling_intention)
            self.add_role_to_beliefs(new_role_literal, calling_intention)
            return True

        # If the goal is an achievement and the trigger is an addition, then the agent will add the goal to his list of intentions
        # applicable_plans = self.plans[
        #    (trigger, goal_type, frozen.functor, len(frozen.args))
        # ]
        all_possible_plans = self.plans[
            (trigger, goal_type, frozen.functor, len(frozen.args))
        ]
        applicable_plans = [
            p for p in all_possible_plans if self._is_plan_applicable_for_roles(p)
        ]

        intention = Intention()

        for plan in applicable_plans:
            for _ in agentspeak.unify_annotated(
                plan.head, frozen, intention.scope, intention.stack
            ):
                for _ in plan.context.execute(self, intention):
                    intention.head_term = frozen
                    intention.instr = plan.body
                    intention.calling_term = term

                    if not delayed and self.intentions:
                        for intention_stack in self.intentions:
                            if intention_stack[-1] == calling_intention:
                                intention_stack.append(intention)
                                return True

                    new_intention_stack = collections.deque()
                    new_intention_stack.append(intention)
                    self.intentions.append(new_intention_stack)
                    return True
        if goal_type == agentspeak.GoalType.achievement:
            raise AslError(
                "no applicable plan for %s%s%s/%d"
                % (trigger.value, goal_type.value, frozen.functor, len(frozen.args))
            )
        elif goal_type == agentspeak.GoalType.test:
            return self.test_belief(term, calling_intention)
        return True

    def _tell_role(self, term, calling_intention):
        """
        Handles the `tellRole` goal, adding a set of beliefs to the agent.

        Args:
            term (Literal): The literal containing the beliefs to add.
            calling_intention (Intention): The intention that initiated this call.
        """
        belief_list = ast.literal_eval(term.args[0])
        for belief in belief_list:
            belief = self._parse_belief(belief)
            self.add_belief(belief, calling_intention.scope)

    def _parse_belief(self, belief):
        """
        Parses a string representation of a belief into an AgentSpeak Literal.

        Args:
            belief (str): The string representation of the belief.

        Returns:
            Literal: The parsed AgentSpeak Literal object.
        """
        tokens = []
        tokens.extend(
            agentspeak.lexer.tokenize(
                agentspeak.StringSource("<stdin>", belief), agentspeak.Log(LOGGER), 1
            )
        )
        tok = tokens[0]
        log = agentspeak.Log(LOGGER)
        tokens.pop(0)
        tokens = iter(tokens)
        tok, ast_literal = parse_literal(tok, tokens, log)

        visitor = agentspeak.runtime.BuildTermVisitor({})
        return agentspeak.Literal(
            ast_literal.functor,
            (t.accept(visitor) for t in ast_literal.terms),
            (t.accept(visitor) for t in ast_literal.annotations),
        )

    def add_belief(self, term, scope):
        """
        Adds a belief to the agent's belief base.

        Args:
            term (Literal): The belief to add.
            scope (Scope): The scope of the belief.
        """
        term = term.grounded(scope)
        if term.functor is None:
            raise AslError("expected belief literal")

        self.beliefs[(term.functor, len(term.args))].add(term)

    def add_role_to_beliefs(self, role_literal, calling_intention):
        """
        Adds a role to the agent's `role([...])` belief.
        This method ensures the `role` belief is a single literal containing
        a list of all current roles.

        Args:
            role_literal (Literal): The literal representing the role to add.
            calling_intention (Intention): The intention that initiated this call.
        """
        existing_role_belief = None
        if ("role", 1) in self.beliefs:
            for belief in self.beliefs[("role", 1)]:
                if (
                    belief.functor == "role"
                    and belief.args
                    and isinstance(belief.args[0], tuple)
                ):
                    existing_role_belief = belief
                    break

        current_python_list_of_py_objs = []
        if existing_role_belief:
            python_tuple_of_literals = existing_role_belief.args[0]
            current_python_list_of_py_objs = (
                _agentspeak_tuple_of_literals_to_python_list(python_tuple_of_literals)
            )
            self.remove_belief(existing_role_belief, calling_intention)

        python_role_to_add = _agentspeak_literal_to_python(role_literal)
        if python_role_to_add not in current_python_list_of_py_objs:
            current_python_list_of_py_objs.append(python_role_to_add)

        new_python_tuple_of_literals = _python_list_to_agentspeak_tuple_of_literals(
            current_python_list_of_py_objs
        )
        new_role_belief = agentspeak.Literal(
            "role", (new_python_tuple_of_literals,), frozenset()
        )
        self.add_belief(new_role_belief, calling_intention.scope)
        return True

    def remove_role_from_beliefs(self, role_literal, calling_intention):
        """
        Removes a role from the agent's `role([...])` belief.
        It reconstructs the belief without the specified role.

        Args:
            role_literal (Literal): The literal representing the role to remove.
            calling_intention (Intention): The intention that initiated this call.
        """
        existing_role_belief = None
        if ("role", 1) in self.beliefs:
            for belief in self.beliefs[("role", 1)]:
                if (
                    belief.functor == "role"
                    and belief.args
                    and isinstance(belief.args[0], tuple)
                ):
                    existing_role_belief = belief
                    break

        if not existing_role_belief:
            return False

        python_tuple_of_literals = existing_role_belief.args[0]
        current_python_list_of_py_objs = _agentspeak_tuple_of_literals_to_python_list(
            python_tuple_of_literals
        )

        python_role_to_remove = _agentspeak_literal_to_python(role_literal)
        if python_role_to_remove in current_python_list_of_py_objs:
            current_python_list_of_py_objs.remove(python_role_to_remove)
            self.remove_belief(existing_role_belief, calling_intention)

            if current_python_list_of_py_objs:
                new_python_tuple_of_literals = (
                    _python_list_to_agentspeak_tuple_of_literals(
                        current_python_list_of_py_objs
                    )
                )
                new_role_belief = agentspeak.Literal(
                    "role", (new_python_tuple_of_literals,), frozenset()
                )
                self.add_belief(new_role_belief, calling_intention.scope)
            return True
        return False

    def _is_plan_applicable_for_roles(self, plan):
        """
        Determines if a plan is applicable based on the agent's current roles
        and the plan's role annotations.

        A plan is applicable if:
        1. It has no role annotation.
        2. It has annotations, but none of them is a 'role' annotation.
        3. It has a 'role' annotation, and at least one of the roles in the
           agent's current roles matches a role required by the plan.

        Args:
            plan (Plan): The plan to check for applicability.

        Returns:
            bool: True if the plan is applicable, False otherwise.
        """
        agent_roles = set()
        if ("role", 1) in self.beliefs:
            role_belief = next(iter(self.beliefs[("role", 1)]), None)
            if role_belief and isinstance(role_belief.args[0], tuple):
                for role_lit in role_belief.args[0]:
                    agent_roles.add(str(role_lit.functor))

        if not plan.annotation:
            return True

        plan_required_roles = set()
        has_role_annotation = False
        for annotation in plan.annotation.annotations:
            if annotation.functor == "role":
                has_role_annotation = True
                # if isinstance(annotation.terms[0], tuple):
                # annotation.args[0] es una tupla de Literales, ej: (Literal('tank'),)
                # plan_required_roles.update(
                #    str(role_lit.functor) for role_lit in annotation.terms[0]
                # )
                role_literals_tuple = annotation.terms[0].terms
                for role_lit in role_literals_tuple:
                    role_name = str(role_lit.functor)
                    plan_required_roles.add(role_name)

        if not has_role_annotation:
            return True

        print(
            "PLAN REQUIRED ROLES:",
            plan_required_roles,
            "AGENT ROLES:",
            agent_roles,
            "RESULT:",
            not plan_required_roles.isdisjoint(agent_roles),
            self.beliefs,
        )
        return not plan_required_roles.isdisjoint(agent_roles)
