from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.published_record_response_manifests_type_1_item_form import PublishedRecordResponseManifestsType1ItemForm
from ..types import UNSET, Unset
from typing import cast






T = TypeVar("T", bound="PublishedRecordResponseManifestsType1Item")



@_attrs_define
class PublishedRecordResponseManifestsType1Item:
    """ One manifest off a published record, with the hash and the signature that record declares over it.

        Attributes:
            type_ (str): The manifest kind exactly as the caller stated it on its part name; validated against no registry.
            form (PublishedRecordResponseManifestsType1ItemForm): The form the payload is carried in, taken from the part's
                own Content-Type at upload.
            payload (Any): The payload's own bytes: the JSON object inline and verbatim for form "json", base64 text for
                form "jumbf".
            hash_ (None | str | Unset): The record's BLAKE3-256 hash over this manifest's STORED bytes, lowercase hex; null
                on a record that declares none.
            signature (None | str | Unset): This manifest's own signature by the registrant's leaf key, base64; null on a
                record that declares none.
     """

    type_: str
    form: PublishedRecordResponseManifestsType1ItemForm
    payload: Any
    hash_: None | str | Unset = UNSET
    signature: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_

        form = self.form.value

        payload = self.payload

        hash_: None | str | Unset
        if isinstance(self.hash_, Unset):
            hash_ = UNSET
        else:
            hash_ = self.hash_

        signature: None | str | Unset
        if isinstance(self.signature, Unset):
            signature = UNSET
        else:
            signature = self.signature


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "type": type_,
            "form": form,
            "payload": payload,
        })
        if hash_ is not UNSET:
            field_dict["hash"] = hash_
        if signature is not UNSET:
            field_dict["signature"] = signature

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = d.pop("type")

        form = PublishedRecordResponseManifestsType1ItemForm(d.pop("form"))




        payload = d.pop("payload")

        def _parse_hash_(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        hash_ = _parse_hash_(d.pop("hash", UNSET))


        def _parse_signature(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        signature = _parse_signature(d.pop("signature", UNSET))


        published_record_response_manifests_type_1_item = cls(
            type_=type_,
            form=form,
            payload=payload,
            hash_=hash_,
            signature=signature,
        )


        published_record_response_manifests_type_1_item.additional_properties = d
        return published_record_response_manifests_type_1_item

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
