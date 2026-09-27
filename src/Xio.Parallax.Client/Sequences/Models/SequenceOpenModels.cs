namespace Xio.Parallax.Client.Sequences.Models;

// PC-102: what opens a sequence: its manifests and an optional expected size
/// <summary>The manifests and optional expected size a sequence opens with.</summary>
/// <param name="Manifests">The manifests to send with open, in the order the wire carries them.</param>
/// <param name="ExpectedSize">
/// The sequence's expected final frame count, when known ahead of time; validated positive when
/// given. Left null, the server tracks no expectation until <c>PUT expected-size</c> sets one.
/// </param>
public sealed record SequenceOpenRequest(IReadOnlyList<ManifestPart> Manifests,
                                         long? ExpectedSize)
{
    /// <summary>The sequence's expected final frame count, when known ahead of time.</summary>
    public long? ExpectedSize { get; } = ValidateExpectedSize(ExpectedSize);

    private static long? ValidateExpectedSize(long? expectedSize)
    {
        return expectedSize is null or > 0
            ? expectedSize
            : throw new ArgumentException($"expectedSize must be above zero when given; was {expectedSize}.", nameof(expectedSize));
    }
}
