from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.slot_progress_counts import SlotProgressCounts
  from ..models.slot_progress_entry_response import SlotProgressEntryResponse





T = TypeVar("T", bound="SlotProgressResponse")



@_attrs_define
class SlotProgressResponse:
    """ 
        Attributes:
            slot_id (str):
            status (str):
            counts (SlotProgressCounts):
            entries (list[SlotProgressEntryResponse]):
     """

    slot_id: str
    status: str
    counts: SlotProgressCounts
    entries: list[SlotProgressEntryResponse]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.slot_progress_counts import SlotProgressCounts # noqa: PLC0415
        from ..models.slot_progress_entry_response import SlotProgressEntryResponse # noqa: PLC0415
        slot_id = self.slot_id

        status = self.status

        counts = self.counts.to_dict()

        entries = []
        for entries_item_data in self.entries:
            entries_item = entries_item_data.to_dict()
            entries.append(entries_item)




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "slotId": slot_id,
            "status": status,
            "counts": counts,
            "entries": entries,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.slot_progress_counts import SlotProgressCounts # noqa: PLC0415
        from ..models.slot_progress_entry_response import SlotProgressEntryResponse # noqa: PLC0415
        d = dict(src_dict)
        slot_id = d.pop("slotId")

        status = d.pop("status")

        counts = SlotProgressCounts.from_dict(d.pop("counts"))




        entries = []
        _entries = d.pop("entries")
        for entries_item_data in (_entries):
            entries_item = SlotProgressEntryResponse.from_dict(entries_item_data)



            entries.append(entries_item)


        slot_progress_response = cls(
            slot_id=slot_id,
            status=status,
            counts=counts,
            entries=entries,
        )


        slot_progress_response.additional_properties = d
        return slot_progress_response

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
