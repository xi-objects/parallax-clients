from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
import datetime






T = TypeVar("T", bound="SlotManifestEntryResponse")



@_attrs_define
class SlotManifestEntryResponse:
    """ 
        Attributes:
            image_hash (str):
            manifests_hash (None | str):
            byte_length (int | str):
            content_type (None | str):
            created_at (datetime.datetime):
            state (str):
            not_registered_reason (None | str):
     """

    image_hash: str
    manifests_hash: None | str
    byte_length: int | str
    content_type: None | str
    created_at: datetime.datetime
    state: str
    not_registered_reason: None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        image_hash = self.image_hash

        manifests_hash: None | str
        manifests_hash = self.manifests_hash

        byte_length: int | str
        byte_length = self.byte_length

        content_type: None | str
        content_type = self.content_type

        created_at = self.created_at.isoformat()

        state = self.state

        not_registered_reason: None | str
        not_registered_reason = self.not_registered_reason


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "imageHash": image_hash,
            "manifestsHash": manifests_hash,
            "byteLength": byte_length,
            "contentType": content_type,
            "createdAt": created_at,
            "state": state,
            "notRegisteredReason": not_registered_reason,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        image_hash = d.pop("imageHash")

        def _parse_manifests_hash(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        manifests_hash = _parse_manifests_hash(d.pop("manifestsHash"))


        def _parse_byte_length(data: object) -> int | str:
            return cast(int | str, data)

        byte_length = _parse_byte_length(d.pop("byteLength"))


        def _parse_content_type(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        content_type = _parse_content_type(d.pop("contentType"))


        created_at = datetime.datetime.fromisoformat(d.pop("createdAt"))




        state = d.pop("state")

        def _parse_not_registered_reason(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        not_registered_reason = _parse_not_registered_reason(d.pop("notRegisteredReason"))


        slot_manifest_entry_response = cls(
            image_hash=image_hash,
            manifests_hash=manifests_hash,
            byte_length=byte_length,
            content_type=content_type,
            created_at=created_at,
            state=state,
            not_registered_reason=not_registered_reason,
        )


        slot_manifest_entry_response.additional_properties = d
        return slot_manifest_entry_response

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
