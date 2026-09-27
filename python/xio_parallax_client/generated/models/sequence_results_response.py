from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
import datetime






T = TypeVar("T", bound="SequenceResultsResponse")



@_attrs_define
class SequenceResultsResponse:
    """ 
        Attributes:
            sequence_hash (str):
            outcome (str):
            final_size (int | str):
            committed_at (datetime.datetime):
     """

    sequence_hash: str
    outcome: str
    final_size: int | str
    committed_at: datetime.datetime
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        sequence_hash = self.sequence_hash

        outcome = self.outcome

        final_size: int | str
        final_size = self.final_size

        committed_at = self.committed_at.isoformat()


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "sequenceHash": sequence_hash,
            "outcome": outcome,
            "finalSize": final_size,
            "committedAt": committed_at,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        sequence_hash = d.pop("sequenceHash")

        outcome = d.pop("outcome")

        def _parse_final_size(data: object) -> int | str:
            return cast(int | str, data)

        final_size = _parse_final_size(d.pop("finalSize"))


        committed_at = datetime.datetime.fromisoformat(d.pop("committedAt"))




        sequence_results_response = cls(
            sequence_hash=sequence_hash,
            outcome=outcome,
            final_size=final_size,
            committed_at=committed_at,
        )


        sequence_results_response.additional_properties = d
        return sequence_results_response

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
