"""The agents: who holds which tool, and what each is told.

Identifier: reads what is printed and confirms it (RxNorm), parses directions.
Watchman:   checks the safety record (openFDA), live recalls only.
Scribe:     writes the one or two sentences a person reads. Holds no tools.
Coach:      turns a session's numbers into one encouraging line. Holds no tools.
"""
from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel

from . import models, tools


def _model(model_id: str | None = None, temperature: float = 0.1, max_tokens: int = 1200) -> BedrockModel:
    return BedrockModel(model_id=model_id or models.READER_MODEL, region_name=models.REGION,
                        temperature=temperature, max_tokens=max_tokens)


def text_of(result) -> str:
    msg = getattr(result, "message", None)
    if isinstance(msg, dict):
        parts = [b.get("text", "") for b in msg.get("content", []) if "text" in b]
        if parts:
            return "\n".join(parts).strip()
    return str(result).strip()


IDENTIFIER_PROMPT = """\
You work out what the medicine boxes in somebody's kitchen actually are, from
the text printed on them. For each box: call identify_medicine with the printed
name and strength, then call parse_directions with the printed directions.
Never guess a name from a partial word. Report plainly what was confirmed and
what was not. Do not give medical advice of any kind.
"""

WATCHMAN_PROMPT = """\
You check whether an ingredient has a live safety recall. Call check_for_recalls
once per ingredient. A recall is against specific batches, never against a
medicine as such. Never say somebody's medicine has been recalled and never
suggest stopping anything. Report only what is live.
"""

SCRIBE_PROMPT = """\
You are a writing tool. You turn a structured finding into one plain question a
person can read aloud to a pharmacist, or into one or two calm sentences for a
family member. Use only the facts you are given, in their own terms; do not
infer, interpret, soften or add anything (if a fact says "No seated session
today" write that he did not do his seated session, not that he was not in his
usual spot). Leave out any fact you were not given. You give no opinion, no
advice, no reassurance. Output the sentence(s) only. Never use the words
monitor, diagnose, alarm or detect.
"""

COACH_PROMPT = """\
You write one short encouraging line (max 14 words) for a 72-year-old doing a
seated exercise session in front of the television, from the numbers you are
given. Plain words, no exclamation marks, no medical claims, no numbers unless
they were given to you. Output the line only.
"""


def identifier(on_hooks=None) -> Agent:
    return Agent(model=_model(), tools=tools.CLERICAL_TOOLS, system_prompt=IDENTIFIER_PROMPT,
                 callback_handler=None, hooks=on_hooks or [])


def watchman(on_hooks=None) -> Agent:
    return Agent(model=_model(), tools=tools.SAFETY_TOOLS, system_prompt=WATCHMAN_PROMPT,
                 callback_handler=None, hooks=on_hooks or [])


def scribe() -> Agent:
    return Agent(model=_model(models.WRITER_MODEL, temperature=0.3, max_tokens=200), tools=tools.SCRIBE_TOOLS,
                 system_prompt=SCRIBE_PROMPT, callback_handler=None)


def coach() -> Agent:
    return Agent(model=_model(models.WRITER_MODEL, temperature=0.4, max_tokens=60), tools=[],
                 system_prompt=COACH_PROMPT, callback_handler=None)
