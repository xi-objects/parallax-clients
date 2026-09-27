namespace Xio.Parallax.Client.Tests.Sequences.Services;

// PC-104: the fresh register conversation: batching, links, END, the verdict, errata, the refused verdict, commit retries
// PC-104: batching by the whole request body's bytes, a verdict-less END refused, errata refused before commit
public sealed class RegisterSequenceTests
{
    private static readonly SequenceOpenRequest OpenRequest = new(Array.Empty<ManifestPart>(), ExpectedSize: null);

    [Fact]
    public async Task Three_frames_under_two_per_request_upload_as_two_batches_then_END_then_commit_and_results()
    {
        var server = await SequenceConversationServer.CreateAsync();
        server.SealingFrameId = 4;
        server.SealingVerdictJson = SequenceConversationServer.Verdict("sealed", connected: true, reach: 4);
        server.Commits.Enqueue(SequenceConversationServer.Commit("registered", "published", "published", "published"));
        using var client = BuildClient(server);
        var progress = new RecordingProgress<SequenceVerdictResponse>();

        var result = await client.RegisterSequenceAsync(Source(1, 2, 3), Options(maxFramesPerRequest: 2), progress);

        var prefix = $"/sequences/{server.SequenceId}";
        Assert.Equal(
            ["POST /sequences", $"POST {prefix}/frames", $"POST {prefix}/frames", $"POST {prefix}/frames", $"POST {prefix}/commit", $"GET {prefix}/results"],
            server.Calls);
        Assert.DoesNotContain(server.Handler.Requests[0].Headers.Keys, name => name.Equals(SequenceConversationServer.TicketHeaderName, StringComparison.OrdinalIgnoreCase));
        Assert.All(server.Handler.Requests.Skip(1), request =>
            Assert.Equal(SequenceConversationServer.Ticket, Assert.Single(request.Headers[SequenceConversationServer.TicketHeaderName])));

        var batches = await server.DecodeUploadsAsync();
        Assert.Equal(3, batches.Count);
        Assert.Equal(
            [new DecodedSequenceFrame(PxFrameType.Body, 1, 0, 2), new DecodedSequenceFrame(PxFrameType.Body, 2, 1, 3)],
            batches[0]);
        Assert.Equal([new DecodedSequenceFrame(PxFrameType.Body, 3, 2, 4)], batches[1]);
        Assert.Equal([new DecodedSequenceFrame(PxFrameType.End, 4, 3, null)], batches[2]);

        Assert.Equal(server.Opened, result.Sequence);
        Assert.True(result.Verdict.Connected);
        Assert.Equal("registered", result.Commit.Outcome);
        Assert.Equal("registered", result.Results.Outcome);
        Assert.Same(result.Verdict, Assert.Single(progress.Reports));
    }

    // PC-104: the byte cap, not the count, splits the batches, at exactly the whole body's length
    [Fact]
    public async Task The_request_byte_cap_splits_batches_at_the_whole_multipart_body_length()
    {
        var calibration = await RunToResultsAsync(maxFramesPerRequest: 2, maxRequestBytes: 1_000_000);
        var twoFrameBody = calibration.Handler.Requests.First(IsFramesRequest).Body.Length;

        var atTheBound = await RunToResultsAsync(maxFramesPerRequest: 8, maxRequestBytes: twoFrameBody);

        Assert.Equal([[1L, 2L], [3L], [4L]], atTheBound.UploadedFrameIds());
        Assert.Equal(twoFrameBody, atTheBound.Handler.Requests.First(IsFramesRequest).Body.Length);
        Assert.All(atTheBound.Handler.Requests.Where(IsFramesRequest), request => Assert.True(request.Body.Length <= twoFrameBody));

        var belowTheBound = await RunToResultsAsync(maxFramesPerRequest: 8, maxRequestBytes: twoFrameBody - 1);

        Assert.Equal([[1L], [2L], [3L], [4L]], belowTheBound.UploadedFrameIds());
        Assert.All(belowTheBound.Handler.Requests.Where(IsFramesRequest), request => Assert.True(request.Body.Length <= twoFrameBody - 1));
    }

    // PC-104: an END batch answered without a verdict did not seal; the conversation refuses, naming END, and commits nothing
    [Fact]
    public async Task An_END_batch_answered_without_a_verdict_throws_naming_the_END_id_and_commits_nothing()
    {
        var server = await SequenceConversationServer.CreateAsync();
        using var client = BuildClient(server);
        var progress = new RecordingProgress<SequenceVerdictResponse>();

        var exception = await Assert.ThrowsAsync<ParallaxClientException>(
            () => client.RegisterSequenceAsync(Source(1), Options(maxFramesPerRequest: 2), progress));

        Assert.Contains("END frame 2", exception.Message, StringComparison.Ordinal);
        var prefix = $"/sequences/{server.SequenceId}";
        Assert.Equal(["POST /sequences", $"POST {prefix}/frames", $"POST {prefix}/frames"], server.Calls);
        Assert.Empty(progress.Reports);
    }

