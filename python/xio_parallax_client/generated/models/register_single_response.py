from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from uuid import UUID






T = TypeVar("T", bound="RegisterSingleResponse")



@_attrs_define
class RegisterSingleResponse:
    """ 
        Attributes:
            id (UUID):
            image_hash (str):
            original_image_hash (None | str):
            engine_record (str):
     """

    id: UUID
    image_hash: str
    original_image_hash: None | str
    engine_record: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        id = str(self.id)

        image_hash = self.image_hash

        original_image_hash: None | str
        original_image_hash = self.original_image_hash

        engine_record = self.engine_record


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "id": id,
            "imageHash": image_hash,
            "originalImageHash": original_image_hash,
            "engineRecord": engine_record,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = UUID(d.pop("id"))




        image_hash = d.pop("imageHash")

        def _parse_original_image_hash(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        original_image_hash = _parse_original_image_hash(d.pop("originalImageHash"))


        engine_record = d.pop("engineRecord")

        register_single_response = cls(
            id=id,
            image_hash=image_hash,
            original_image_hash=original_image_hash,
            engine_record=engine_record,
        )


        register_single_response.additional_properties = d
        return register_single_response

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
