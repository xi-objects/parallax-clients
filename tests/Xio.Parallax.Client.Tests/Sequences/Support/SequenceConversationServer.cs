namespace Xio.Parallax.Client.Tests.Sequences.Support;

// PC-104: one uploaded frame read back through Common: its type, its id and its links
/// <summary>One uploaded frame decoded back through Common: its type, id and links.</summary>
/// <param name="Type">The frame's type, BODY or END.</param>
/// <param name="FrameId">The frame's id.</param>
/// <param name="Prev">The frame's prev link.</param>
/// <param name="Next">The frame's next link; null for END, which carries none.</param>
internal sealed record DecodedSequenceFrame(PxFrameType Type, long FrameId, long Prev, long? Next);

// PC-104: a scripted sequence server for the register conversation, each route answered from its own script
/// <summary>
/// A fake sequence server behind <see cref="FakeHttpMessageHandler"/>: open answers a real HEAD
/// frame, frames answers each part's id (errata where scripted, the sealing verdict on the batch
/// carrying <see cref="SealingFrameId"/>), and progress and commit answer their queued scripts in order.
/// </summary>
internal sealed class SequenceConversationServer
{
    internal const string Ticket = "sequence-ticket-register";
    internal const string TicketHeaderName = "X-Sequence-Ticket";

    private readonly string _headFrameBase64;

    private SequenceConversationServer(Guid sequenceId, string headFrameBase64)
    {
        SequenceId = sequenceId;
        _headFrameBase64 = headFrameBase64;
        Handler = new FakeHttpMessageHandler(Respond);
    }

    internal Guid SequenceId { get; }

    internal FakeHttpMessageHandler Handler { get; }

    /// <summary>The sequence as open answers it, for a resume.</summary>
    internal OpenedSequence Opened => new(new SequenceHandle(SequenceId, Ticket), 0);

    internal HashSet<long> ErrataFrameIds { get; } = [];

    /// <summary>The frame id whose batch answers <see cref="SealingVerdictJson"/>: the END id.</summary>
    internal long? SealingFrameId { get; set; }

    internal string? SealingVerdictJson { get; set; }

    internal Queue<string> Progress { get; } = new();

    internal Queue<string> Commits { get; } = new();

    internal string GapsJson { get; set; } = """{ "gaps": [] }""";

    /// <summary>Every request's method and path, in order.</summary>
    internal IReadOnlyList<string> Calls => Handler.Requests.Select(request => $"{request.Method} {request.RequestUri.AbsolutePath}").ToList();

    internal static async Task<SequenceConversationServer> CreateAsync()
    {
        var sequenceId = Guid.NewGuid();
        return new SequenceConversationServer(sequenceId, await SequenceHeadFrameFixture.EncodeBase64Async(sequenceId, headFrameId: 0));
    }

    /// <summary>A verdict shaped as the document declares it.</summary>
    internal static string Verdict(string state, bool connected, long reach, string gaps = "[]", string errata = "[]")
        => $$"""{ "state": "{{state}}", "framesReceived": {{reach}}, "expectedSize": null, "reach": {{reach}}, "gaps": {{gaps}}, "errata": {{errata}}, "connected": {{(connected ? "true" : "false")}} }""";

    /// <summary>A commit response shaped as the document declares it, with the given frame states.</summary>
    internal static string Commit(string outcome, params string[] frameStates)
    {
        var frames = string.Join(", ", frameStates.Select((state, index) =>
            $$"""{ "frameId": {{index + 1}}, "state": "{{state}}", "originalImageHash": null, "refusalName": null }"""));
        var hash = outcome == "incomplete" ? "null" : "\"sequence-hash\"";
        return $$"""{ "sequenceHash": {{hash}}, "outcome": "{{outcome}}", "sequenceRecordPublished": {{(outcome == "incomplete" ? "false" : "true")}}, "frames": [ {{frames}} ] }""";
    }

    /// <summary>The part ids of every frames request, one list per request, in order.</summary>
    internal IReadOnlyList<IReadOnlyList<long>> UploadedFrameIds()
        => FramesRequests().Select(parts => (IReadOnlyList<long>)parts.Select(part => long.Parse(part.Name, CultureInfo.InvariantCulture)).ToList()).ToList();

