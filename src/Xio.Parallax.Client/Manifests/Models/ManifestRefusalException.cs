namespace Xio.Parallax.Client.Manifests.Models;

/// <summary>
/// Manifest resolution refused: every offending image, each with one reason. Nothing was resolved
/// for any image, so nothing is sent.
/// </summary>
public sealed class ManifestRefusalException : Exception
{
    /// <summary>Creates the refusal over every offending image.</summary>
    /// <param name="refusals">One refusal per offending image, in request order.</param>
    public ManifestRefusalException(IReadOnlyList<ManifestRefusal> refusals)
        : base(Describe(refusals))
    {
        Refusals = refusals;
    }

    /// <summary>One refusal per offending image, in request order.</summary>
    public IReadOnlyList<ManifestRefusal> Refusals { get; }

    private static string Describe(IReadOnlyList<ManifestRefusal> refusals)
    {
        ArgumentNullException.ThrowIfNull(refusals);
        var lines = refusals.Select(refusal => $"{refusal.FileName}: {refusal.Reason}");
        return string.Join('\n', lines.Prepend($"Manifest resolution refused {refusals.Count} image(s):"));
    }
}
