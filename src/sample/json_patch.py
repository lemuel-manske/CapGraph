from copy import deepcopy
from typing import Literal, TypedDict


type JsonValue = dict | list | str | int | float | bool | None


class JsonPatchException(Exception):
    ...


class AddOperation(TypedDict):
    op: Literal["add"]
    path: str
    value: JsonValue


class ReplaceOperation(TypedDict):
    op: Literal["replace"]
    path: str
    value: JsonValue


class RemoveOperation(TypedDict):
    op: Literal["remove"]
    path: str


class MoveOperation(TypedDict):
    op: Literal["move"]
    path: str
    from_path: str


class CopyOperation(TypedDict):
    op: Literal["copy"]
    path: str
    from_path: str


type PatchOperation = AddOperation | ReplaceOperation | RemoveOperation | MoveOperation | CopyOperation


def patches_equal(patches1: list[PatchOperation], patches2: list[PatchOperation]) -> bool:
    """
    Compares two lists of patch operations for equality, ignoring order.
    """

    def normalize(patches: list[PatchOperation]) -> list[PatchOperation]:
        return sorted(patches, key=lambda p: (p['op'], p['path']))

    return normalize(patches1) == normalize(patches2)


def diff(doc: dict, modified: dict) -> list[PatchOperation]:
    """
    Computes the list of patch operations required to transform doc into modified.
    """

    ops: list[PatchOperation] = []

    def _escape(token: str) -> str:
        return token.replace("~", "~0").replace("/", "~1")

    def walk(old: JsonValue, new: JsonValue, path: str) -> None:
        if isinstance(old, dict) and isinstance(new, dict):
            old_keys = set(old)
            new_keys = set(new)

            for key in sorted(old_keys - new_keys):
                ops.append(
                    RemoveOperation(
                        op="remove",
                        path=f"{path}/{_escape(key)}" if path else f"/{_escape(key)}",
                    )
                )

            for key in sorted(new_keys - old_keys):
                ops.append(
                    AddOperation(
                        op="add",
                        path=f"{path}/{_escape(key)}" if path else f"/{_escape(key)}",
                        value=deepcopy(new[key]),
                    )
                )

            for key in sorted(old_keys & new_keys):
                child_path = (
                    f"{path}/{_escape(key)}" if path else f"/{_escape(key)}"
                )
                walk(old[key], new[key], child_path)

            return

        if isinstance(old, list) and isinstance(new, list):
            if old != new:
                ops.append(
                    ReplaceOperation(
                        op="replace",
                        path=path or "",
                        value=deepcopy(new),
                    )
                )
            return

        if old != new:
            ops.append(
                ReplaceOperation(
                    op="replace",
                    path=path or "",
                    value=deepcopy(new),
                )
            )

    walk(doc, modified, "")

    return ops


def apply_patches(document: dict, patches: list[PatchOperation]) -> dict:
    """
    Applies the given list of patch operations to the document and returns the modified document.
    """

    patcher = JsonPatch(patches)
    return patcher.apply(document)


class JsonPatch:
    """
    Applies dict patches.
    """

    def __init__(self, patches: list[PatchOperation]):
        self.patches = patches

    def apply(self, document: dict) -> dict:
        """
        Applies the patch operations to the given document and returns the modified document.
        """

        doc = deepcopy(document)

        for patch in self.patches:
            op = patch['op']
            path = patch['path']

            if not path and op in ("add", "replace"):
                assert 'value' in patch, "Missing value for add/replace operation"

                doc = deepcopy(patch['value'])
                continue

            if op == "add":
                assert 'value' in patch, "Missing value for add operation"
                self._add(doc, path, patch['value'])

            elif op == "replace":
                assert 'value' in patch, "Missing value for replace operation"
                self._replace(doc, path, patch['value'])

            elif op == "remove":
                self._remove(doc, path)

            elif op == "test":
                assert 'value' in patch, "Missing value for test operation"
                self._test(doc, path, patch['value'])

            elif op == "copy":
                assert 'from_path' in patch, "Missing from_path for copy operation"
                self._copy(doc, patch['from_path'], path)

            elif op == "move":
                assert 'from_path' in patch, "Missing from_path for move operation"
                self._move(doc, patch['from_path'], path)

            else:
                raise JsonPatchException(f"Unsupported op: {op}")

        assert isinstance(doc, dict), "Root document must be a dict"

        return doc

    def _split_path(self, path: str) -> list[str]:
        return [p for p in path.strip("/").split("/") if p]

    def _resolve(self, doc: JsonValue, path: str) -> tuple[JsonValue, str]:
        parts = self._split_path(path)
        current: JsonValue = doc

        for part in parts[:-1]:
            current = self._step(current, part)

        return current, parts[-1]

    def _step(self, current: JsonValue, part: str) -> JsonValue:
        if ":" in part and isinstance(current, list):
            key, expected = part.split(":", 1)

            for item in current:
                if isinstance(item, dict) and str(item.get(key)) == expected:
                    return item

            raise KeyError(f"No match for filter {part}")

        if isinstance(current, list):
            return current[int(part)]

        if isinstance(current, dict):
            return current[part]

        raise TypeError(f"Cannot navigate through {type(current)}")

    def _add(self, doc: JsonValue, path: str, value: JsonValue) -> None:
        parent, key = self._resolve(doc, path)

        if isinstance(parent, list):
            if key == "-":
                parent.append(value)
            else:
                parent.insert(int(key), value)
        elif isinstance(parent, dict):
            parent[key] = value
        else:
            raise TypeError("Invalid target for add")

    def _replace(self, doc: JsonValue, path: str, value: JsonValue) -> None:
        parent, key = self._resolve(doc, path)

        if isinstance(parent, list):
            idx = int(key)
            if idx >= len(parent):
                raise JsonPatchException(f"Replace target does not exist: {path}")
            parent[idx] = value
        elif isinstance(parent, dict):
            if key not in parent:
                raise JsonPatchException(f"Replace target does not exist: {path}")
            parent[key] = value
        else:
            raise JsonPatchException(f"Invalid target for replace: {path}")

    def _remove(self, doc: JsonValue, path: str) -> None:
        parent, key = self._resolve(doc, path)

        if isinstance(parent, list):
            del parent[int(key)]
        elif isinstance(parent, dict):
            del parent[key]
        else:
            raise TypeError("Invalid target for remove")

    def _test(self, doc: JsonValue, path: str, value: JsonValue) -> None:
        current = self._get(doc, path)

        if current != value:
            raise JsonPatchException(f"Test failed at {path}: {current} != {value}")

    def _copy(self, doc: JsonValue, from_path: str, to_path: str) -> None:
        value = self._get(doc, from_path)
        self._add(doc, to_path, deepcopy(value))

    def _move(self, doc: JsonValue, from_path: str, to_path: str) -> None:
        value = self._get(doc, from_path)
        self._remove(doc, from_path)
        self._add(doc, to_path, value)

    def _get(self, doc: JsonValue, path: str) -> JsonValue:
        parent, key = self._resolve(doc, path)

        if isinstance(parent, list):
            return parent[int(key)]
        elif isinstance(parent, dict):
            return parent[key]

        raise TypeError("Invalid target for get")
