from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.slot_upload_outcome_response import SlotUploadOutcomeResponse





T = TypeVar("T", bound="SlotUploadResponse")



@_attrs_define
class SlotUploadResponse:
    """ 
        Attributes:
            outcomes (list[SlotUploadOutcomeResponse]):
     """

    outcomes: list[SlotUploadOutcomeResponse]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.slot_upload_outcome_response import SlotUploadOutcomeResponse # noqa: PLC0415
        outcomes = []
        for outcomes_item_data in self.outcomes:
            outcomes_item = outcomes_item_data.to_dict()
            outcomes.append(outcomes_item)




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "outcomes": outcomes,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.slot_upload_outcome_response import SlotUploadOutcomeResponse # noqa: PLC0415
        d = dict(src_dict)
        outcomes = []
        _outcomes = d.pop("outcomes")
        for outcomes_item_data in (_outcomes):
            outcomes_item = SlotUploadOutcomeResponse.from_dict(outcomes_item_data)



            outcomes.append(outcomes_item)


        slot_upload_response = cls(
            outcomes=outcomes,
        )


        slot_upload_response.additional_properties = d
        return slot_upload_response

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
