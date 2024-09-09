import collections
from agentspeak.runtime import Agent, Intention, AslError

import agentspeak
import roles_src


class RoleAgent(Agent):
    def call(self, trigger, goal_type, term, calling_intention, delayed=False):
        # Modify beliefs.
        if goal_type == agentspeak.GoalType.belief:
            if trigger == agentspeak.Trigger.addition:
                self.add_belief(term, calling_intention.scope)
            else:
                found = self.remove_belief(term, calling_intention)
                if not found:
                    return True

        # Freeze with caller scope.
        frozen = agentspeak.freeze(term, calling_intention.scope, {})

        if not isinstance(frozen, agentspeak.Literal):
            raise AslError("expected literal")

        # Wake up waiting intentions.
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

        # If the goal is an achievement and the trigger is a removal, then the agent will delete the goal from his list of
        # intentions
        if (
            goal_type == agentspeak.GoalType.achievement
            and trigger == agentspeak.Trigger.removal
        ):
            self._unachieve(term)
            return True

        # If the goal is an tellHow and the trigger is an addition, then the agent will add the goal received as string to his
        # list of plans
        if (
            goal_type == agentspeak.GoalType.tellHow
            and trigger == agentspeak.Trigger.addition
        ):
            self._tell_how(term)
            return True

        # If the goal is an askHow and the trigger is an addition, then the agent will find the plan in his list of plans and
        # send it to the agent that asked
        if (
            goal_type == agentspeak.GoalType.askHow
            and trigger == agentspeak.Trigger.addition
        ):
            return self._ask_how(term)

        # If the goal is an unTellHow and the trigger is a removal, then the agent will delete the goal from his list of plans
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
            self._add_role(term)
            return True

        # If the goal is an achievement and the trigger is an addition, then the agent will add the goal to his list of intentions
        applicable_plans = self.plans[
            (trigger, goal_type, frozen.functor, len(frozen.args))
        ]
        intention = Intention()
        # Find matching plan.
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

    def _add_role(self, term, scope):
        Agent.add_belief(term, scope)
        return True
