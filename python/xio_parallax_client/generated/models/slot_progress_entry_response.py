from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from uuid import UUID






T = TypeVar("T", bound="SlotProgressEntryResponse")



@_attrs_define
class SlotProgressEntryResponse:
    """ 
        Attributes:
            image_hash (str):
            state (str):
            registration_id (None | UUID):
            failure_reason (None | str):
     """

    image_hash: str
    state: str
    registration_id: None | UUID
    failure_reason: None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        image_hash = self.image_hash

        state = self.state

        registration_id: None | str
        if isinstance(self.registration_id, UUID):
            registration_id = str(self.registration_id)
        else:
            registration_id = self.registration_id

        failure_reason: None | str
        failure_reason = self.failure_reason


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "imageHash": image_hash,
            "state": state,
            "registrationId": registration_id,
            "failureReason": failure_reason,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        image_hash = d.pop("imageHash")

        state = d.pop("state")

        def _parse_registration_id(data: object) -> None | UUID:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                registration_id_type_1 = UUID(data)



                return registration_id_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | UUID, data)

        registration_id = _parse_registration_id(d.pop("registrationId"))


        def _parse_failure_reason(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        failure_reason = _parse_failure_reason(d.pop("failureReason"))


        slot_progress_entry_response = cls(
            image_hash=image_hash,
            state=state,
            registration_id=registration_id,
            failure_reason=failure_reason,
        )


        slot_progress_entry_response.additional_properties = d
        return slot_progress_entry_response

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
