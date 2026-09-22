from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
import datetime






T = TypeVar("T", bound="SlotResponse")



@_attrs_define
class SlotResponse:
    """ 
        Attributes:
            slot_id (str):
            status (str):
            entry_count (int | str):
            opened_at (datetime.datetime):
            expires_at (datetime.datetime):
     """

    slot_id: str
    status: str
    entry_count: int | str
    opened_at: datetime.datetime
    expires_at: datetime.datetime
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        slot_id = self.slot_id

        status = self.status

        entry_count: int | str
        entry_count = self.entry_count

        opened_at = self.opened_at.isoformat()

        expires_at = self.expires_at.isoformat()


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "slotId": slot_id,
            "status": status,
            "entryCount": entry_count,
            "openedAt": opened_at,
            "expiresAt": expires_at,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        slot_id = d.pop("slotId")

        status = d.pop("status")

        def _parse_entry_count(data: object) -> int | str:
            return cast(int | str, data)

        entry_count = _parse_entry_count(d.pop("entryCount"))


        opened_at = datetime.datetime.fromisoformat(d.pop("openedAt"))




        expires_at = datetime.datetime.fromisoformat(d.pop("expiresAt"))




        slot_response = cls(
            slot_id=slot_id,
            status=status,
            entry_count=entry_count,
            opened_at=opened_at,
            expires_at=expires_at,
        )


        slot_response.additional_properties = d
        return slot_response

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
