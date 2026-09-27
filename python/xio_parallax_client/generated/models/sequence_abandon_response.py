from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from uuid import UUID






T = TypeVar("T", bound="SequenceAbandonResponse")



@_attrs_define
class SequenceAbandonResponse:
    """ 
        Attributes:
            sequence_id (UUID):
            state (str):
            packets_purged (int | str):
     """

    sequence_id: UUID
    state: str
    packets_purged: int | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        sequence_id = str(self.sequence_id)

        state = self.state

        packets_purged: int | str
        packets_purged = self.packets_purged


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "sequenceId": sequence_id,
            "state": state,
            "packetsPurged": packets_purged,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        sequence_id = UUID(d.pop("sequenceId"))




        state = d.pop("state")

        def _parse_packets_purged(data: object) -> int | str:
            return cast(int | str, data)

        packets_purged = _parse_packets_purged(d.pop("packetsPurged"))


        sequence_abandon_response = cls(
            sequence_id=sequence_id,
            state=state,
            packets_purged=packets_purged,
        )


        sequence_abandon_response.additional_properties = d
        return sequence_abandon_response

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
