"""agents.py - defines the triage agent, the three specialists, and the
escalate-to-human tool. This is the main file: everything else in this
folder exists to support what happens here.

The multi-agent "triage" pattern
---------------------------------
This is the diagram from exercise_2.md (multiagent_exercise2.png):

                              main.py
                                 |  triage_agent.run(message, deps=customer)
                                 v
               s           +---------------+
                          | triage_agent  |  <- the ONLY agent main.py talks to
                          +---------------+
                           /      |      \\        \\
                          /       |       \\         \\
           ask_billing_agent  ask_technical_agent  ask_sales_agent   escalate_to_human
                  |                  |                  |                   |
                  v                  v                  v                   v
            billing_agent     technical_agent      sales_agent        (plain function,
            (an AI call)       (an AI call)        (an AI call)        no AI call - just
                                                                        writes a ticket file)

Triage vs. the "handoff" pattern from lecture 07
--------------------------------------------------
Lecture 07's coach_agent called ALL of its specialists for every question,
then combined their answers. A triage agent is different: it reads ONE
customer message and picks EXACTLY ONE of the four branches below - the one
that best matches what the customer needs - the same way a human working a
support inbox sorts each new ticket into exactly one queue before anyone
answers it. See the instructions given to `triage_agent` further down; the
"IMPORTANT" line is what enforces "exactly one", because nothing in the
Python code itself can force the model to stop after one tool call.

Key idea, same as lecture 07: a *tool* of the triage agent simply calls
another agent's `.run()`. That is all "delegation" is - the specialist's
answer comes back to the triage agent as a normal string, which it then
relays to the customer (lightly reworded or not, depending on what it
decides).

Connections to other files
----------------------------
- model.py         -> `nvidia_model()` gives the LLM used by all four agents
- dependencies.py  -> `CustomerDeps` is the data (name, email, account_id,
                       plan) every agent can read via `ctx.deps`
- main.py          -> imports `triage_agent` and `CustomerDeps`, then runs
                       a handful of sample customer messages through it
"""