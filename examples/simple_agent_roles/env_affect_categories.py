#!/usr/bin/env python

import agentspeak.stdlib
import os
import roles_src.role_actions
import roles_src.role_agent

env = agentspeak.runtime.Environment()
agent_cls = roles_src.role_agent.RoleAgent

with open(os.path.join(os.path.dirname(__file__), "executer.asl")) as source:
    agents = env.build_agents(
        source,
        1,
        roles_src.role_actions.actions,
        agent_cls=agent_cls,
    )

with open(os.path.join(os.path.dirname(__file__), "dispatcher.asl")) as source:
    agents = env.build_agents(
        source,
        1,
        roles_src.role_actions.actions,
        agent_cls=agent_cls,
    )

if __name__ == "__main__":
    env.run()
