from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast






T = TypeVar("T", bound="CreateAccountRequest")



@_attrs_define
class CreateAccountRequest:
    """ 
        Attributes:
            name (str):
            registration_grant (int | str):
            lookup_grant (int | str):
     """

    name: str
    registration_grant: int | str
    lookup_grant: int | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        name = self.name

        registration_grant: int | str
        registration_grant = self.registration_grant

        lookup_grant: int | str
        lookup_grant = self.lookup_grant


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "name": name,
            "registrationGrant": registration_grant,
            "lookupGrant": lookup_grant,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        def _parse_registration_grant(data: object) -> int | str:
            return cast(int | str, data)

        registration_grant = _parse_registration_grant(d.pop("registrationGrant"))


        def _parse_lookup_grant(data: object) -> int | str:
            return cast(int | str, data)

        lookup_grant = _parse_lookup_grant(d.pop("lookupGrant"))


        create_account_request = cls(
            name=name,
            registration_grant=registration_grant,
            lookup_grant=lookup_grant,
        )


        create_account_request.additional_properties = d
        return create_account_request

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
