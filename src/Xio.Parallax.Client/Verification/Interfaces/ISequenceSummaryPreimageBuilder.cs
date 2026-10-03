namespace Xio.Parallax.Client.Verification.Interfaces;

// PC-119: the bytes a sequence record's leaf signs over its summary - Xio.Parallax.Common's sequence summary
// preimage, version 1, laid out here exactly as px-frame.md "The sequence summary preimage" defines it
/// <summary>Builds the version-1 sequence summary preimage a published sequence record's <c>summarySignature</c> is made over.</summary>
public interface ISequenceSummaryPreimageBuilder
{
    /// <summary>Builds the 115-byte preimage, every integer big-endian: <c>[0x01] ‖ u16(19) ‖ "px-sequence-summary" ‖ u16(32) ‖
    /// sequenceHash ‖ u8(expectedSize present) ‖ i32(expectedSize or 0) ‖ i32(finalSize) ‖ u8(connected) ‖ u8(sealed) ‖ i64(reach) ‖
    /// i32(framesReceived) ‖ u32(frame count) ‖ framesDigest</c>, where the frames digest is BLAKE3-256 over every frame's
    /// <c>i64(frameId) ‖ originalImageHash ‖ frameHash</c>, concatenated in walk order.</summary>
    /// <exception cref="ArgumentException">A hash is not 32 bytes, there are no frames, or a size or count is negative.</exception>
    byte[] Build(XioSequenceSummaryPreimageRequest request);

    /// <summary>Returns the frames digest alone: BLAKE3-256 over every frame's 72-byte entry in walk order.</summary>
    byte[] FramesDigest(IReadOnlyList<SequenceSummaryFrameEntry> frames);
}
