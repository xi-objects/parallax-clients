from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.lookup_query_result_response import LookupQueryResultResponse





T = TypeVar("T", bound="LookupResultsResponse")



@_attrs_define
class LookupResultsResponse:
    """ 
        Attributes:
            lookup_slot_id (str):
            queries (list[LookupQueryResultResponse]):
     """

    lookup_slot_id: str
    queries: list[LookupQueryResultResponse]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.lookup_query_result_response import LookupQueryResultResponse # noqa: PLC0415
        lookup_slot_id = self.lookup_slot_id

        queries = []
        for queries_item_data in self.queries:
            queries_item = queries_item_data.to_dict()
            queries.append(queries_item)




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "lookupSlotId": lookup_slot_id,
            "queries": queries,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.lookup_query_result_response import LookupQueryResultResponse # noqa: PLC0415
        d = dict(src_dict)
        lookup_slot_id = d.pop("lookupSlotId")

        queries = []
        _queries = d.pop("queries")
        for queries_item_data in (_queries):
            queries_item = LookupQueryResultResponse.from_dict(queries_item_data)



            queries.append(queries_item)


        lookup_results_response = cls(
            lookup_slot_id=lookup_slot_id,
            queries=queries,
        )


        lookup_results_response.additional_properties = d
        return lookup_results_response

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
