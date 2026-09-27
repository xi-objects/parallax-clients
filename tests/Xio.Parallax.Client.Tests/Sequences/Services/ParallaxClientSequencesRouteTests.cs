namespace Xio.Parallax.Client.Tests.Sequences.Services;

// PC-103: every route past open (gaps, progress, expected-size, commit, results, abandon) sends
// its own method and path, carries the ticket header, and maps its response through the
// generated request builder
public sealed class ParallaxClientSequencesRouteTests
{
    private const string TicketHeaderName = "X-Sequence-Ticket";

    [Fact]
    public async Task GetSequenceGapsAsync_SendsGetGaps_UnderTheTicketHeader_AndMapsTheResponse()
    {
        var handle = new SequenceHandle(Guid.NewGuid(), "sequence-ticket-gaps");
        var handler = CreateHandler(HttpMethod.Get, $"/sequences/{handle.SequenceId}/gaps", FakeResponses.Json(
            HttpStatusCode.OK,
            """{ "gaps": [ { "from": 2, "to": 4, "gapFrame": "AAA=" } ] }"""));
        using var client = BuildClient(handler);

        var response = await client.GetSequenceGapsAsync(handle);

        Assert.Single(response.Gaps!);
        Assert.Equal(2, response.Gaps![0].From);
        Assert.Equal(4, response.Gaps[0].To);
        AssertTicketHeaderSent(handler, "sequence-ticket-gaps");
    }

    [Fact]
    public async Task GetSequenceProgressAsync_SendsGetProgress_UnderTheTicketHeader_AndMapsTheResponse()
    {
        var handle = new SequenceHandle(Guid.NewGuid(), "sequence-ticket-progress");
        var handler = CreateHandler(HttpMethod.Get, $"/sequences/{handle.SequenceId}/progress", FakeResponses.Json(
            HttpStatusCode.OK,
            """{ "state": "open", "framesReceived": 3, "reach": 3, "connected": false, "gaps": [], "errata": [] }"""));
        using var client = BuildClient(handler);

        var response = await client.GetSequenceProgressAsync(handle);

        Assert.Equal("open", response.State);
        Assert.Equal(3, response.FramesReceived);
        AssertTicketHeaderSent(handler, "sequence-ticket-progress");
    }

    [Fact]
    public async Task AmendSequenceExpectedSizeAsync_SendsPutExpectedSize_UnderTheTicketHeader()
    {
        var handle = new SequenceHandle(Guid.NewGuid(), "sequence-ticket-amend");
        var handler = CreateHandler(HttpMethod.Put, $"/sequences/{handle.SequenceId}/expected-size", new HttpResponseMessage(HttpStatusCode.NoContent));
        using var client = BuildClient(handler);

        await client.AmendSequenceExpectedSizeAsync(handle, 99);

        var request = Assert.Single(handler.Requests);
        using var document = JsonDocument.Parse(request.Body);
        Assert.Equal(99, document.RootElement.GetProperty("expectedSize").GetInt32());
        AssertTicketHeaderSent(handler, "sequence-ticket-amend");
    }

    [Theory]
    [InlineData(0)]
    [InlineData(-1)]
    public async Task AmendSequenceExpectedSizeAsync_RefusesANonPositiveSize_BeforeSendingAnyRequest(long expectedSize)
    {
        var handler = new FakeHttpMessageHandler(_ => throw new InvalidOperationException("No request should be sent."));
        using var client = BuildClient(handler);
        var handle = new SequenceHandle(Guid.NewGuid(), "t");

        await Assert.ThrowsAsync<ArgumentOutOfRangeException>(() => client.AmendSequenceExpectedSizeAsync(handle, expectedSize));

        Assert.Empty(handler.Requests);
    }

