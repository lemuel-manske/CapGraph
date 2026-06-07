from copy import deepcopy

from src.engine.api import State
from src.engine.runner import loop
from src.llm.api import ChatMessage
from src.llm.ollama_impl import OllamaChat
from src.sample.domain.api import SchematicsTree
from src.sample.schematics import root as schematics_root
from src.utils.json_patch import apply_patches

ollama = OllamaChat(model="qwen3:4b")

SYSTEM_PROMPT = """
You build Schema-driven UI.

The user provides a natural language prompt and an anchor to the UI.

Your job is to call the right tools to build the UI that matches the user intent.
"""


def run(anchor: str, prompt: str, tree: dict) -> dict:
    history = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="user", content=prompt),
    ]

    schematics_tree = SchematicsTree(deepcopy(tree))
    current_tree = dict(tree)
    committed = 0

    def _commit(state: State) -> None:
        nonlocal current_tree, committed
        for op in list(state.operations)[committed:]:
            if op["op"] == "json_patch":
                current_tree = apply_patches(current_tree, op["patches"])
        committed = len(state.operations)

    for frame in loop(anchor, ollama, schematics_root, history, schematics_tree=schematics_tree):
        _commit(frame.state)

    return current_tree
