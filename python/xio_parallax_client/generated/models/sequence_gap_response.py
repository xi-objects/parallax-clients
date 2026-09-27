from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast






T = TypeVar("T", bound="SequenceGapResponse")



@_attrs_define
class SequenceGapResponse:
    """ 
        Attributes:
            from_ (int | str):
            to (int | str):
            gap_frame (str):
     """

    from_: int | str
    to: int | str
    gap_frame: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from_: int | str
        from_ = self.from_

        to: int | str
        to = self.to

        gap_frame = self.gap_frame


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "from": from_,
            "to": to,
            "gapFrame": gap_frame,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        def _parse_from_(data: object) -> int | str:
            return cast(int | str, data)

        from_ = _parse_from_(d.pop("from"))


        def _parse_to(data: object) -> int | str:
            return cast(int | str, data)

        to = _parse_to(d.pop("to"))


        gap_frame = d.pop("gapFrame")

        sequence_gap_response = cls(
            from_=from_,
            to=to,
            gap_frame=gap_frame,
        )


        sequence_gap_response.additional_properties = d
        return sequence_gap_response

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
