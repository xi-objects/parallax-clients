from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast






T = TypeVar("T", bound="SequenceAmendExpectedSizeRequest")



@_attrs_define
class SequenceAmendExpectedSizeRequest:
    """ 
        Attributes:
            expected_size (int | str):
     """

    expected_size: int | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        expected_size: int | str
        expected_size = self.expected_size


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "expectedSize": expected_size,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        def _parse_expected_size(data: object) -> int | str:
            return cast(int | str, data)

        expected_size = _parse_expected_size(d.pop("expectedSize"))


        sequence_amend_expected_size_request = cls(
            expected_size=expected_size,
        )


        sequence_amend_expected_size_request.additional_properties = d
        return sequence_amend_expected_size_request

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
