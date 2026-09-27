namespace Xio.Parallax.Client.Tests.Sequences.Services;

// PC-104: what the register conversation refuses: the options, an oversized frame, an empty source
public sealed class RegisterSequenceRefusalTests
{
    [Fact]
    public async Task Both_open_and_existing_set_throws_naming_both_before_any_request()
    {
        var server = await SequenceConversationServer.CreateAsync();
        using var client = RegisterSequenceTests.BuildClient(server);
        var options = RegisterSequenceTests.Options(maxFramesPerRequest: 8) with { Existing = server.Opened };

        var exception = await Assert.ThrowsAsync<ArgumentException>(
            () => client.RegisterSequenceAsync(RegisterSequenceTests.Source(1), options, progress: null));

        Assert.Contains("Open", exception.Message, StringComparison.Ordinal);
        Assert.Contains("Existing", exception.Message, StringComparison.Ordinal);
        Assert.Empty(server.Calls);
    }

    [Fact]
    public async Task Neither_open_nor_existing_set_throws_naming_both_before_any_request()
    {
        var server = await SequenceConversationServer.CreateAsync();
        using var client = RegisterSequenceTests.BuildClient(server);
        var options = RegisterSequenceTests.Options(maxFramesPerRequest: 8) with { Open = null };

        var exception = await Assert.ThrowsAsync<ArgumentException>(
            () => client.RegisterSequenceAsync(RegisterSequenceTests.Source(1), options, progress: null));

        Assert.Contains("Open", exception.Message, StringComparison.Ordinal);
        Assert.Contains("Existing", exception.Message, StringComparison.Ordinal);
        Assert.Empty(server.Calls);
    }

    [Fact]
    public async Task A_frame_alone_above_max_request_bytes_throws_naming_its_id_and_uploads_nothing()
    {
        var server = await SequenceConversationServer.CreateAsync();
        using var client = RegisterSequenceTests.BuildClient(server);
        var source = new FakeSequenceFrameSource([SequenceFrameInput.ForImage(1, TimeSpan.Zero, new byte[256])]);
        var options = RegisterSequenceTests.Options(maxFramesPerRequest: 8, maxRequestBytes: 64);

        var exception = await Assert.ThrowsAsync<ArgumentException>(
            () => client.RegisterSequenceAsync(source, options, progress: null));

        Assert.Contains("frame 1", exception.Message, StringComparison.Ordinal);
        Assert.Equal(["POST /sequences"], server.Calls);
    }

    [Fact]
    public async Task An_empty_source_on_a_fresh_open_throws_and_leaves_the_sequence_open()
    {
        var server = await SequenceConversationServer.CreateAsync();
        using var client = RegisterSequenceTests.BuildClient(server);

        var exception = await Assert.ThrowsAsync<InvalidOperationException>(
            () => client.RegisterSequenceAsync(RegisterSequenceTests.Source(), RegisterSequenceTests.Options(maxFramesPerRequest: 8), progress: null));

        Assert.Contains("at least one BODY", exception.Message, StringComparison.Ordinal);
        Assert.Equal(["POST /sequences"], server.Calls);
    }
}
