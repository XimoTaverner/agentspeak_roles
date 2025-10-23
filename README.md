# agentspeak_roles

## Overview

`agentspeak_roles` is an extension for the AgentSpeak framework that introduces robust role management capabilities for agents. This library allows AgentSpeak agents to dynamically adopt, remove, and update roles, and critically, to filter their applicable plans based on the roles they currently possess. This enhances the flexibility and adaptability of multi-agent systems by enabling context-dependent behavior.

## Features

-   **Role-Based Plan Applicability**: Plans can be annotated with required roles, ensuring they are only considered when an agent holds the necessary roles.
-   **Dynamic Role Management**: Agents can add, remove, and update their roles during runtime.
-   **Agent-to-Agent Role Adoption**: Facilitates the transfer of role-specific knowledge (beliefs and plans) between agents.
-   **Clear Role Belief Representation**: Roles are managed as a structured belief within the agent's belief base.

## Installation

To install `agentspeak_roles`, you can clone the repository and install it as a Python package:

```bash
git clone https://github.com/your-username/agentspeak_roles.git
cd agentspeak_roles
pip install .
```

Make sure you have `agentspeak` installed as well:

```bash
pip install agentspeak
```

## Usage

### Defining Roles in ASL

Roles are defined as annotations on plans in your AgentSpeak (`.asl`) files. For example:

```asl
@p1[role([tank])]
+!attack: role(X)
<-
    .print("Agent is attacking as a tank!").

@p2[role([support])]
+!attack: role(X)
<-
    .print("Agent is healing as a support!").

+!attack
<-
    .print("Agent is performing a general attack!").
```

In this example, the `+!attack` goal will trigger different plans based on whether the agent has the `tank` or `support` role. If neither role is present, the general `+!attack` plan will be applicable.

### Agent Role Management

Agents can manage their roles using custom actions (e.g., `.add_role`, `.remove_role`, `.update_role`) which interact with the `RoleAgent`'s internal belief system. These actions typically send messages to the agent itself to modify its `role([...])` belief.

Refer to the `examples/simple_agent_roles` directory for practical demonstrations of how to define and manage roles within an AgentSpeak environment.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
