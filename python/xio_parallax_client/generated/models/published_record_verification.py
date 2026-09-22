from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
import datetime






T = TypeVar("T", bound="PublishedRecordVerification")



@_attrs_define
class PublishedRecordVerification:
    """ 
        Attributes:
            content_hash (str):
            hash_algorithm (str):
            signed_at_utc (datetime.datetime):
            signature (str):
            signature_algorithm (str):
            public_key (str):
            leaf_certificate (str):
            certificate_chain (list[str]):
            leaf_certificate_thumbprint (str):
            trust_context (str):
            trust_version (int | str):
            canonical_version (int | str):
            collection_signature (None | str):
     """

    content_hash: str
    hash_algorithm: str
    signed_at_utc: datetime.datetime
    signature: str
    signature_algorithm: str
    public_key: str
    leaf_certificate: str
    certificate_chain: list[str]
    leaf_certificate_thumbprint: str
    trust_context: str
    trust_version: int | str
    canonical_version: int | str
    collection_signature: None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        content_hash = self.content_hash

        hash_algorithm = self.hash_algorithm

        signed_at_utc = self.signed_at_utc.isoformat()

        signature = self.signature

        signature_algorithm = self.signature_algorithm

        public_key = self.public_key

        leaf_certificate = self.leaf_certificate

        certificate_chain = self.certificate_chain



        leaf_certificate_thumbprint = self.leaf_certificate_thumbprint

        trust_context = self.trust_context

        trust_version: int | str
        trust_version = self.trust_version

        canonical_version: int | str
        canonical_version = self.canonical_version

        collection_signature: None | str
        collection_signature = self.collection_signature


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "contentHash": content_hash,
            "hashAlgorithm": hash_algorithm,
            "signedAtUtc": signed_at_utc,
            "signature": signature,
            "signatureAlgorithm": signature_algorithm,
            "publicKey": public_key,
            "leafCertificate": leaf_certificate,
            "certificateChain": certificate_chain,
            "leafCertificateThumbprint": leaf_certificate_thumbprint,
            "trustContext": trust_context,
            "trustVersion": trust_version,
            "canonicalVersion": canonical_version,
            "collectionSignature": collection_signature,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        content_hash = d.pop("contentHash")

        hash_algorithm = d.pop("hashAlgorithm")

        signed_at_utc = datetime.datetime.fromisoformat(d.pop("signedAtUtc"))




        signature = d.pop("signature")

        signature_algorithm = d.pop("signatureAlgorithm")

        public_key = d.pop("publicKey")

        leaf_certificate = d.pop("leafCertificate")

        certificate_chain = cast(list[str], d.pop("certificateChain"))


        leaf_certificate_thumbprint = d.pop("leafCertificateThumbprint")

        trust_context = d.pop("trustContext")

        def _parse_trust_version(data: object) -> int | str:
            return cast(int | str, data)

        trust_version = _parse_trust_version(d.pop("trustVersion"))


        def _parse_canonical_version(data: object) -> int | str:
            return cast(int | str, data)

        canonical_version = _parse_canonical_version(d.pop("canonicalVersion"))


        def _parse_collection_signature(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        collection_signature = _parse_collection_signature(d.pop("collectionSignature"))


        published_record_verification = cls(
            content_hash=content_hash,
            hash_algorithm=hash_algorithm,
            signed_at_utc=signed_at_utc,
            signature=signature,
            signature_algorithm=signature_algorithm,
            public_key=public_key,
            leaf_certificate=leaf_certificate,
            certificate_chain=certificate_chain,
            leaf_certificate_thumbprint=leaf_certificate_thumbprint,
            trust_context=trust_context,
            trust_version=trust_version,
            canonical_version=canonical_version,
            collection_signature=collection_signature,
        )


        published_record_verification.additional_properties = d
        return published_record_verification

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
