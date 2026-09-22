from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from uuid import UUID






T = TypeVar("T", bound="SlotUploadOutcomeResponse")



@_attrs_define
class SlotUploadOutcomeResponse:
    """ 
        Attributes:
            part_index (int | str):
            file_name (None | str):
            accepted (bool):
            image_hash (None | str):
            rejection_reason (None | str):
            registration_remaining (int | None | str):
            lookup_remaining (int | None | str):
            registration_id (None | UUID):
     """

    part_index: int | str
    file_name: None | str
    accepted: bool
    image_hash: None | str
    rejection_reason: None | str
    registration_remaining: int | None | str
    lookup_remaining: int | None | str
    registration_id: None | UUID
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        part_index: int | str
        part_index = self.part_index

        file_name: None | str
        file_name = self.file_name

        accepted = self.accepted

        image_hash: None | str
        image_hash = self.image_hash

        rejection_reason: None | str
        rejection_reason = self.rejection_reason

        registration_remaining: int | None | str
        registration_remaining = self.registration_remaining

        lookup_remaining: int | None | str
        lookup_remaining = self.lookup_remaining

        registration_id: None | str
        if isinstance(self.registration_id, UUID):
            registration_id = str(self.registration_id)
        else:
            registration_id = self.registration_id


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "partIndex": part_index,
            "fileName": file_name,
            "accepted": accepted,
            "imageHash": image_hash,
            "rejectionReason": rejection_reason,
            "registrationRemaining": registration_remaining,
            "lookupRemaining": lookup_remaining,
            "registrationId": registration_id,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        def _parse_part_index(data: object) -> int | str:
            return cast(int | str, data)

        part_index = _parse_part_index(d.pop("partIndex"))


        def _parse_file_name(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        file_name = _parse_file_name(d.pop("fileName"))


        accepted = d.pop("accepted")

        def _parse_image_hash(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        image_hash = _parse_image_hash(d.pop("imageHash"))


        def _parse_rejection_reason(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        rejection_reason = _parse_rejection_reason(d.pop("rejectionReason"))


        def _parse_registration_remaining(data: object) -> int | None | str:
            if data is None:
                return data
            return cast(int | None | str, data)

        registration_remaining = _parse_registration_remaining(d.pop("registrationRemaining"))


        def _parse_lookup_remaining(data: object) -> int | None | str:
            if data is None:
                return data
            return cast(int | None | str, data)

        lookup_remaining = _parse_lookup_remaining(d.pop("lookupRemaining"))


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


        slot_upload_outcome_response = cls(
            part_index=part_index,
            file_name=file_name,
            accepted=accepted,
            image_hash=image_hash,
            rejection_reason=rejection_reason,
            registration_remaining=registration_remaining,
            lookup_remaining=lookup_remaining,
            registration_id=registration_id,
        )


        slot_upload_outcome_response.additional_properties = d
        return slot_upload_outcome_response

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
