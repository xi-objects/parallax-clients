from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.sequence_admitted_frame_response import SequenceAdmittedFrameResponse
  from ..models.sequence_verdict_response import SequenceVerdictResponse





T = TypeVar("T", bound="SequenceFrameBatchResponse")



@_attrs_define
class SequenceFrameBatchResponse:
    """ 
        Attributes:
            frames (list[SequenceAdmittedFrameResponse]):
            verdict (None | SequenceVerdictResponse):
     """

    frames: list[SequenceAdmittedFrameResponse]
    verdict: None | SequenceVerdictResponse
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.sequence_admitted_frame_response import SequenceAdmittedFrameResponse # noqa: PLC0415
        from ..models.sequence_verdict_response import SequenceVerdictResponse # noqa: PLC0415
        frames = []
        for frames_item_data in self.frames:
            frames_item = frames_item_data.to_dict()
            frames.append(frames_item)



        verdict: dict[str, Any] | None
        if isinstance(self.verdict, SequenceVerdictResponse):
            verdict = self.verdict.to_dict()
        else:
            verdict = self.verdict


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "frames": frames,
            "verdict": verdict,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.sequence_admitted_frame_response import SequenceAdmittedFrameResponse # noqa: PLC0415
        from ..models.sequence_verdict_response import SequenceVerdictResponse # noqa: PLC0415
        d = dict(src_dict)
        frames = []
        _frames = d.pop("frames")
        for frames_item_data in (_frames):
            frames_item = SequenceAdmittedFrameResponse.from_dict(frames_item_data)



            frames.append(frames_item)


        def _parse_verdict(data: object) -> None | SequenceVerdictResponse:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                verdict_type_1 = SequenceVerdictResponse.from_dict(data)



                return verdict_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SequenceVerdictResponse, data)

        verdict = _parse_verdict(d.pop("verdict"))


        sequence_frame_batch_response = cls(
            frames=frames,
            verdict=verdict,
        )


        sequence_frame_batch_response.additional_properties = d
        return sequence_frame_batch_response

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
