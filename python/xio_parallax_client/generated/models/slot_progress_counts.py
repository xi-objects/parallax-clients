from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast






T = TypeVar("T", bound="SlotProgressCounts")



@_attrs_define
class SlotProgressCounts:
    """ 
        Attributes:
            total (int | str):
            held (int | str):
            registered (int | str):
            answered (int | str):
            failed (int | str):
            errata (int | str):
            retry (int | str):
     """

    total: int | str
    held: int | str
    registered: int | str
    answered: int | str
    failed: int | str
    errata: int | str
    retry: int | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        total: int | str
        total = self.total

        held: int | str
        held = self.held

        registered: int | str
        registered = self.registered

        answered: int | str
        answered = self.answered

        failed: int | str
        failed = self.failed

        errata: int | str
        errata = self.errata

        retry: int | str
        retry = self.retry


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "total": total,
            "held": held,
            "registered": registered,
            "answered": answered,
            "failed": failed,
            "errata": errata,
            "retry": retry,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        def _parse_total(data: object) -> int | str:
            return cast(int | str, data)

        total = _parse_total(d.pop("total"))


        def _parse_held(data: object) -> int | str:
            return cast(int | str, data)

        held = _parse_held(d.pop("held"))


        def _parse_registered(data: object) -> int | str:
            return cast(int | str, data)

        registered = _parse_registered(d.pop("registered"))


        def _parse_answered(data: object) -> int | str:
            return cast(int | str, data)

        answered = _parse_answered(d.pop("answered"))


        def _parse_failed(data: object) -> int | str:
            return cast(int | str, data)

        failed = _parse_failed(d.pop("failed"))


        def _parse_errata(data: object) -> int | str:
            return cast(int | str, data)

        errata = _parse_errata(d.pop("errata"))


        def _parse_retry(data: object) -> int | str:
            return cast(int | str, data)

        retry = _parse_retry(d.pop("retry"))


        slot_progress_counts = cls(
            total=total,
            held=held,
            registered=registered,
            answered=answered,
            failed=failed,
            errata=errata,
            retry=retry,
        )


        slot_progress_counts.additional_properties = d
        return slot_progress_counts

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
