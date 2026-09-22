from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast






T = TypeVar("T", bound="AccountStatsGrantResponse")



@_attrs_define
class AccountStatsGrantResponse:
    """ 
        Attributes:
            grant (int | str):
            consumed (int | str):
            held (int | str):
            remaining (int | str):
     """

    grant: int | str
    consumed: int | str
    held: int | str
    remaining: int | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        grant: int | str
        grant = self.grant

        consumed: int | str
        consumed = self.consumed

        held: int | str
        held = self.held

        remaining: int | str
        remaining = self.remaining


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "grant": grant,
            "consumed": consumed,
            "held": held,
            "remaining": remaining,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        def _parse_grant(data: object) -> int | str:
            return cast(int | str, data)

        grant = _parse_grant(d.pop("grant"))


        def _parse_consumed(data: object) -> int | str:
            return cast(int | str, data)

        consumed = _parse_consumed(d.pop("consumed"))


        def _parse_held(data: object) -> int | str:
            return cast(int | str, data)

        held = _parse_held(d.pop("held"))


        def _parse_remaining(data: object) -> int | str:
            return cast(int | str, data)

        remaining = _parse_remaining(d.pop("remaining"))


        account_stats_grant_response = cls(
            grant=grant,
            consumed=consumed,
            held=held,
            remaining=remaining,
        )


        account_stats_grant_response.additional_properties = d
        return account_stats_grant_response

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
