from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast






T = TypeVar("T", bound="PublishedFrameMembership")



@_attrs_define
class PublishedFrameMembership:
    """ 
        Attributes:
            sequence_hash (str):
            frame_id (int | str):
            frame_hash (str):
     """

    sequence_hash: str
    frame_id: int | str
    frame_hash: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        sequence_hash = self.sequence_hash

        frame_id: int | str
        frame_id = self.frame_id

        frame_hash = self.frame_hash


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "sequenceHash": sequence_hash,
            "frameId": frame_id,
            "frameHash": frame_hash,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        sequence_hash = d.pop("sequenceHash")

        def _parse_frame_id(data: object) -> int | str:
            return cast(int | str, data)

        frame_id = _parse_frame_id(d.pop("frameId"))


        frame_hash = d.pop("frameHash")

        published_frame_membership = cls(
            sequence_hash=sequence_hash,
            frame_id=frame_id,
            frame_hash=frame_hash,
        )


        published_frame_membership.additional_properties = d
        return published_frame_membership

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