    // PC-104: decodes through the shared Common provider
    /// <summary>Every frames request's frames decoded back through Common, one list per request.</summary>
    internal async Task<IReadOnlyList<IReadOnlyList<DecodedSequenceFrame>>> DecodeUploadsAsync()
    {
        using var provider = CommonServiceProviderFactory.Build();
        var decoder = provider.GetRequiredService<IXioPxFrameDecoder>();
        var batches = new List<IReadOnlyList<DecodedSequenceFrame>>();
        foreach (var parts in FramesRequests())
        {
            var batch = new List<DecodedSequenceFrame>();
            foreach (var part in parts)
            {
                var read = await decoder.DecodeAsync(new XioReadPxFrameRequest(part.Body), CancellationToken.None);
                var header = Assert.IsType<PxFrameAccepted<PxFrame>>(read).Value.Header;
                batch.Add(header switch
                {
                    PxBodyHeader body => new DecodedSequenceFrame(PxFrameType.Body, body.FrameId, body.Prev, body.Next),
                    PxEndHeader end => new DecodedSequenceFrame(PxFrameType.End, end.FrameId, end.Prev, null),
                    _ => throw new InvalidOperationException($"{header.FrameType} is not a client frame."),
                });
            }

            batches.Add(batch);
        }

        return batches;
    }

    private IEnumerable<IReadOnlyList<RawMultipartPart>> FramesRequests()
        => Handler.Requests
            .Where(request => request.RequestUri.AbsolutePath.EndsWith("/frames", StringComparison.Ordinal))
            .Select(request => RawMultipartReader.Read(request.ContentType, request.Body));

    private HttpResponseMessage Respond(HttpRequestMessage request)
    {
        var path = request.RequestUri!.AbsolutePath;
        var prefix = $"/sequences/{SequenceId}";
        return (request.Method.Method, path) switch
        {
            ("POST", "/sequences") => FakeResponses.Json(
                HttpStatusCode.Created,
                $$"""{ "sequenceId": "{{SequenceId}}", "ticket": "{{Ticket}}", "headFrame": "{{_headFrameBase64}}" }"""),
            ("POST", _) when path == $"{prefix}/frames" => AnswerFrames(),
            ("GET", _) when path == $"{prefix}/progress" => FakeResponses.Json(HttpStatusCode.OK, Progress.Dequeue()),
            ("GET", _) when path == $"{prefix}/gaps" => FakeResponses.Json(HttpStatusCode.OK, GapsJson),
            ("POST", _) when path == $"{prefix}/commit" => FakeResponses.Json(HttpStatusCode.OK, Commits.Dequeue()),
            ("GET", _) when path == $"{prefix}/results" => FakeResponses.Json(
                HttpStatusCode.OK,
                """{ "sequenceHash": "sequence-hash", "outcome": "registered", "finalSize": 3, "committedAt": "2026-09-26T00:00:00Z" }"""),
            _ => throw new InvalidOperationException($"unscripted request {request.Method} {path}."),
        };
    }

    private HttpResponseMessage AnswerFrames()
    {
        var ids = UploadedFrameIds()[^1];
        var frames = string.Join(", ", ids.Select(id => $$"""{ "frameId": {{id}}, "errata": {{(ErrataFrameIds.Contains(id) ? "true" : "false")}} }"""));
        var verdict = SealingFrameId is { } sealingId && ids.Contains(sealingId) && SealingVerdictJson is { } json ? json : "null";
        return FakeResponses.Json(HttpStatusCode.Created, $$"""{ "frames": [ {{frames}} ], "verdict": {{verdict}} }""");
    }
}

// PC-104: records every report synchronously, unlike Progress<T>, which posts to a context
/// <summary>An <see cref="IProgress{T}"/> that records every report at once, in order.</summary>
internal sealed class RecordingProgress<T> : IProgress<T>
{
    internal List<T> Reports { get; } = [];

    public void Report(T value) => Reports.Add(value);
}
