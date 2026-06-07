import networkx as nx

from src.engine.api import Capability
from src.sample.tools import DEFINITIONS


# form (node)
# field (node)
# add_field (edge) - is a capability

# root - add_form -> form
# form - add_field -> field

class Schematics:

    def __init__(self, g: nx.DiGraph | None = None, curr_node: str = 'root') -> None:
        def root():
            root = nx.DiGraph()
            root.add_node('root')
            return root

        self._g = g or root()
        self._curr_node = curr_node

    def explore(self, node: str) -> Schematics:
        '''
        Explores the current schematics, and navigates to the target node, exposing a new set
        of capabilities.
        '''

        explored = nx.DiGraph()

        def dfs(n: str) -> None:
            explored.add_node(n)

            for _, to_node, d in self._g.edges(n, data=True):
                explored.add_edge(n, to_node, **d)
                dfs(to_node)

        dfs(node)
        return Schematics(explored, node)

    def capabilities(self) -> list[str]:
        '''
        Returns only the capabilities that expand from the current node.
        '''

        return [d['capability'] for _, _, d in self._g.edges(self._curr_node, data=True)]

    def _add_edge(self, from_node: str, to_node: str, capability: Capability) -> None:
        self._g.add_edge(from_node, to_node, capability=capability.name)

    def _add_node(self, s: str) -> None:
        self._g.add_node(s)


def _build_graph() -> Schematics:
    graph = Schematics()

    for d in DEFINITIONS:
        needs = d.needs
        produces = d.produces

        for need in needs:
            graph._add_node(need)

        for produce in produces:
            graph._add_node(produce)

        for need in needs:
            for produce in produces:
                graph._add_edge(need, produce, d)

    return graph


root = _build_graph()
