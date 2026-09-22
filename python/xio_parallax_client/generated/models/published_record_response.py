from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.published_record_outcome import PublishedRecordOutcome
from typing import cast

if TYPE_CHECKING:
  from ..models.published_record_response_manifests_type_1_item import PublishedRecordResponseManifestsType1Item
  from ..models.published_record_verification import PublishedRecordVerification





T = TypeVar("T", bound="PublishedRecordResponse")



@_attrs_define
class PublishedRecordResponse:
    """ 
        Attributes:
            original_image_hash (str):
            outcome (PublishedRecordOutcome):
            manifests (list[PublishedRecordResponseManifestsType1Item] | None):
            verification (None | PublishedRecordVerification):
            failure_reason (None | str):
     """

    original_image_hash: str
    outcome: PublishedRecordOutcome
    manifests: list[PublishedRecordResponseManifestsType1Item] | None
    verification: None | PublishedRecordVerification
    failure_reason: None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.published_record_response_manifests_type_1_item import PublishedRecordResponseManifestsType1Item # noqa: PLC0415
        from ..models.published_record_verification import PublishedRecordVerification # noqa: PLC0415
        original_image_hash = self.original_image_hash

        outcome = self.outcome.value

        manifests: list[dict[str, Any]] | None
        if isinstance(self.manifests, list):
            manifests = []
            for manifests_type_1_item_data in self.manifests:
                manifests_type_1_item = manifests_type_1_item_data.to_dict()
                manifests.append(manifests_type_1_item)


        else:
            manifests = self.manifests

        verification: dict[str, Any] | None
        if isinstance(self.verification, PublishedRecordVerification):
            verification = self.verification.to_dict()
        else:
            verification = self.verification

        failure_reason: None | str
        failure_reason = self.failure_reason


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "originalImageHash": original_image_hash,
            "outcome": outcome,
            "manifests": manifests,
            "verification": verification,
            "failureReason": failure_reason,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.published_record_response_manifests_type_1_item import PublishedRecordResponseManifestsType1Item # noqa: PLC0415
        from ..models.published_record_verification import PublishedRecordVerification # noqa: PLC0415
        d = dict(src_dict)
        original_image_hash = d.pop("originalImageHash")

        outcome = PublishedRecordOutcome(d.pop("outcome"))




        def _parse_manifests(data: object) -> list[PublishedRecordResponseManifestsType1Item] | None:
            if data is None:
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                manifests_type_1 = []
                _manifests_type_1 = data
                for manifests_type_1_item_data in (_manifests_type_1):
                    manifests_type_1_item = PublishedRecordResponseManifestsType1Item.from_dict(manifests_type_1_item_data)



                    manifests_type_1.append(manifests_type_1_item)

                return manifests_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[PublishedRecordResponseManifestsType1Item] | None, data)

        manifests = _parse_manifests(d.pop("manifests"))


        def _parse_verification(data: object) -> None | PublishedRecordVerification:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                verification_type_1 = PublishedRecordVerification.from_dict(data)



                return verification_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | PublishedRecordVerification, data)

        verification = _parse_verification(d.pop("verification"))


        def _parse_failure_reason(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        failure_reason = _parse_failure_reason(d.pop("failureReason"))


        published_record_response = cls(
            original_image_hash=original_image_hash,
            outcome=outcome,
            manifests=manifests,
            verification=verification,
            failure_reason=failure_reason,
        )


        published_record_response.additional_properties = d
        return published_record_response

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
