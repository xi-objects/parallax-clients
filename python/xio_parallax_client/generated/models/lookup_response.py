from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.lookup_candidate import LookupCandidate





T = TypeVar("T", bound="LookupResponse")



@_attrs_define
class LookupResponse:
    """ 
        Attributes:
            matched (bool):
            matched_original_image_hashes (list[str]):
            candidates (list[LookupCandidate]):
     """

    matched: bool
    matched_original_image_hashes: list[str]
    candidates: list[LookupCandidate]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.lookup_candidate import LookupCandidate # noqa: PLC0415
        matched = self.matched

        matched_original_image_hashes = self.matched_original_image_hashes



        candidates = []
        for candidates_item_data in self.candidates:
            candidates_item = candidates_item_data.to_dict()
            candidates.append(candidates_item)




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "matched": matched,
            "matchedOriginalImageHashes": matched_original_image_hashes,
            "candidates": candidates,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.lookup_candidate import LookupCandidate # noqa: PLC0415
        d = dict(src_dict)
        matched = d.pop("matched")

        matched_original_image_hashes = cast(list[str], d.pop("matchedOriginalImageHashes"))


        candidates = []
        _candidates = d.pop("candidates")
        for candidates_item_data in (_candidates):
            candidates_item = LookupCandidate.from_dict(candidates_item_data)



            candidates.append(candidates_item)


        lookup_response = cls(
            matched=matched,
            matched_original_image_hashes=matched_original_image_hashes,
            candidates=candidates,
        )


        lookup_response.additional_properties = d
        return lookup_response

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
