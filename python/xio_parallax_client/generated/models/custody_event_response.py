from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from uuid import UUID
import datetime






T = TypeVar("T", bound="CustodyEventResponse")



@_attrs_define
class CustodyEventResponse:
    """ 
        Attributes:
            id (UUID):
            account_id (UUID):
            subject_id (str):
            subject_kind (str):
            pool_key (str):
            image_hash (str):
            kind (str):
            byte_length (int | None | str):
            custody_path (None | str):
            verified_absent_at (datetime.datetime | None):
            occurred_at (datetime.datetime):
     """

    id: UUID
    account_id: UUID
    subject_id: str
    subject_kind: str
    pool_key: str
    image_hash: str
    kind: str
    byte_length: int | None | str
    custody_path: None | str
    verified_absent_at: datetime.datetime | None
    occurred_at: datetime.datetime
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        id = str(self.id)

        account_id = str(self.account_id)

        subject_id = self.subject_id

        subject_kind = self.subject_kind

        pool_key = self.pool_key

        image_hash = self.image_hash

        kind = self.kind

        byte_length: int | None | str
        byte_length = self.byte_length

        custody_path: None | str
        custody_path = self.custody_path

        verified_absent_at: None | str
        if isinstance(self.verified_absent_at, datetime.datetime):
            verified_absent_at = self.verified_absent_at.isoformat()
        else:
            verified_absent_at = self.verified_absent_at

        occurred_at = self.occurred_at.isoformat()


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "id": id,
            "accountId": account_id,
            "subjectId": subject_id,
            "subjectKind": subject_kind,
            "poolKey": pool_key,
            "imageHash": image_hash,
            "kind": kind,
            "byteLength": byte_length,
            "custodyPath": custody_path,
            "verifiedAbsentAt": verified_absent_at,
            "occurredAt": occurred_at,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = UUID(d.pop("id"))




        account_id = UUID(d.pop("accountId"))




        subject_id = d.pop("subjectId")

        subject_kind = d.pop("subjectKind")

        pool_key = d.pop("poolKey")

        image_hash = d.pop("imageHash")

        kind = d.pop("kind")

        def _parse_byte_length(data: object) -> int | None | str:
            if data is None:
                return data
            return cast(int | None | str, data)

        byte_length = _parse_byte_length(d.pop("byteLength"))


        def _parse_custody_path(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        custody_path = _parse_custody_path(d.pop("custodyPath"))


        def _parse_verified_absent_at(data: object) -> datetime.datetime | None:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                verified_absent_at_type_1 = datetime.datetime.fromisoformat(data)



                return verified_absent_at_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None, data)

        verified_absent_at = _parse_verified_absent_at(d.pop("verifiedAbsentAt"))


        occurred_at = datetime.datetime.fromisoformat(d.pop("occurredAt"))




        custody_event_response = cls(
            id=id,
            account_id=account_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
            pool_key=pool_key,
            image_hash=image_hash,
            kind=kind,
            byte_length=byte_length,
            custody_path=custody_path,
            verified_absent_at=verified_absent_at,
            occurred_at=occurred_at,
        )


        custody_event_response.additional_properties = d
        return custody_event_response

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
