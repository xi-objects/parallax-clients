from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from uuid import UUID






T = TypeVar("T", bound="SequenceOpenResponse")



@_attrs_define
class SequenceOpenResponse:
    """ 
        Attributes:
            sequence_id (UUID):
            head_frame (str):
            ticket (str):
     """

    sequence_id: UUID
    head_frame: str
    ticket: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        sequence_id = str(self.sequence_id)

        head_frame = self.head_frame

        ticket = self.ticket


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "sequenceId": sequence_id,
            "headFrame": head_frame,
            "ticket": ticket,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        sequence_id = UUID(d.pop("sequenceId"))




        head_frame = d.pop("headFrame")

        ticket = d.pop("ticket")

        sequence_open_response = cls(
            sequence_id=sequence_id,
            head_frame=head_frame,
            ticket=ticket,
        )


        sequence_open_response.additional_properties = d
        return sequence_open_response

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
