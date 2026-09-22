from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.lookup_response import LookupResponse





T = TypeVar("T", bound="LookupQueryResultResponse")



@_attrs_define
class LookupQueryResultResponse:
    """ 
        Attributes:
            image_hash (str):
            state (str):
            result (LookupResponse | None):
            failure_reason (None | str):
     """

    image_hash: str
    state: str
    result: LookupResponse | None
    failure_reason: None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.lookup_response import LookupResponse # noqa: PLC0415
        image_hash = self.image_hash

        state = self.state

        result: dict[str, Any] | None
        if isinstance(self.result, LookupResponse):
            result = self.result.to_dict()
        else:
            result = self.result

        failure_reason: None | str
        failure_reason = self.failure_reason


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "imageHash": image_hash,
            "state": state,
            "result": result,
            "failureReason": failure_reason,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.lookup_response import LookupResponse # noqa: PLC0415
        d = dict(src_dict)
        image_hash = d.pop("imageHash")

        state = d.pop("state")

        def _parse_result(data: object) -> LookupResponse | None:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                result_type_1 = LookupResponse.from_dict(data)



                return result_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(LookupResponse | None, data)

        result = _parse_result(d.pop("result"))


        def _parse_failure_reason(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        failure_reason = _parse_failure_reason(d.pop("failureReason"))


        lookup_query_result_response = cls(
            image_hash=image_hash,
            state=state,
            result=result,
            failure_reason=failure_reason,
        )


        lookup_query_result_response.additional_properties = d
        return lookup_query_result_response

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
