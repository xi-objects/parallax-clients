from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field
import json
from .. import types

from ..types import UNSET, Unset

from ..types import File, FileTypes
from ..types import UNSET, Unset
from io import BytesIO
from typing import cast






T = TypeVar("T", bound="PostLookupBody")



@_attrs_define
class PostLookupBody:
    """ 
        Attributes:
            image (list[File] | Unset): The query image. Its part name carries no meaning. Its content type must be one of
                SlotUpload:AllowedContentTypes; one image is bounded by the calling account's maxImageBytes and the whole
                request by its maxRequestBytes, both set by the admin.
     """

    image: list[File] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        image: list[FileTypes] | Unset = UNSET
        if not isinstance(self.image, Unset):
            image = []
            for image_item_data in self.image:
                image_item = image_item_data.to_tuple()

                image.append(image_item)




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
        })
        if image is not UNSET:
            field_dict["image"] = image

        return field_dict


    def to_multipart(self) -> types.RequestFiles:
        files: types.RequestFiles = []

        if not isinstance(self.image, Unset):
            for image_item_element in self.image:
                files.append(("image", image_item_element.to_tuple()))





        for prop_name, prop in self.additional_properties.items():
            files.append((prop_name, (None, str(prop).encode(), "text/plain")))



        return files


    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _image = d.pop("image", UNSET)
        image: list[File] | Unset = UNSET
        if _image is not UNSET:
            image = []
            for image_item_data in _image:
                image_item = File(
                     payload = BytesIO(image_item_data)
                )



                image.append(image_item)


        post_lookup_body = cls(
            image=image,
        )


        post_lookup_body.additional_properties = d
        return post_lookup_body

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
