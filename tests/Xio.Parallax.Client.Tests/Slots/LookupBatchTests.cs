namespace Xio.Parallax.Client.Tests.Slots;

public sealed class LookupBatchTests
{
    [Fact]
    public async Task LookupBatchAsync_UploadsOnlyTheImageTheSlotIsMissing_ThenCommitsPollsAndRecoversResults()
    {
        var image1 = new ImageUpload("one.png", "image/png", new byte[] { 3, 3, 3 });
        var image2 = new ImageUpload("two.png", "image/png", new byte[] { 4, 4, 4 });
        var hash2 = Convert.ToHexStringLower(SHA256.HashData(image2.Bytes.Span));
        var progressCallCount = 0;

        var handler = new FakeHttpMessageHandler(request =>
        {
            var path = request.RequestUri!.AbsolutePath;
            if (request.Method == HttpMethod.Post && path == "/lookup/slots")
            {
                return FakeResponses.Json(HttpStatusCode.Created, "{ \"lookupSlotId\": \"lookup-1\" }");
            }

            if (request.Method == HttpMethod.Post && path == "/lookup/slots/lookup-1/queries/missing")
            {
                return FakeResponses.Json(HttpStatusCode.OK, "{ \"missing\": [\"" + hash2 + "\"] }");
            }

            if (request.Method == HttpMethod.Post && path == "/lookup/slots/lookup-1/queries")
            {
                return FakeResponses.Json(HttpStatusCode.OK, "{ \"outcomes\": [] }");
            }

            if (request.Method == HttpMethod.Post && path == "/lookup/slots/lookup-1/commit")
            {
                return FakeResponses.Json(HttpStatusCode.OK, "{ \"lookupSlotId\": \"lookup-1\", \"queries\": [] }");
            }

            if (request.Method == HttpMethod.Get && path == "/lookup/slots/lookup-1/progress")
            {
                progressCallCount++;
                var state = progressCallCount == 1 ? "retry" : "answered";
                return FakeResponses.Json(
                    HttpStatusCode.OK,
                    "{ \"slotId\": \"lookup-1\", \"status\": \"committed\", \"counts\": {}, \"entries\": [ { \"imageHash\": \"" + hash2 + "\", \"state\": \"" + state + "\" } ] }");
            }

            if (request.Method == HttpMethod.Get && path == "/lookup/slots/lookup-1/results")
            {
                return FakeResponses.Json(
                    HttpStatusCode.OK,
                    "{ \"lookupSlotId\": \"lookup-1\", \"queries\": [ { \"imageHash\": \"" + hash2 + "\", \"state\": \"answered\" } ] }");
            }

            throw new InvalidOperationException($"Unexpected request: {request.Method} {path}");
        });

        using var httpClient = new HttpClient(handler);
        var options = new ParallaxClientOptions { Batching = new UploadBatching(1_000_000, 10) };
        using var client = new ParallaxClient(options, httpClient);
        var images = new List<ImageUpload> { image1, image2 };
        var batchOptions = new LookupBatchOptions(TimeSpan.FromMilliseconds(1), TimeSpan.FromSeconds(5));

        var result = await client.LookupBatchAsync(images, batchOptions, progress: null);

        Assert.Equal("lookup-1", result.LookupSlotId);
        Assert.Equal(2, progressCallCount);
        Assert.Single(result.Results.Queries!);

        var uploadRequest = handler.Requests.Single(r => r.RequestUri.AbsolutePath == "/lookup/slots/lookup-1/queries");
        var uploadedParts = MultipartWireReader.Read(uploadRequest.ContentType, uploadRequest.Body);
        var imagePart = Assert.Single(uploadedParts);
        Assert.Equal("image", imagePart.Name);
    }

    [Fact]
    public async Task LookupBatchAsync_WithoutBatchingConfigured_RefusesBeforeSendingAnyRequest()
    {
        var handler = new FakeHttpMessageHandler(_ => throw new InvalidOperationException("No request should be sent."));
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);
        var images = new List<ImageUpload> { new("a.png", "image/png", new byte[] { 1 }) };
        var batchOptions = new LookupBatchOptions(TimeSpan.FromMilliseconds(1), TimeSpan.FromSeconds(1));

        await Assert.ThrowsAsync<ParallaxClientException>(() => client.LookupBatchAsync(images, batchOptions, progress: null));

        Assert.Empty(handler.Requests);
    }
}
