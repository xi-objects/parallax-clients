namespace Xio.Parallax.Client.C2pa.Models;

/// <summary>What detection found in a file: its carrier, the embedded C2PA store when there is one, and a description of the finding.</summary>
/// <param name="Carrier">The carrier the file was recognised as, or <see cref="C2paCarrier.Unsupported"/>.</param>
/// <param name="Store">The embedded store; null when the carrier is unsupported, carries no store, or its store is malformed.</param>
/// <param name="Detail">A description of what was found, or of why no store is returned.</param>
public sealed record EmbeddedC2paResult(C2paCarrier Carrier,
                                        EmbeddedC2paStore? Store,
                                        string Detail);

/// <summary>An embedded C2PA manifest store: its superbox bytes and a summary of every box inside it.</summary>
/// <param name="Bytes">The whole JUMBF superbox, from its LBox to its last byte.</param>
/// <param name="Boxes">Every box of the store in document order, the superbox first.</param>
public sealed record EmbeddedC2paStore(ReadOnlyMemory<byte> Bytes,
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

/// <summary>The comparison of an embedded C2PA store with a recovered record.</summary>
/// <param name="Outcome">How the store compares with the record's manifests.</param>
/// <param name="MatchedKind">The kind of the record manifest the store matched; null unless the outcome is <see cref="C2paComparisonOutcome.Match"/>.</param>
/// <param name="Detail">A description of the comparison.</param>
public sealed record C2paComparison(C2paComparisonOutcome Outcome,
                                    string? MatchedKind,
                                    string Detail);

/// <summary>What a carrier reader extracted: the candidate superbox bytes, or null with the reason.</summary>
internal sealed record CarrierExtraction(ReadOnlyMemory<byte>? Superbox,
                                         string Detail);

/// <summary>One parsed JUMBF box header: the box type, where the box starts, where its payload starts and where it ends.</summary>
internal sealed record JumbfBoxHeader(string Type,
                                      int Start,
                                      int PayloadStart,
                                      int End);

/// <summary>A malformed carrier or JUMBF structure, reported as the detection's detail.</summary>
internal sealed class C2paFormatException(string message) : Exception(message);