    [Fact]
    public async Task CommitSequenceAsync_SendsPostCommit_UnderTheTicketHeader_AndMapsTheResponse()
    {
        var handle = new SequenceHandle(Guid.NewGuid(), "sequence-ticket-commit");
        var handler = CreateHandler(HttpMethod.Post, $"/sequences/{handle.SequenceId}/commit", FakeResponses.Json(
            HttpStatusCode.OK,
            """{ "outcome": "registered", "sequenceHash": "abc123", "sequenceRecordPublished": true, "frames": [] }"""));
        using var client = BuildClient(handler);

        var response = await client.CommitSequenceAsync(handle);

        Assert.Equal("registered", response.Outcome);
        Assert.Equal("abc123", response.SequenceHash);
        AssertTicketHeaderSent(handler, "sequence-ticket-commit");
    }

    [Fact]
    public async Task CommitSequenceAsync_WhenTheSequenceHasShortfalls_ThrowsTheTypedProblem()
    {
        var handle = new SequenceHandle(Guid.NewGuid(), "sequence-ticket-commit-409");
        var handler = CreateHandler(HttpMethod.Post, $"/sequences/{handle.SequenceId}/commit", FakeResponses.Problem(
            HttpStatusCode.Conflict,
            """{ "type": "urn:xio:parallax:problem:sequence-not-committable", "title": "Not committable", "status": 409 }"""));
        using var client = BuildClient(handler);

        var exception = await Assert.ThrowsAsync<ParallaxProblemException>(() => client.CommitSequenceAsync(handle));

        Assert.Equal(409, exception.Status);
        Assert.Equal("sequence-not-committable", exception.Slug);
    }

    [Fact]
    public async Task GetSequenceResultsAsync_SendsGetResults_UnderTheTicketHeader_AndMapsTheResponse()
    {
        var handle = new SequenceHandle(Guid.NewGuid(), "sequence-ticket-results");
        var handler = CreateHandler(HttpMethod.Get, $"/sequences/{handle.SequenceId}/results", FakeResponses.Json(
            HttpStatusCode.OK,
            """{ "outcome": "alreadyRegistered", "sequenceHash": "def456", "finalSize": 10, "committedAt": "2026-09-26T00:00:00Z" }"""));
        using var client = BuildClient(handler);

        var response = await client.GetSequenceResultsAsync(handle);

        Assert.Equal("alreadyRegistered", response.Outcome);
        Assert.Equal(10, response.FinalSize);
        AssertTicketHeaderSent(handler, "sequence-ticket-results");
    }

    [Fact]
    public async Task AbandonSequenceAsync_SendsDeleteSequence_UnderTheTicketHeader_AndMapsTheResponse()
    {
        var handle = new SequenceHandle(Guid.NewGuid(), "sequence-ticket-abandon");
        var handler = CreateHandler(HttpMethod.Delete, $"/sequences/{handle.SequenceId}", FakeResponses.Json(
            HttpStatusCode.OK,
            $$"""{ "sequenceId": "{{handle.SequenceId}}", "state": "abandoned", "packetsPurged": 4 }"""));
        using var client = BuildClient(handler);

        var response = await client.AbandonSequenceAsync(handle);

        Assert.Equal("abandoned", response.State);
        Assert.Equal(4, response.PacketsPurged);
        AssertTicketHeaderSent(handler, "sequence-ticket-abandon");
    }

    private static FakeHttpMessageHandler CreateHandler(HttpMethod expectedMethod, string expectedPath, HttpResponseMessage response)
    {
        return new FakeHttpMessageHandler(request =>
        {
            Assert.Equal(expectedMethod, request.Method);
            Assert.Equal(expectedPath, request.RequestUri!.AbsolutePath);
            return response;
        });
    }

    private static ParallaxClient BuildClient(FakeHttpMessageHandler handler)
        => new(new ParallaxClientOptions(), new HttpClient(handler));

    private static void AssertTicketHeaderSent(FakeHttpMessageHandler handler, string expectedTicket)
    {
        var request = Assert.Single(handler.Requests);
        var ticketHeader = Assert.Single(request.Headers, header => header.Key.Equals(TicketHeaderName, StringComparison.OrdinalIgnoreCase));
        Assert.Equal(expectedTicket, Assert.Single(ticketHeader.Value));
    }
}
