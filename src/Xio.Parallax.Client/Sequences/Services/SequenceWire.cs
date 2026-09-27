namespace Xio.Parallax.Client.Sequences.Services;

// PC-104: the sequence wire words the register conversation branches on, spelled once
/// <summary>The sequence states, commit outcome and commit frame state the register conversation reads.</summary>
internal static class SequenceWire
{
    /// <summary>A sequence still taking frames.</summary>
    public const string Open = "open";

    /// <summary>A sequence END sealed; only fills are taken.</summary>
    public const string Sealed = "sealed";

    /// <summary>A sequence the engine has taken.</summary>
    public const string Committed = "committed";

    /// <summary>A commit that did not write the sequence record this call.</summary>
    public const string Incomplete = "incomplete";

    /// <summary>A frame a commit has not published yet.</summary>
    public const string NotPublished = "notPublished";
}
