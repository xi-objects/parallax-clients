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






T = TypeVar("T", bound="PostSlotsSlotIdUploadsBody")



@_attrs_define
class PostSlotsSlotIdUploadsBody:
    """ 
        Attributes:
            manifestkind (list[str] | Unset): The manifests of the image part that follows. Manifest kind must be 1 to 64
                characters of A-Z, a-z, 0-9, '.', '_' or '-'. The part's own Content-Type gives the manifest's form, with no
                default. One part is bounded by SlotUpload:MaxManifestBytes and one image carries at most
                SlotUpload:MaxManifestsPerImage of them.
            image (list[File] | Unset): One image to register. Its content type must be one of
                SlotUpload:AllowedContentTypes; one image is bounded by SlotUpload:MaxImageBytes and the whole request by
                SlotUpload:MaxRequestBytes.
     """

    manifestkind: list[str] | Unset = UNSET
    image: list[File] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        manifestkind: list[str] | Unset = UNSET
        if not isinstance(self.manifestkind, Unset):
            manifestkind = self.manifestkind



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
        if manifestkind is not UNSET:
            field_dict["manifest[<kind>]"] = manifestkind
        if image is not UNSET:
            field_dict["image"] = image

        return field_dict


    def to_multipart(self) -> types.RequestFiles:
        files: types.RequestFiles = []

        if not isinstance(self.manifestkind, Unset):
            for manifestkind_item_element in self.manifestkind:
                files.append(("manifest[<kind>]", (None, str(manifestkind_item_element).encode(), "text/plain")))




        if not isinstance(self.image, Unset):
            for image_item_element in self.image:
                files.append(("image", image_item_element.to_tuple()))





        for prop_name, prop in self.additional_properties.items():
            files.append((prop_name, (None, str(prop).encode(), "text/plain")))



        return files


    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        manifestkind = cast(list[str], d.pop("manifest[<kind>]", UNSET))


        _image = d.pop("image", UNSET)
        image: list[File] | Unset = UNSET
        if _image is not UNSET:
            image = []
            for image_item_data in _image:
                image_item = File(
                     payload = BytesIO(image_item_data)
                )



                image.append(image_item)


        post_slots_slot_id_uploads_body = cls(
            manifestkind=manifestkind,
            image=image,
        )


        post_slots_slot_id_uploads_body.additional_properties = d
        return post_slots_slot_id_uploads_body

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
