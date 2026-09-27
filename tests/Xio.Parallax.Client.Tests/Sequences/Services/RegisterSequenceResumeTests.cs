namespace Xio.Parallax.Client.Tests.Sequences.Services;

// PC-104: resuming the register conversation from each state the sequence's progress answers
public sealed class RegisterSequenceResumeTests
{
    [Fact]
    public async Task Resuming_an_open_sequence_uploads_only_the_frames_in_a_gap_or_above_the_reach_then_END()
    {
        var server = await SequenceConversationServer.CreateAsync();
        server.Progress.Enqueue(SequenceConversationServer.Verdict("open", connected: false, reach: 3));
        server.GapsJson = """{ "gaps": [ { "from": 4, "to": 4, "gapFrame": "AAA=" } ] }""";
        server.SealingFrameId = 7;
        server.SealingVerdictJson = SequenceConversationServer.Verdict("sealed", connected: true, reach: 7);
        server.Commits.Enqueue(SequenceConversationServer.Commit("registered", "published"));
        using var client = RegisterSequenceTests.BuildClient(server);
        var progress = new RecordingProgress<SequenceVerdictResponse>();

        var result = await client.RegisterSequenceAsync(RegisterSequenceTests.Source(1, 2, 3, 4, 5, 6), Resume(server), progress);

        var prefix = $"/sequences/{server.SequenceId}";
        Assert.Equal(
            [$"GET {prefix}/progress", $"GET {prefix}/gaps", $"POST {prefix}/frames", $"POST {prefix}/frames", $"POST {prefix}/commit", $"GET {prefix}/results"],
            server.Calls);
        Assert.Equal([[4L, 5L, 6L], [7L]], server.UploadedFrameIds());
        var batches = await server.DecodeUploadsAsync();
        Assert.Equal(new DecodedSequenceFrame(PxFrameType.Body, 4, 3, 5), batches[0][0]);
        Assert.Equal([new DecodedSequenceFrame(PxFrameType.End, 7, 6, null)], batches[1]);
        Assert.Equal(server.Opened, result.Sequence);
        Assert.Equal(2, progress.Reports.Count);
    }

    [Fact]
    public async Task Resuming_a_sealed_sequence_uploads_only_the_gap_fills_and_sends_no_END()
    {
        var server = await SequenceConversationServer.CreateAsync();
        server.Progress.Enqueue(SequenceConversationServer.Verdict("sealed", connected: false, reach: 3, gaps: """[ { "from": 4, "to": 4 } ]"""));
        server.Progress.Enqueue(SequenceConversationServer.Verdict("sealed", connected: true, reach: 7));
        server.GapsJson = """{ "gaps": [ { "from": 4, "to": 4, "gapFrame": "AAA=" } ] }""";
        server.Commits.Enqueue(SequenceConversationServer.Commit("registered", "published"));
        using var client = RegisterSequenceTests.BuildClient(server);

        var result = await client.RegisterSequenceAsync(RegisterSequenceTests.Source(1, 2, 3, 4, 5, 6), Resume(server), progress: null);

        var prefix = $"/sequences/{server.SequenceId}";
        Assert.Equal(
            [$"GET {prefix}/progress", $"GET {prefix}/gaps", $"POST {prefix}/frames", $"GET {prefix}/progress", $"POST {prefix}/commit", $"GET {prefix}/results"],
            server.Calls);
        var batch = Assert.Single(await server.DecodeUploadsAsync());
        Assert.Equal([new DecodedSequenceFrame(PxFrameType.Body, 4, 3, 5)], batch);
        Assert.True(result.Verdict.Connected);
    }

    [Fact]
    public async Task Resuming_a_committed_sequence_sends_only_commit_and_results()
    {
        var server = await SequenceConversationServer.CreateAsync();
        server.Progress.Enqueue(SequenceConversationServer.Verdict("committed", connected: true, reach: 7));
        server.Commits.Enqueue(SequenceConversationServer.Commit("alreadyRegistered", "alreadyPublished"));
        using var client = RegisterSequenceTests.BuildClient(server);

        var result = await client.RegisterSequenceAsync(RegisterSequenceTests.Source(1, 2, 3), Resume(server), progress: null);

        var prefix = $"/sequences/{server.SequenceId}";
        Assert.Equal([$"GET {prefix}/progress", $"POST {prefix}/commit", $"GET {prefix}/results"], server.Calls);
        Assert.Equal("alreadyRegistered", result.Commit.Outcome);
        Assert.Equal("committed", result.Verdict.State);
    }

    [Fact]
    public async Task Resuming_an_abandoned_sequence_throws_naming_the_state()
    {
        var server = await SequenceConversationServer.CreateAsync();
        server.Progress.Enqueue(SequenceConversationServer.Verdict("abandoned", connected: false, reach: 2));
        using var client = RegisterSequenceTests.BuildClient(server);

        var exception = await Assert.ThrowsAsync<InvalidOperationException>(
            () => client.RegisterSequenceAsync(RegisterSequenceTests.Source(1, 2, 3), Resume(server), progress: null));

        Assert.Contains("abandoned", exception.Message, StringComparison.Ordinal);
        Assert.Equal([$"GET /sequences/{server.SequenceId}/progress"], server.Calls);
    }

    private static SequenceRegisterOptions Resume(SequenceConversationServer server)
        => RegisterSequenceTests.Options(maxFramesPerRequest: 8) with { Open = null, Existing = server.Opened };
}
