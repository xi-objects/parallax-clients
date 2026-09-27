from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from uuid import UUID
import datetime






T = TypeVar("T", bound="AccountResponse")



@_attrs_define
class AccountResponse:
    """ 
        Attributes:
            id (UUID):
            name (str):
            status (str):
            registration_grant (int | str):
            lookup_grant (int | str):
            registration_slot_idle_ttl (str):
            registration_slot_absolute_ttl (str):
            max_open_registration_slots (int | str):
            lookup_slot_idle_ttl (str):
            lookup_slot_absolute_ttl (str):
            max_open_lookup_slots (int | str):
            max_image_bytes (int | str):
            max_request_bytes (int | str):
            max_query_images_per_lookup_slot (int | str):
            max_query_images_per_lookup_request (int | str):
            max_frames_per_sequence (int | str): Not enforced yet (S17).
            max_open_sequences (int | str): Not enforced yet (S17).
            sequence_idle_ttl (str): Not enforced yet (S17).
            sequence_absolute_ttl (str): Not enforced yet (S17).
            max_frame_bytes (int | str): Not enforced yet (S17).
            accepted_upload_rate (int | str): Not enforced yet (S17).
            in_flight_allowance (int | str): Not enforced yet (S17).
            sequences_enabled (bool):
            created_at (datetime.datetime):
     """

    id: UUID
    name: str
    status: str
    registration_grant: int | str
    lookup_grant: int | str
    registration_slot_idle_ttl: str
    registration_slot_absolute_ttl: str
    max_open_registration_slots: int | str
    lookup_slot_idle_ttl: str
    lookup_slot_absolute_ttl: str
    max_open_lookup_slots: int | str
    max_image_bytes: int | str
    max_request_bytes: int | str
    max_query_images_per_lookup_slot: int | str
    max_query_images_per_lookup_request: int | str
    max_frames_per_sequence: int | str
    max_open_sequences: int | str
    sequence_idle_ttl: str
    sequence_absolute_ttl: str
    max_frame_bytes: int | str
    accepted_upload_rate: int | str
    in_flight_allowance: int | str
    sequences_enabled: bool
    created_at: datetime.datetime
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        id = str(self.id)

        name = self.name

        status = self.status

        registration_grant: int | str
        registration_grant = self.registration_grant

        lookup_grant: int | str
        lookup_grant = self.lookup_grant

        registration_slot_idle_ttl = self.registration_slot_idle_ttl

        registration_slot_absolute_ttl = self.registration_slot_absolute_ttl

        max_open_registration_slots: int | str
        max_open_registration_slots = self.max_open_registration_slots

        lookup_slot_idle_ttl = self.lookup_slot_idle_ttl

        lookup_slot_absolute_ttl = self.lookup_slot_absolute_ttl

        max_open_lookup_slots: int | str
        max_open_lookup_slots = self.max_open_lookup_slots

        max_image_bytes: int | str
        max_image_bytes = self.max_image_bytes

        max_request_bytes: int | str
        max_request_bytes = self.max_request_bytes

        max_query_images_per_lookup_slot: int | str
        max_query_images_per_lookup_slot = self.max_query_images_per_lookup_slot

        max_query_images_per_lookup_request: int | str
        max_query_images_per_lookup_request = self.max_query_images_per_lookup_request

        max_frames_per_sequence: int | str
        max_frames_per_sequence = self.max_frames_per_sequence

        max_open_sequences: int | str
        max_open_sequences = self.max_open_sequences

        sequence_idle_ttl = self.sequence_idle_ttl

        sequence_absolute_ttl = self.sequence_absolute_ttl

        max_frame_bytes: int | str
        max_frame_bytes = self.max_frame_bytes

        accepted_upload_rate: int | str
        accepted_upload_rate = self.accepted_upload_rate

        in_flight_allowance: int | str
        in_flight_allowance = self.in_flight_allowance

        sequences_enabled = self.sequences_enabled

        created_at = self.created_at.isoformat()


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "id": id,
            "name": name,
            "status": status,
            "registrationGrant": registration_grant,
            "lookupGrant": lookup_grant,
            "registrationSlotIdleTtl": registration_slot_idle_ttl,
            "registrationSlotAbsoluteTtl": registration_slot_absolute_ttl,
            "maxOpenRegistrationSlots": max_open_registration_slots,
            "lookupSlotIdleTtl": lookup_slot_idle_ttl,
            "lookupSlotAbsoluteTtl": lookup_slot_absolute_ttl,
            "maxOpenLookupSlots": max_open_lookup_slots,
            "maxImageBytes": max_image_bytes,
            "maxRequestBytes": max_request_bytes,
            "maxQueryImagesPerLookupSlot": max_query_images_per_lookup_slot,
            "maxQueryImagesPerLookupRequest": max_query_images_per_lookup_request,
            "maxFramesPerSequence": max_frames_per_sequence,
            "maxOpenSequences": max_open_sequences,
            "sequenceIdleTtl": sequence_idle_ttl,
            "sequenceAbsoluteTtl": sequence_absolute_ttl,
            "maxFrameBytes": max_frame_bytes,
            "acceptedUploadRate": accepted_upload_rate,
            "inFlightAllowance": in_flight_allowance,
            "sequencesEnabled": sequences_enabled,
            "createdAt": created_at,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = UUID(d.pop("id"))




        name = d.pop("name")

        status = d.pop("status")

        def _parse_registration_grant(data: object) -> int | str:
            return cast(int | str, data)

        registration_grant = _parse_registration_grant(d.pop("registrationGrant"))


        def _parse_lookup_grant(data: object) -> int | str:
            return cast(int | str, data)

        lookup_grant = _parse_lookup_grant(d.pop("lookupGrant"))


        registration_slot_idle_ttl = d.pop("registrationSlotIdleTtl")

        registration_slot_absolute_ttl = d.pop("registrationSlotAbsoluteTtl")

        def _parse_max_open_registration_slots(data: object) -> int | str:
            return cast(int | str, data)

        max_open_registration_slots = _parse_max_open_registration_slots(d.pop("maxOpenRegistrationSlots"))


        lookup_slot_idle_ttl = d.pop("lookupSlotIdleTtl")

        lookup_slot_absolute_ttl = d.pop("lookupSlotAbsoluteTtl")

        def _parse_max_open_lookup_slots(data: object) -> int | str:
            return cast(int | str, data)

        max_open_lookup_slots = _parse_max_open_lookup_slots(d.pop("maxOpenLookupSlots"))


        def _parse_max_image_bytes(data: object) -> int | str:
            return cast(int | str, data)

        max_image_bytes = _parse_max_image_bytes(d.pop("maxImageBytes"))


        def _parse_max_request_bytes(data: object) -> int | str:
            return cast(int | str, data)

        max_request_bytes = _parse_max_request_bytes(d.pop("maxRequestBytes"))


        def _parse_max_query_images_per_lookup_slot(data: object) -> int | str:
            return cast(int | str, data)

        max_query_images_per_lookup_slot = _parse_max_query_images_per_lookup_slot(d.pop("maxQueryImagesPerLookupSlot"))


        def _parse_max_query_images_per_lookup_request(data: object) -> int | str:
            return cast(int | str, data)

        max_query_images_per_lookup_request = _parse_max_query_images_per_lookup_request(d.pop("maxQueryImagesPerLookupRequest"))


        def _parse_max_frames_per_sequence(data: object) -> int | str:
            return cast(int | str, data)

        max_frames_per_sequence = _parse_max_frames_per_sequence(d.pop("maxFramesPerSequence"))


        def _parse_max_open_sequences(data: object) -> int | str:
            return cast(int | str, data)

        max_open_sequences = _parse_max_open_sequences(d.pop("maxOpenSequences"))


        sequence_idle_ttl = d.pop("sequenceIdleTtl")

        sequence_absolute_ttl = d.pop("sequenceAbsoluteTtl")

        def _parse_max_frame_bytes(data: object) -> int | str:
            return cast(int | str, data)

        max_frame_bytes = _parse_max_frame_bytes(d.pop("maxFrameBytes"))


        def _parse_accepted_upload_rate(data: object) -> int | str:
            return cast(int | str, data)

        accepted_upload_rate = _parse_accepted_upload_rate(d.pop("acceptedUploadRate"))


        def _parse_in_flight_allowance(data: object) -> int | str:
            return cast(int | str, data)

        in_flight_allowance = _parse_in_flight_allowance(d.pop("inFlightAllowance"))


        sequences_enabled = d.pop("sequencesEnabled")

        created_at = datetime.datetime.fromisoformat(d.pop("createdAt"))




        account_response = cls(
            id=id,
            name=name,
            status=status,
            registration_grant=registration_grant,
            lookup_grant=lookup_grant,
            registration_slot_idle_ttl=registration_slot_idle_ttl,
            registration_slot_absolute_ttl=registration_slot_absolute_ttl,
            max_open_registration_slots=max_open_registration_slots,
            lookup_slot_idle_ttl=lookup_slot_idle_ttl,
            lookup_slot_absolute_ttl=lookup_slot_absolute_ttl,
            max_open_lookup_slots=max_open_lookup_slots,
            max_image_bytes=max_image_bytes,
            max_request_bytes=max_request_bytes,
            max_query_images_per_lookup_slot=max_query_images_per_lookup_slot,
            max_query_images_per_lookup_request=max_query_images_per_lookup_request,
            max_frames_per_sequence=max_frames_per_sequence,
            max_open_sequences=max_open_sequences,
            sequence_idle_ttl=sequence_idle_ttl,
            sequence_absolute_ttl=sequence_absolute_ttl,
            max_frame_bytes=max_frame_bytes,
            accepted_upload_rate=accepted_upload_rate,
            in_flight_allowance=in_flight_allowance,
            sequences_enabled=sequences_enabled,
            created_at=created_at,
        )


        account_response.additional_properties = d
        return account_response

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
