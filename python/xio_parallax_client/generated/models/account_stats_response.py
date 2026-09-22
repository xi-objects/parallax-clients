from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.account_stats_grant_response import AccountStatsGrantResponse





T = TypeVar("T", bound="AccountStatsResponse")



@_attrs_define
class AccountStatsResponse:
    """ 
        Attributes:
            registrations (AccountStatsGrantResponse):
            lookups (AccountStatsGrantResponse):
            call_count (int | str):
     """

    registrations: AccountStatsGrantResponse
    lookups: AccountStatsGrantResponse
    call_count: int | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.account_stats_grant_response import AccountStatsGrantResponse # noqa: PLC0415
        registrations = self.registrations.to_dict()

        lookups = self.lookups.to_dict()

        call_count: int | str
        call_count = self.call_count


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "registrations": registrations,
            "lookups": lookups,
            "callCount": call_count,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.account_stats_grant_response import AccountStatsGrantResponse # noqa: PLC0415
        d = dict(src_dict)
        registrations = AccountStatsGrantResponse.from_dict(d.pop("registrations"))




        lookups = AccountStatsGrantResponse.from_dict(d.pop("lookups"))




        def _parse_call_count(data: object) -> int | str:
            return cast(int | str, data)

        call_count = _parse_call_count(d.pop("callCount"))


        account_stats_response = cls(
            registrations=registrations,
            lookups=lookups,
            call_count=call_count,
        )


        account_stats_response.additional_properties = d
        return account_stats_response

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
