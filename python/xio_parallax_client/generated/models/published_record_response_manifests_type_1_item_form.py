from enum import StrEnum

class PublishedRecordResponseManifestsType1ItemForm(StrEnum):
    JSON = "json"
    JUMBF = "jumbf"

    def __str__(self) -> str:
        return str(self.value)
