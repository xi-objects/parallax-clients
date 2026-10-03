from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast






T = TypeVar("T", bound="PublishedSequenceVerdict")



@_attrs_define
class PublishedSequenceVerdict:
    """ 
        Attributes:
            connected (bool):
            sealed (bool):
            reach (int | str):
            frames_received (int | str):
     """

    connected: bool
    sealed: bool
    reach: int | str
    frames_received: int | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        connected = self.connected

        sealed = self.sealed

        reach: int | str
        reach = self.reach

        frames_received: int | str
        frames_received = self.frames_received


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "connected": connected,
            "sealed": sealed,
            "reach": reach,
            "framesReceived": frames_received,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        connected = d.pop("connected")

        sealed = d.pop("sealed")

        def _parse_reach(data: object) -> int | str:
            return cast(int | str, data)

        reach = _parse_reach(d.pop("reach"))


        def _parse_frames_received(data: object) -> int | str:
            return cast(int | str, data)

        frames_received = _parse_frames_received(d.pop("framesReceived"))


        published_sequence_verdict = cls(
            connected=connected,
            sealed=sealed,
            reach=reach,
            frames_received=frames_received,
        )


        published_sequence_verdict.additional_properties = d
        return published_sequence_verdict

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
