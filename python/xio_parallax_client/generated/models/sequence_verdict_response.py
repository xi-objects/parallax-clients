from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.sequence_errata_frame_response import SequenceErrataFrameResponse
  from ..models.sequence_gap_range_response import SequenceGapRangeResponse





T = TypeVar("T", bound="SequenceVerdictResponse")



@_attrs_define
class SequenceVerdictResponse:
    """ 
        Attributes:
            state (str):
            frames_received (int | str):
            expected_size (int | None | str):
            reach (int | str):
            gaps (list[SequenceGapRangeResponse]):
            errata (list[SequenceErrataFrameResponse]):
            connected (bool):
     """

    state: str
    frames_received: int | str
    expected_size: int | None | str
    reach: int | str
    gaps: list[SequenceGapRangeResponse]
    errata: list[SequenceErrataFrameResponse]
    connected: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.sequence_errata_frame_response import SequenceErrataFrameResponse # noqa: PLC0415
        from ..models.sequence_gap_range_response import SequenceGapRangeResponse # noqa: PLC0415
        state = self.state

        frames_received: int | str
        frames_received = self.frames_received

        expected_size: int | None | str
        expected_size = self.expected_size

        reach: int | str
        reach = self.reach

        gaps = []
        for gaps_item_data in self.gaps:
            gaps_item = gaps_item_data.to_dict()
            gaps.append(gaps_item)



        errata = []
        for errata_item_data in self.errata:
            errata_item = errata_item_data.to_dict()
            errata.append(errata_item)



        connected = self.connected


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "state": state,
            "framesReceived": frames_received,
            "expectedSize": expected_size,
            "reach": reach,
            "gaps": gaps,
            "errata": errata,
            "connected": connected,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.sequence_errata_frame_response import SequenceErrataFrameResponse # noqa: PLC0415
        from ..models.sequence_gap_range_response import SequenceGapRangeResponse # noqa: PLC0415
        d = dict(src_dict)
        state = d.pop("state")

        def _parse_frames_received(data: object) -> int | str:
            return cast(int | str, data)

        frames_received = _parse_frames_received(d.pop("framesReceived"))


        def _parse_expected_size(data: object) -> int | None | str:
            if data is None:
                return data
            return cast(int | None | str, data)

        expected_size = _parse_expected_size(d.pop("expectedSize"))


        def _parse_reach(data: object) -> int | str:
            return cast(int | str, data)

        reach = _parse_reach(d.pop("reach"))


        gaps = []
        _gaps = d.pop("gaps")
        for gaps_item_data in (_gaps):
            gaps_item = SequenceGapRangeResponse.from_dict(gaps_item_data)



            gaps.append(gaps_item)


        errata = []
        _errata = d.pop("errata")
        for errata_item_data in (_errata):
            errata_item = SequenceErrataFrameResponse.from_dict(errata_item_data)



            errata.append(errata_item)


        connected = d.pop("connected")

        sequence_verdict_response = cls(
            state=state,
            frames_received=frames_received,
            expected_size=expected_size,
            reach=reach,
            gaps=gaps,
            errata=errata,
            connected=connected,
        )


        sequence_verdict_response.additional_properties = d
        return sequence_verdict_response

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
