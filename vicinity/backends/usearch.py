from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy import typing as npt
from usearch.index import Index as UsearchIndex

from vicinity.backends.base import AbstractBackend, BaseArgs
from vicinity.datatypes import Backend, QueryResult


@dataclass
class UsearchArgs(BaseArgs):
    dim: int = 0
    metric: Literal["cos", "ip", "l2sq", "hamming", "tanimoto"] = "cos"
    connectivity: int = 16
    expansion_add: int = 128
    expansion_search: int = 64


class UsearchBackend(AbstractBackend[UsearchArgs]):
    argument_class = UsearchArgs

    def __init__(
        self,
        index: UsearchIndex,
        arguments: UsearchArgs,
    ) -> None:
        """Initialize the backend using Usearch."""
        super().__init__(arguments)
        self.index = index

    @classmethod
    def from_vectors(
        cls: type[UsearchBackend],
        vectors: npt.NDArray,
        metric: Literal["cos", "ip", "l2sq", "hamming", "tanimoto"],
        connectivity: int,
        expansion_add: int,
        expansion_search: int,
        **kwargs: Any,
    ) -> UsearchBackend:
        """
        Create a new instance from vectors.

        :param vectors: The vectors to index.
        :param metric: The metric to use.
        :param connectivity: The connectivity parameter.
        :param expansion_add: The expansion add parameter.
        :param expansion_search: The expansion search parameter.
        :param **kwargs: Additional keyword arguments.
        :return: A new instance of the backend.
        """
        dim = vectors.shape[1]
        index = UsearchIndex(
            ndim=dim,
            metric=metric,
            connectivity=connectivity,
            expansion_add=expansion_add,
            expansion_search=expansion_search,
        )
        index.add(keys=None, vectors=vectors)  # type: ignore
        arguments = UsearchArgs(
            dim=dim,
            metric=metric,
            connectivity=connectivity,
            expansion_add=expansion_add,
            expansion_search=expansion_search,
        )
        backend = cls(index, arguments=arguments)

        return backend

    @property
    def backend_type(self) -> Backend:
        """The type of the backend."""
        return Backend.USEARCH

    @property
    def dim(self) -> int:
        """Get the dimension of the space."""
        return self.index.ndim

    def __len__(self) -> int:
        """Get the number of vectors."""
        return len(self.index)

    @classmethod
    def load(cls: type[UsearchBackend], base_path: Path) -> UsearchBackend:
        """Load the index from a path."""
        path = Path(base_path) / "index.usearch"
        arguments = UsearchArgs.load(base_path / "arguments.json")
        index = UsearchIndex(
            ndim=arguments.dim,
            metric=arguments.metric,
            connectivity=arguments.connectivity,
            expansion_add=arguments.expansion_add,
            expansion_search=arguments.expansion_search,
        )
        index.load(str(path))
        return cls(index, arguments=arguments)

    def save(self, base_path: Path) -> None:
        """Save the index to a path."""
        path = Path(base_path) / "index.usearch"
        self.index.save(str(path))
        self.arguments.dump(base_path / "arguments.json")

    def query(self, vectors: npt.NDArray, k: int) -> QueryResult:
        """Query the backend and return results as tuples of keys and distances."""
        results = self.index.search(vectors, k)
        keys = np.array(results.keys).reshape(-1, k)
        distances = np.array(results.distances, dtype=np.float32).reshape(-1, k)
        return list(zip(keys, distances))

    def insert(self, vectors: npt.NDArray) -> None:
        """Insert vectors into the backend."""
        self.index.add(None, vectors)  # type: ignore

    def delete(self, indices: list[int]) -> None:
        """Delete vectors from the index (not supported by usearch)."""
        raise NotImplementedError("Dynamic deletion is not supported by usearch.")

    def threshold(self, vectors: npt.NDArray, threshold: float) -> list[npt.NDArray]:
        """Threshold the backend and return filtered keys."""
        return [
            np.array(keys_row)[np.array(distances_row, dtype=np.float32) < threshold]
            for keys_row, distances_row in self.query(vectors, 100)
        ]