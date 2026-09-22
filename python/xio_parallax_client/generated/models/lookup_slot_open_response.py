from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
import datetime






T = TypeVar("T", bound="LookupSlotOpenResponse")



@_attrs_define
class LookupSlotOpenResponse:
    """ 
        Attributes:
            lookup_slot_id (str):
            expires_at (datetime.datetime):
     """

    lookup_slot_id: str
    expires_at: datetime.datetime
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        lookup_slot_id = self.lookup_slot_id

        expires_at = self.expires_at.isoformat()


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "lookupSlotId": lookup_slot_id,
            "expiresAt": expires_at,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        lookup_slot_id = d.pop("lookupSlotId")

        expires_at = datetime.datetime.fromisoformat(d.pop("expiresAt"))




        lookup_slot_open_response = cls(
            lookup_slot_id=lookup_slot_id,
            expires_at=expires_at,
        )


        lookup_slot_open_response.additional_properties = d
        return lookup_slot_open_response

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
