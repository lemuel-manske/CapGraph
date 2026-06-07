from typing import Iterable

from src.utils.json_patch import PatchOperation


class SchematicsTree(dict):
    """
    A class representing a tree structure for the schematics of the UI.
    """

    def __init__(self, *args, id_key: str = "id", gen_key: str = "children", **kwargs):
        super().__init__(*args, **kwargs)

        self._id_key = id_key
        self._gen_key = gen_key

    def add(self, node_id: str, new: dict) -> list[PatchOperation]:
        """
        Add a new node with the given ID and data to the tree,
        and return a list of patch operations to apply the change.
        """

        parent = self.at(node_id)

        if parent is None:
            raise ValueError(f"Node with id {node_id} not found in schematics tree.")

        if self._gen_key not in parent:
            parent[self._gen_key] = []

        parent[self._gen_key].append(new)

        path = self.path_to(node_id)

        assert path is not None, f"Failed to find path to parent node with id {node_id}."

        new[self._id_key] = self.next_id()

        children_path = f"{path}/{self._gen_key}/-" if path else f"/{self._gen_key}/-"

        op: PatchOperation = {
            "op": "add",
            "path": children_path,
            "value": new,
        }

        return [op]

    def at(self, target_id: str) -> SchematicsTree | None:
        """
        Return the node with the given ID, or None if it doesn't exist.
        """

        if self.get(self._id_key) == target_id:
            return self

        for child in self.children_iter():
            result = child.at(target_id)

            if result is not None:
                return result

        return None

    def children_iter(self) -> Iterable[SchematicsTree]:
        """
        Return an iterator over the child nodes of this node.
        """

        for child in self.get(self._gen_key, []):
            yield SchematicsTree(child)

    def path_to(self, target_id: str) -> str | None:
        """
        Return the JSON pointer path to the component with the given ID.
        """

        if self.get(self._id_key) == target_id:
            return ""

        for i, child in enumerate(self.children_iter()):
            child_path = child.path_to(target_id)

            if child_path is not None:
                return f"/{self._gen_key}/{i}{child_path}"

        return None

    def next_id(self) -> str:
        """
        Generate a new unique ID for a node in the tree.
        """

        existing_ids = set()

        def collect_ids(node: SchematicsTree):
            existing_ids.add(node.get(self._id_key))

            for child in node.children_iter():
                collect_ids(child)

        collect_ids(self)

        i = 1
        while True:
            new_id = f"node_{i}"

            if new_id not in existing_ids:
                return new_id

            i += 1
