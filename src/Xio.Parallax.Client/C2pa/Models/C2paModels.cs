namespace Xio.Parallax.Client.C2pa.Models;

/// <summary>The comparison of an embedded JUMBF manifest store with a recovered record.</summary>
/// <param name="Outcome">How the store compares with the record's manifests.</param>
/// <param name="MatchedKind">The kind of the record manifest the store matched; null unless the outcome is <see cref="C2paComparisonOutcome.Match"/>.</param>
/// <param name="Detail">A description of the comparison.</param>
public sealed record C2paComparison(C2paComparisonOutcome Outcome,
                                    string? MatchedKind,
                                    string Detail);
