from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast

if TYPE_CHECKING:
  from ..models.published_sequence_frame import PublishedSequenceFrame
  from ..models.published_sequence_verdict import PublishedSequenceVerdict





T = TypeVar("T", bound="PublishedSequence")



@_attrs_define
class PublishedSequence:
    """ 
        Attributes:
            expected_size (int | None | str):
            final_size (int | str):
            verdict (PublishedSequenceVerdict):
            frames (list[PublishedSequenceFrame]):
            summary_preimage_version (int | None | str | Unset):
            summary_signature (None | str | Unset):
     """

    expected_size: int | None | str
    final_size: int | str
    verdict: PublishedSequenceVerdict
    frames: list[PublishedSequenceFrame]
    summary_preimage_version: int | None | str | Unset = UNSET
    summary_signature: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.published_sequence_frame import PublishedSequenceFrame # noqa: PLC0415
        from ..models.published_sequence_verdict import PublishedSequenceVerdict # noqa: PLC0415
        expected_size: int | None | str
        expected_size = self.expected_size

        final_size: int | str
        final_size = self.final_size

        verdict = self.verdict.to_dict()

        frames = []
        for frames_item_data in self.frames:
            frames_item = frames_item_data.to_dict()
            frames.append(frames_item)



        summary_preimage_version: int | None | str | Unset
        if isinstance(self.summary_preimage_version, Unset):
            summary_preimage_version = UNSET
        else:
            summary_preimage_version = self.summary_preimage_version

        summary_signature: None | str | Unset
        if isinstance(self.summary_signature, Unset):
            summary_signature = UNSET
        else:
            summary_signature = self.summary_signature


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "expectedSize": expected_size,
            "finalSize": final_size,
            "verdict": verdict,
            "frames": frames,
        })
        if summary_preimage_version is not UNSET:
            field_dict["summaryPreimageVersion"] = summary_preimage_version
        if summary_signature is not UNSET:
            field_dict["summarySignature"] = summary_signature

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.published_sequence_frame import PublishedSequenceFrame # noqa: PLC0415
        from ..models.published_sequence_verdict import PublishedSequenceVerdict # noqa: PLC0415
        d = dict(src_dict)
        def _parse_expected_size(data: object) -> int | None | str:
            if data is None:
                return data
            return cast(int | None | str, data)

        expected_size = _parse_expected_size(d.pop("expectedSize"))


        def _parse_final_size(data: object) -> int | str:
            return cast(int | str, data)

        final_size = _parse_final_size(d.pop("finalSize"))


        verdict = PublishedSequenceVerdict.from_dict(d.pop("verdict"))




        frames = []
        _frames = d.pop("frames")
        for frames_item_data in (_frames):
            frames_item = PublishedSequenceFrame.from_dict(frames_item_data)



            frames.append(frames_item)


        def _parse_summary_preimage_version(data: object) -> int | None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | str | Unset, data)

        summary_preimage_version = _parse_summary_preimage_version(d.pop("summaryPreimageVersion", UNSET))


        def _parse_summary_signature(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        summary_signature = _parse_summary_signature(d.pop("summarySignature", UNSET))


        published_sequence = cls(
            expected_size=expected_size,
            final_size=final_size,
            verdict=verdict,
            frames=frames,
            summary_preimage_version=summary_preimage_version,
            summary_signature=summary_signature,
        )


        published_sequence.additional_properties = d
        return published_sequence

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