    // PC-104: errata refuse before commit, as the server's commit does: the verdict carries them and nothing is committed
    [Fact]
    public async Task A_sealing_verdict_naming_errata_throws_the_verdict_with_them_and_commits_nothing()
    {
        var server = await SequenceConversationServer.CreateAsync();
        server.ErrataFrameIds.Add(2);
        server.SealingFrameId = 4;
        server.SealingVerdictJson = SequenceConversationServer.Verdict(
            "sealed",
            connected: true,
            reach: 4,
            errata: """[ { "frameId": 2, "originalImageHash": "original-image-hash-2" } ]""");
        using var client = BuildClient(server);

        var exception = await Assert.ThrowsAsync<SequenceVerdictException>(
            () => client.RegisterSequenceAsync(Source(1, 2, 3), Options(maxFramesPerRequest: 8), progress: null));

        var errata = Assert.Single(exception.Verdict.Errata!);
        Assert.Equal(2, errata.FrameId);
        Assert.Equal("original-image-hash-2", errata.OriginalImageHash);
        Assert.Contains("1 errata", exception.Message, StringComparison.Ordinal);
        Assert.DoesNotContain(server.Calls, call => call.EndsWith("/commit", StringComparison.Ordinal));
    }

    [Fact]
    public async Task A_sealing_verdict_with_a_gap_throws_the_verdict_and_commits_nothing()
    {
        var server = await SequenceConversationServer.CreateAsync();
        server.SealingFrameId = 4;
        server.SealingVerdictJson = SequenceConversationServer.Verdict("sealed", connected: false, reach: 1, gaps: """[ { "from": 2, "to": 2 } ]""");
        using var client = BuildClient(server);

        var exception = await Assert.ThrowsAsync<SequenceVerdictException>(
            () => client.RegisterSequenceAsync(Source(1, 2, 3), Options(maxFramesPerRequest: 8), progress: null));

        var gap = Assert.Single(exception.Verdict.Gaps!);
        Assert.Equal(2, gap.From);
        Assert.DoesNotContain(server.Calls, call => call.EndsWith("/commit", StringComparison.Ordinal));
    }

    [Fact]
    public async Task An_incomplete_commit_is_called_again_after_the_poll_interval_until_registered()
    {
        var server = await SequenceConversationServer.CreateAsync();
        server.SealingFrameId = 2;
        server.SealingVerdictJson = SequenceConversationServer.Verdict("sealed", connected: true, reach: 2);
        server.Commits.Enqueue(SequenceConversationServer.Commit("incomplete", "notPublished"));
        server.Commits.Enqueue(SequenceConversationServer.Commit("registered", "published"));
        using var client = BuildClient(server);

        var result = await client.RegisterSequenceAsync(Source(1), Options(maxFramesPerRequest: 8, commitAttempts: 2), progress: null);

        Assert.Equal("registered", result.Commit.Outcome);
        Assert.Equal(2, server.Calls.Count(call => call.EndsWith("/commit", StringComparison.Ordinal)));
        Assert.EndsWith("/results", server.Calls[^1], StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_commit_still_incomplete_after_every_attempt_throws_the_commit_after_exactly_that_many_calls()
    {
        var server = await SequenceConversationServer.CreateAsync();
        server.SealingFrameId = 3;
        server.SealingVerdictJson = SequenceConversationServer.Verdict("sealed", connected: true, reach: 3);
        server.Commits.Enqueue(SequenceConversationServer.Commit("incomplete", "published", "notPublished"));
        server.Commits.Enqueue(SequenceConversationServer.Commit("incomplete", "published", "notPublished"));
        using var client = BuildClient(server);

        var exception = await Assert.ThrowsAsync<SequenceCommitException>(
            () => client.RegisterSequenceAsync(Source(1, 2), Options(maxFramesPerRequest: 8, commitAttempts: 2), progress: null));

        Assert.Equal("incomplete", exception.Commit.Outcome);
        Assert.Equal(2, server.Calls.Count(call => call.EndsWith("/commit", StringComparison.Ordinal)));
        Assert.DoesNotContain(server.Calls, call => call.EndsWith("/results", StringComparison.Ordinal));
        Assert.DoesNotContain(SequenceConversationServer.Ticket, exception.Message, StringComparison.Ordinal);
    }

    // PC-104: a fresh server scripted to seal 1, 2, 3 with END 4 and register, run through to results under the given caps
    private static async Task<SequenceConversationServer> RunToResultsAsync(int maxFramesPerRequest, long maxRequestBytes)
    {
        var server = await SequenceConversationServer.CreateAsync();
        server.SealingFrameId = 4;
        server.SealingVerdictJson = SequenceConversationServer.Verdict("sealed", connected: true, reach: 4);
        server.Commits.Enqueue(SequenceConversationServer.Commit("registered", "published", "published", "published"));
        using var client = BuildClient(server);
        await client.RegisterSequenceAsync(Source(1, 2, 3), Options(maxFramesPerRequest, maxRequestBytes: maxRequestBytes), progress: null);
        return server;
    }

    // PC-104: whether a recorded request is a frames upload
    private static bool IsFramesRequest(RecordedHttpRequest request)
        => request.RequestUri.AbsolutePath.EndsWith("/frames", StringComparison.Ordinal);

    internal static ParallaxClient BuildClient(SequenceConversationServer server)
        => new(new ParallaxClientOptions(), new HttpClient(server.Handler));

    internal static FakeSequenceFrameSource Source(params long[] frameIds)
        => new(frameIds.Select(id => SequenceFrameInput.ForImage(id, TimeSpan.FromMilliseconds(40 * id), new byte[] { (byte)id, 7, 7 })).ToList());

    internal static SequenceRegisterOptions Options(int maxFramesPerRequest, int commitAttempts = 1, long maxRequestBytes = 1_000_000)
        => new(TimeSpan.FromMilliseconds(1), commitAttempts, new SequenceBatching(maxRequestBytes, maxFramesPerRequest)) { Open = OpenRequest };
}
