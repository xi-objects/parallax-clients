from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.sequence_commit_frame_response import SequenceCommitFrameResponse





T = TypeVar("T", bound="SequenceCommitResponse")



@_attrs_define
class SequenceCommitResponse:
    """ 
        Attributes:
            sequence_hash (None | str):
            outcome (str):
            sequence_record_published (bool):
            frames (list[SequenceCommitFrameResponse]):
     """

    sequence_hash: None | str
    outcome: str
    sequence_record_published: bool
    frames: list[SequenceCommitFrameResponse]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.sequence_commit_frame_response import SequenceCommitFrameResponse # noqa: PLC0415
        sequence_hash: None | str
        sequence_hash = self.sequence_hash

        outcome = self.outcome

        sequence_record_published = self.sequence_record_published

        frames = []
        for frames_item_data in self.frames:
            frames_item = frames_item_data.to_dict()
            frames.append(frames_item)




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "sequenceHash": sequence_hash,
            "outcome": outcome,
            "sequenceRecordPublished": sequence_record_published,
            "frames": frames,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.sequence_commit_frame_response import SequenceCommitFrameResponse # noqa: PLC0415
        d = dict(src_dict)
        def _parse_sequence_hash(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        sequence_hash = _parse_sequence_hash(d.pop("sequenceHash"))


        outcome = d.pop("outcome")

        sequence_record_published = d.pop("sequenceRecordPublished")

        frames = []
        _frames = d.pop("frames")
        for frames_item_data in (_frames):
            frames_item = SequenceCommitFrameResponse.from_dict(frames_item_data)



            frames.append(frames_item)


        sequence_commit_response = cls(
            sequence_hash=sequence_hash,
            outcome=outcome,
            sequence_record_published=sequence_record_published,
            frames=frames,
        )


        sequence_commit_response.additional_properties = d
        return sequence_commit_response

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
