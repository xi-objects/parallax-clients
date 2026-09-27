namespace Xio.Parallax.Client.Tests.Sequences.Services;

// PC-103: UploadSequenceFramesAsync sends one octet-stream part per frame, in order, under the
// ticket header; RemoveSequenceFrameAsync deletes one BODY member under the same header
public sealed class ParallaxClientSequencesFramesTests : IDisposable
{
    private readonly SequenceFrameEncoder _encoder = new();

    [Fact]
    public async Task UploadSequenceFramesAsync_SendsOneOctetStreamPartPerFrameInOrder_UnderTheTicketHeader()
    {
        var sequenceId = Guid.NewGuid();
        var handle = new SequenceHandle(sequenceId, "sequence-ticket-frames");
        var frame1 = await _encoder.EncodeBodyAsync(sequenceId, SequenceFrameInput.ForImage(1, TimeSpan.Zero, new byte[] { 1, 2, 3 }), prev: 0, next: 2, CancellationToken.None);
        var frame2 = await _encoder.EncodeBodyAsync(sequenceId, SequenceFrameInput.ForImage(2, TimeSpan.FromSeconds(1), new byte[] { 4, 5 }), prev: 1, next: 3, CancellationToken.None);

        var handler = new FakeHttpMessageHandler(request =>
        {
            Assert.Equal($"/sequences/{sequenceId}/frames", request.RequestUri!.AbsolutePath);
            Assert.Equal(HttpMethod.Post, request.Method);
            return FakeResponses.Json(
                HttpStatusCode.Created,
                """{ "frames": [ { "frameId": 1, "errata": false }, { "frameId": 2, "errata": false } ] }""");
        });
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);

        var response = await client.UploadSequenceFramesAsync(handle, new[] { frame1, frame2 });

        Assert.Equal(2, response.Frames!.Count);
        Assert.Null(response.Verdict);

        var uploadRequest = Assert.Single(handler.Requests);
        var ticketValues = Assert.Single(uploadRequest.Headers, header => header.Key.Equals("X-Sequence-Ticket", StringComparison.OrdinalIgnoreCase));
        Assert.Equal("sequence-ticket-frames", Assert.Single(ticketValues.Value));

        var parts = RawMultipartReader.Read(uploadRequest.ContentType, uploadRequest.Body);
        Assert.Collection(
            parts,
            part =>
            {
                Assert.Equal("1", part.Name);
                Assert.Equal("application/octet-stream", part.ContentType);
                Assert.Equal(frame1.Bytes.ToArray(), part.Body);
            },
            part =>
            {
                Assert.Equal("2", part.Name);
                Assert.Equal("application/octet-stream", part.ContentType);
                Assert.Equal(frame2.Bytes.ToArray(), part.Body);
            });

        var ticketBytes = Encoding.UTF8.GetBytes(handle.Ticket);
        Assert.True(IndexOfSequence(uploadRequest.Body, ticketBytes) < 0, "the ticket must never appear in the request body.");
    }

    [Fact]
    public async Task UploadSequenceFramesAsync_ReturnsTheVerdictWhenTheBatchSealsTheSequence()
    {
        var sequenceId = Guid.NewGuid();
        var handle = new SequenceHandle(sequenceId, "t");
        var frame = await _encoder.EncodeEndAsync(sequenceId, frameId: 3, prev: 2, CancellationToken.None);

        var handler = new FakeHttpMessageHandler(_ => FakeResponses.Json(
            HttpStatusCode.Created,
            """{ "frames": [ { "frameId": 3, "errata": false } ], "verdict": { "state": "sealed", "connected": true, "gaps": [], "errata": [] } }"""));
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);

        var response = await client.UploadSequenceFramesAsync(handle, new[] { frame });

        Assert.NotNull(response.Verdict);
        Assert.Equal("sealed", response.Verdict!.State);
        Assert.True(response.Verdict.Connected);
    }

    [Fact]
    public async Task UploadSequenceFramesAsync_RefusesAnEmptyList_BeforeSendingAnyRequest()
    {
        var handler = new FakeHttpMessageHandler(_ => throw new InvalidOperationException("No request should be sent."));
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);
        var handle = new SequenceHandle(Guid.NewGuid(), "t");

        var exception = await Assert.ThrowsAsync<ArgumentException>(
            () => client.UploadSequenceFramesAsync(handle, Array.Empty<EncodedFrame>()));

        Assert.Equal("frames", exception.ParamName);
        Assert.Empty(handler.Requests);
    }

    [Fact]
    public async Task UploadSequenceFramesAsync_WhenTheSequenceRefusesTheBatch_ThrowsTheTypedProblem()
    {
        var sequenceId = Guid.NewGuid();
        var handle = new SequenceHandle(sequenceId, "t");
        var frame = await _encoder.EncodeBodyAsync(sequenceId, SequenceFrameInput.ForImage(1, TimeSpan.Zero, new byte[] { 9 }), prev: 0, next: 2, CancellationToken.None);

        var handler = new FakeHttpMessageHandler(_ => FakeResponses.Problem(
            HttpStatusCode.Conflict,
            """{ "type": "urn:xio:parallax:problem:sequence-not-open", "title": "Not open", "status": 409 }"""));
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);

        var exception = await Assert.ThrowsAsync<ParallaxProblemException>(
            () => client.UploadSequenceFramesAsync(handle, new[] { frame }));

        Assert.Equal(409, exception.Status);
        Assert.Equal("sequence-not-open", exception.Slug);
    }

    [Fact]
    public async Task RemoveSequenceFrameAsync_DeletesTheGivenFrame_UnderTheTicketHeader()
    {
        var sequenceId = Guid.NewGuid();
        var handle = new SequenceHandle(sequenceId, "sequence-ticket-remove");

        var handler = new FakeHttpMessageHandler(request =>
        {
            Assert.Equal($"/sequences/{sequenceId}/frames/7", request.RequestUri!.AbsolutePath);
            Assert.Equal(HttpMethod.Delete, request.Method);
            return new HttpResponseMessage(HttpStatusCode.NoContent);
        });
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);

        await client.RemoveSequenceFrameAsync(handle, frameId: 7);

        var deleteRequest = Assert.Single(handler.Requests);
        var ticketValues = Assert.Single(deleteRequest.Headers, header => header.Key.Equals("X-Sequence-Ticket", StringComparison.OrdinalIgnoreCase));
        Assert.Equal("sequence-ticket-remove", Assert.Single(ticketValues.Value));
    }

    public void Dispose() => _encoder.Dispose();

    private static int IndexOfSequence(byte[] haystack, byte[] needle)
    {
        if (needle.Length == 0 || needle.Length > haystack.Length)
        {
            return -1;
        }

        for (var i = 0; i <= haystack.Length - needle.Length; i++)
        {
            var found = true;
            for (var j = 0; j < needle.Length; j++)
            {
                if (haystack[i + j] != needle[j])
                {
                    found = false;
                    break;
                }
            }

            if (found)
            {
                return i;
            }
        }

        return -1;
    }
}
