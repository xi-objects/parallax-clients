namespace Xio.Parallax.Client.Verification.Models;

// PC-119: the values the version-1 sequence summary preimage is laid out from - exactly the summary a
// published sequence record answers, with its sequence hash (the record's own contentHash)
/// <summary>Asks for the version-1 sequence summary preimage.</summary>
/// <param name="SequenceHash">The sequence hash bytes: the sequence record's own content hash.</param>
/// <param name="ExpectedSize">The size the registrant declared, or null when it declared none.</param>
/// <param name="FinalSize">How many frames the sequence was committed with.</param>
/// <param name="Connected">Whether the walk arrived at END through frames only.</param>
/// <param name="Sealed">Whether END had sealed the sequence.</param>
/// <param name="Reach">The highest frame id the walk reached without a gap.</param>
/// <param name="FramesReceived">How many frames the sequence was committed with, as the verdict counts them.</param>
/// <param name="Frames">Every frame, in walk order.</param>
public sealed record XioSequenceSummaryPreimageRequest(ReadOnlyMemory<byte> SequenceHash,
                                                       int? ExpectedSize,
                                                       int FinalSize,
                                                       bool Connected,
                                                       bool Sealed,
                                                       long Reach,
                                                       int FramesReceived,
                                                       IReadOnlyList<SequenceSummaryFrameEntry> Frames);

// PC-119: one frame's 72-byte contribution to the summary's frames digest
/// <summary>One frame's contribution to the summary preimage's frames digest.</summary>
/// <param name="FrameId">The frame's id within the sequence.</param>
/// <param name="OriginalImageHash">The frame record's key: its image's BLAKE3-256 content hash bytes.</param>
/// <param name="FrameHash">The frame's PX frame hash bytes.</param>
public sealed record SequenceSummaryFrameEntry(long FrameId,
                                               ReadOnlyMemory<byte> OriginalImageHash,
                                               ReadOnlyMemory<byte> FrameHash);

// PC-119: asks for a sequence record's two checks, over the record's own summary and what admission read
/// <summary>Asks for a published sequence record's sequence-hash and summary-signature checks.</summary>
internal sealed record XioSequenceSummaryCheckRequest(PublishedSequence Sequence,
                                                      RecordAdmissionResult Admission);
