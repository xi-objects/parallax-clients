namespace Xio.Parallax.Client.C2pa.Models;

/// <summary>What detection found in a file: its carrier, the outcome, every embedded JUMBF manifest store when found, and a description of the finding.</summary>
/// <param name="Carrier">The carrier the file was recognised as, or <see cref="C2paCarrier.Unsupported"/>.</param>
/// <param name="Outcome">Whether stores were found, the carrier holds none, its slot is malformed, or the carrier is unsupported.</param>
/// <param name="Stores">Every embedded store in document order, each classified c2pa or jumbf; empty unless the outcome is <see cref="EmbeddedC2paOutcome.Found"/>.</param>
/// <param name="Detail">A description of what was found, or of why no store is returned.</param>
public sealed record EmbeddedC2paResult(C2paCarrier Carrier,
                                        EmbeddedC2paOutcome Outcome,
                                        IReadOnlyList<EmbeddedC2paStore> Stores,
                                        string Detail);

/// <summary>An embedded JUMBF manifest store: its classified kind, its superbox bytes and a summary of every box inside it.</summary>
/// <param name="Kind">c2pa when the description box carries the C2PA manifest-store UUID and the label c2pa; jumbf for any other well-formed superbox.</param>
/// <param name="Bytes">The whole JUMBF superbox, from its LBox to its last byte.</param>
/// <param name="Boxes">Every box of the store in document order, the superbox first.</param>
public sealed record EmbeddedC2paStore(string Kind,
                                       ReadOnlyMemory<byte> Bytes,
                                       IReadOnlyList<JumbfBoxSummary> Boxes);

/// <summary>One JUMBF box of a store: its type, its label, its nesting depth and its length.</summary>
/// <param name="Type">The box's four-character TBox, for example jumb, jumd or cbor.</param>
/// <param name="Label">The description label of a jumb box and of its jumd box; null for other boxes and for unlabelled ones.</param>
/// <param name="Depth">The nesting depth; the store's superbox is 0.</param>
/// <param name="Length">The box's length in bytes, header included.</param>
public sealed record JumbfBoxSummary(string Type,
                                     string? Label,
                                     int Depth,
                                     long Length);

/// <summary>The comparison of an embedded JUMBF manifest store with a recovered record.</summary>
/// <param name="Outcome">How the store compares with the record's manifests.</param>
/// <param name="MatchedKind">The kind of the record manifest the store matched; null unless the outcome is <see cref="C2paComparisonOutcome.Match"/>.</param>
/// <param name="Detail">A description of the comparison.</param>
public sealed record C2paComparison(C2paComparisonOutcome Outcome,
                                    string? MatchedKind,
                                    string Detail);

/// <summary>What a carrier reader extracted: every candidate superbox in document order, empty for none, and a description.</summary>
internal sealed record CarrierExtraction(IReadOnlyList<ReadOnlyMemory<byte>> Superboxes,
                                         string Detail);

/// <summary>One parsed JUMBF box header: the box type, where the box starts, where its payload starts and where it ends.</summary>
internal sealed record JumbfBoxHeader(string Type,
                                      int Start,
                                      int PayloadStart,
                                      int End);

/// <summary>A malformed carrier or JUMBF structure, reported as the detection's detail.</summary>
internal sealed class C2paFormatException(string message) : Exception(message);
