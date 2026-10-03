namespace Xio.Parallax.Client.Tests.Sequences.Services;

// PC-121: the register result keeps every BODY frame's PX frame hash it encoded, in chain order - each one the trailer
// of the very bytes the client uploaded for that frame - and END, outside the sequence hash, is not among them
public sealed class RegisterSequenceFrameHashTests
{
    [Fact]
    public async Task A_fresh_register_keeps_every_BODY_frames_hash_in_chain_order_and_not_END()
    {
        var server = await SequenceConversationServer.CreateAsync();
        server.SealingFrameId = 4;
        server.SealingVerdictJson = SequenceConversationServer.Verdict("sealed", connected: true, reach: 4);
        server.Commits.Enqueue(SequenceConversationServer.Commit("registered", "published", "published", "published"));
        using var client = RegisterSequenceTests.BuildClient(server);

        var result = await client.RegisterSequenceAsync(
            RegisterSequenceTests.Source(1, 2, 3),
            RegisterSequenceTests.Options(maxFramesPerRequest: 2),
            progress: null);

        Assert.Equal([1L, 2L, 3L], result.EncodedFrameHashes.Select(hash => hash.FrameId));
        AssertEachHashIsItsUploadedTrailer(server, result);
    }

    [Fact]
    public async Task Resuming_an_open_sequence_keeps_only_the_frames_this_run_sent()
    {
        var server = await SequenceConversationServer.CreateAsync();
        server.Progress.Enqueue(SequenceConversationServer.Verdict("open", connected: false, reach: 3));
        server.GapsJson = """{ "gaps": [] }""";
        server.SealingFrameId = 7;
        server.SealingVerdictJson = SequenceConversationServer.Verdict("sealed", connected: true, reach: 7);
        server.Commits.Enqueue(SequenceConversationServer.Commit("registered", "published"));
        using var client = RegisterSequenceTests.BuildClient(server);

        var result = await client.RegisterSequenceAsync(RegisterSequenceTests.Source(1, 2, 3, 4, 5, 6), Resume(server), progress: null);

        Assert.Equal([4L, 5L, 6L], result.EncodedFrameHashes.Select(hash => hash.FrameId));
        AssertEachHashIsItsUploadedTrailer(server, result);
    }

    [Fact]
    public async Task Resuming_a_committed_sequence_keeps_no_frame_hash()
    {
        var server = await SequenceConversationServer.CreateAsync();
        server.Progress.Enqueue(SequenceConversationServer.Verdict("committed", connected: true, reach: 7));
        server.Commits.Enqueue(SequenceConversationServer.Commit("alreadyRegistered", "alreadyPublished"));
        using var client = RegisterSequenceTests.BuildClient(server);

        var result = await client.RegisterSequenceAsync(RegisterSequenceTests.Source(1, 2, 3), Resume(server), progress: null);

        Assert.Empty(result.EncodedFrameHashes);
    }

    // PC-121: a PX frame ends with its own 32-byte frame hash, so each kept hash is checked against the bytes that went up
    private static void AssertEachHashIsItsUploadedTrailer(SequenceConversationServer server, SequenceRegisterResult result)
    {
        var uploaded = server.UploadedFrames().ToDictionary(frame => frame.FrameId, frame => frame.Bytes);
        Assert.All(result.EncodedFrameHashes, kept =>
        {
            var bytes = uploaded[kept.FrameId];
            Assert.Equal(32, kept.FrameHash.Length);
            Assert.Equal(bytes.AsSpan(bytes.Length - 32).ToArray(), kept.FrameHash.ToArray());
        });
    }

    private static SequenceRegisterOptions Resume(SequenceConversationServer server)
        => RegisterSequenceTests.Options(maxFramesPerRequest: 8) with { Open = null, Existing = server.Opened };
}
