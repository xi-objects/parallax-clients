from enum import StrEnum

class PublishedRecordOutcome(StrEnum):
    NORECORDANSWERED = "noRecordAnswered"
    PUBLISHED = "published"
    REFUSED = "refused"
    RETRY = "retry"
    TAKENDOWN = "takenDown"

    def __str__(self) -> str:
        return str(self.value)
