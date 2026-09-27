namespace Xio.Parallax.Client;

// PC-103: shared machinery for the sequence conversation: the one place the ticket header is
// attached, and the plumbing for the two sequence routes whose multipart body the generator
// cannot shape (open, frame upload)
/// <summary>
/// Shared machinery for the sequence route members: the <c>X-Sequence-Ticket</c> header every
/// route but open carries, and the error mappings for the two routes sent through the raw
/// multipart sender rather than a generated request builder.
/// </summary>
public sealed partial class ParallaxClient
{
    private const string SequenceOpenUrlTemplate = "{+baseurl}/sequences";
    private const string SequenceFramesUrlTemplate = "{+baseurl}/sequences/{sequenceId}/frames";
    private const string SequenceTicketHeaderName = "X-Sequence-Ticket";

    private static readonly Dictionary<string, ParsableFactory<IParsable>> SequenceOpenErrorMapping =
        BuildErrorMapping(400, 401, 403, 413);

    private static readonly Dictionary<string, ParsableFactory<IParsable>> SequenceFramesErrorMapping =
        BuildErrorMapping(400, 401, 403, 404, 409, 413, 422, 500, 503);

    private readonly SequenceFrameEncoder _sequenceFrameEncoder = new();

    /// <summary>
    /// The one header every sequence route but open sends: the sequence's own ticket. This is
    /// the single place a ticket is ever placed on a request; nothing else builds this header.
    /// </summary>
    /// <param name="ticket">The sequence's ticket, from its <see cref="SequenceHandle"/>.</param>
    /// <returns>The ticket, keyed by <see cref="SequenceTicketHeaderName"/>.</returns>
    private static IReadOnlyDictionary<string, string> SequenceTicketHeaders(string ticket)
        => new Dictionary<string, string>(StringComparer.Ordinal) { [SequenceTicketHeaderName] = ticket };

    /// <summary>
    /// The same ticket header from <see cref="SequenceTicketHeaders"/>, shaped as the
    /// configuration action a generated sequence request builder takes.
    /// </summary>
    /// <param name="ticket">The sequence's ticket, from its <see cref="SequenceHandle"/>.</param>
    /// <returns>A configuration action that attaches the ticket header.</returns>
    private static Action<RequestConfiguration<DefaultQueryParameters>> SequenceTicketConfiguration(string ticket)
        => configuration =>
        {
            foreach (var header in SequenceTicketHeaders(ticket))
            {
                configuration.Headers.Add(header.Key, header.Value);
            }
        };

    private Dictionary<string, object> SequencePathParameters(Guid sequenceId)
        => new(StringComparer.Ordinal)
        {
            ["baseurl"] = _requestAdapter.BaseUrl!,
            ["sequenceId"] = sequenceId.ToString(),
        };
}
