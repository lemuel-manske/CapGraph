from __future__ import annotations

from dataclasses import dataclass
from typing import Generator

from src.utils.json_patch import PatchOperation, apply_patches


@dataclass(frozen=True)
class Diff:
    """A patch to the schematics tree."""

    ops: list[PatchOperation]


@dataclass(frozen=True)
class FetchSchematics:
    """Request to fetch the current schematics tree."""

    ...


@dataclass(frozen=True)
class SaveSchematics:
    """Request to persist the patched schematics tree."""

    data: dict


type PersistenceEvent = FetchSchematics | SaveSchematics


def apply_diffs(
    diffs: list[Diff],
) -> Generator[PersistenceEvent, dict | None]:
    if diffs:
        tree = yield FetchSchematics()

        assert isinstance(tree, dict), "Expected fetched tree to be a dict"

        yield SaveSchematics(data=apply_patches(tree, [op for diff in diffs for op in diff.ops]))
