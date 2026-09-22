namespace Xio.Parallax.Client.Tests.Slots;

public sealed class RegisterBatchTests
{
    [Fact]
    public async Task RegisterBatchAsync_UploadsOnlyTheImageTheSlotIsMissing_ThenCommitsAndPollsToATerminalState()
    {
        var image1 = new ImageUpload("one.png", "image/png", new byte[] { 1, 1, 1 });
        var image2 = new ImageUpload("two.png", "image/png", new byte[] { 2, 2, 2 });
        var hash2 = Convert.ToHexStringLower(SHA256.HashData(image2.Bytes.Span));
        var progressCallCount = 0;

        var handler = new FakeHttpMessageHandler(request =>
        {
            var path = request.RequestUri!.AbsolutePath;
            if (request.Method == HttpMethod.Post && path == "/slots")
            {
                return FakeResponses.Json(HttpStatusCode.Created, "{ \"slotId\": \"slot-1\" }");
            }

            if (request.Method == HttpMethod.Post && path == "/slots/slot-1/uploads/missing")
            {
                return FakeResponses.Json(HttpStatusCode.OK, "{ \"missing\": [\"" + hash2 + "\"] }");
            }

            if (request.Method == HttpMethod.Post && path == "/slots/slot-1/uploads")
            {
                return FakeResponses.Json(
                    HttpStatusCode.OK,
                    "{ \"outcomes\": [ { \"partIndex\": 0, \"fileName\": \"two.png\", \"accepted\": true, \"imageHash\": \"" + hash2 + "\" } ] }");
            }

            if (request.Method == HttpMethod.Post && path == "/slots/slot-1/commit")
            {
                return FakeResponses.Json(HttpStatusCode.OK, "{ \"slotId\": \"slot-1\", \"status\": \"committed\", \"entries\": [] }");
            }

            if (request.Method == HttpMethod.Get && path == "/slots/slot-1/progress")
            {
                progressCallCount++;
                var state = progressCallCount == 1 ? "retry" : "registered";
                return FakeResponses.Json(
                    HttpStatusCode.OK,
                    "{ \"slotId\": \"slot-1\", \"status\": \"committed\", \"counts\": {}, \"entries\": [ { \"imageHash\": \"" + hash2 + "\", \"state\": \"" + state + "\" } ] }");
            }

            throw new InvalidOperationException($"Unexpected request: {request.Method} {path}");
        });

        using var httpClient = new HttpClient(handler);
        var options = new ParallaxClientOptions { Batching = new UploadBatching(1_000_000, 10) };
        using var client = new ParallaxClient(options, httpClient);
        var items = new List<RegistrationItem>
        {
            new(image1, Array.Empty<ManifestPart>()),
            new(image2, Array.Empty<ManifestPart>()),
        };
        var batchOptions = new RegisterBatchOptions(TimeSpan.FromMilliseconds(1), TimeSpan.FromSeconds(5));

        var result = await client.RegisterBatchAsync(items, batchOptions, progress: null);

        Assert.Equal("slot-1", result.SlotId);
        Assert.Equal(2, progressCallCount);
        Assert.Equal("registered", Assert.Single(result.FinalProgress.Entries!).State);

        var uploadRequest = handler.Requests.Single(r => r.RequestUri.AbsolutePath == "/slots/slot-1/uploads");
        var uploadedParts = MultipartWireReader.Read(uploadRequest.ContentType, uploadRequest.Body);
        var imagePart = Assert.Single(uploadedParts);
        Assert.Equal("image", imagePart.Name);
    }

    [Fact]
    public async Task RegisterBatchAsync_WithoutBatchingConfigured_RefusesBeforeSendingAnyRequest()
    {
        var handler = new FakeHttpMessageHandler(_ => throw new InvalidOperationException("No request should be sent."));
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);
        var items = new List<RegistrationItem>
        {
            new(new ImageUpload("a.png", "image/png", new byte[] { 1 }), Array.Empty<ManifestPart>()),
        };
        var batchOptions = new RegisterBatchOptions(TimeSpan.FromMilliseconds(1), TimeSpan.FromSeconds(1));

        await Assert.ThrowsAsync<ParallaxClientException>(() => client.RegisterBatchAsync(items, batchOptions, progress: null));

        Assert.Empty(handler.Requests);
    }

    [Fact]
    public async Task RegisterBatchAsync_WhenProgressNeverLeavesRetry_ThrowsOncePollTimeoutElapses()
    {
        var image = new ImageUpload("a.png", "image/png", new byte[] { 7 });
        var hash = Convert.ToHexStringLower(SHA256.HashData(image.Bytes.Span));

        var handler = new FakeHttpMessageHandler(request =>
        {
            var path = request.RequestUri!.AbsolutePath;
            if (path == "/slots" && request.Method == HttpMethod.Post)
            {
                return FakeResponses.Json(HttpStatusCode.Created, "{ \"slotId\": \"slot-timeout\" }");
            }

            if (path == "/slots/slot-timeout/uploads/missing")
            {
                return FakeResponses.Json(HttpStatusCode.OK, "{ \"missing\": [\"" + hash + "\"] }");
            }

            if (path == "/slots/slot-timeout/uploads")
            {
                return FakeResponses.Json(HttpStatusCode.OK, "{ \"outcomes\": [] }");
            }

            if (path == "/slots/slot-timeout/commit")
            {
                return FakeResponses.Json(HttpStatusCode.OK, "{ \"slotId\": \"slot-timeout\", \"status\": \"committed\", \"entries\": [] }");
            }

            if (path == "/slots/slot-timeout/progress")
            {
                return FakeResponses.Json(
                    HttpStatusCode.OK,
                    "{ \"slotId\": \"slot-timeout\", \"status\": \"committed\", \"counts\": {}, \"entries\": [ { \"imageHash\": \"" + hash + "\", \"state\": \"retry\" } ] }");
            }

            throw new InvalidOperationException($"Unexpected request: {request.Method} {path}");
        });

        using var httpClient = new HttpClient(handler);
        var options = new ParallaxClientOptions { Batching = new UploadBatching(1_000_000, 10) };
        using var client = new ParallaxClient(options, httpClient);
        var items = new List<RegistrationItem> { new(image, Array.Empty<ManifestPart>()) };
        var batchOptions = new RegisterBatchOptions(TimeSpan.FromMilliseconds(5), TimeSpan.FromMilliseconds(50));

        await Assert.ThrowsAsync<ParallaxClientException>(() => client.RegisterBatchAsync(items, batchOptions, progress: null));
    }
}
