namespace Xio.Parallax.Client.Tests.Slots;

public sealed class LookupBatchTests
{
    [Fact]
    public async Task LookupBatchAsync_UploadsOnlyTheImageTheSlotIsMissing_ThenCommitAnswersTheResultsWithoutPolling()
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
                return FakeResponses.Json(
                    HttpStatusCode.OK,
                    "{ \"lookupSlotId\": \"lookup-1\", \"queries\": [ { \"imageHash\": \"" + hash2 + "\", \"state\": \"retry\" } ] }");
            }

            if (request.Method == HttpMethod.Get && path == "/lookup/slots/lookup-1/progress")
            {
                progressCallCount++;
                return FakeResponses.Json(
                    HttpStatusCode.OK,
                    "{ \"slotId\": \"lookup-1\", \"status\": \"committed\", \"counts\": {}, \"entries\": [ { \"imageHash\": \"" + hash2 + "\", \"state\": \"retry\" } ] }");
            }

            throw new InvalidOperationException($"Unexpected request: {request.Method} {path}");
        });

        using var httpClient = new HttpClient(handler);
        var options = new ParallaxClientOptions { Batching = new UploadBatching(1_000_000, 10) };
        using var client = new ParallaxClient(options, httpClient);
        var images = new List<ImageUpload> { image1, image2 };
        var batchOptions = new LookupBatchOptions();

        var result = await client.LookupBatchAsync(images, batchOptions, progress: null);

        Assert.Equal("lookup-1", result.LookupSlotId);
        Assert.Equal(1, progressCallCount);
        Assert.DoesNotContain(handler.Requests, r => r.RequestUri.AbsolutePath == "/lookup/slots/lookup-1/results");
        var query = Assert.Single(result.Results.Queries!);
        Assert.Equal(hash2, query.ImageHash);
        Assert.Equal("retry", query.State);

        var uploadRequest = handler.Requests.Single(r => r.RequestUri.AbsolutePath == "/lookup/slots/lookup-1/queries");
        var uploadedParts = MultipartWireReader.Read(uploadRequest.ContentType, uploadRequest.Body);
        var imagePart = Assert.Single(uploadedParts);
        Assert.Equal("image", imagePart.Name);
    }

    [Fact]
    public async Task LookupBatchAsync_WhenCommitResponseBodyIsEmpty_ReadsResultsOnceInstead()
    {
        var image = new ImageUpload("a.png", "image/png", new byte[] { 9, 9, 9 });
        var hash = Convert.ToHexStringLower(SHA256.HashData(image.Bytes.Span));
        var resultsCallCount = 0;

        var handler = new FakeHttpMessageHandler(request =>
        {
            var path = request.RequestUri!.AbsolutePath;
            if (request.Method == HttpMethod.Post && path == "/lookup/slots")
            {
                return FakeResponses.Json(HttpStatusCode.Created, "{ \"lookupSlotId\": \"lookup-2\" }");
            }

            if (request.Method == HttpMethod.Post && path == "/lookup/slots/lookup-2/queries/missing")
            {
                return FakeResponses.Json(HttpStatusCode.OK, "{ \"missing\": [\"" + hash + "\"] }");
            }

            if (request.Method == HttpMethod.Post && path == "/lookup/slots/lookup-2/queries")
            {
                return FakeResponses.Json(HttpStatusCode.OK, "{ \"outcomes\": [] }");
            }

            if (request.Method == HttpMethod.Post && path == "/lookup/slots/lookup-2/commit")
            {
                return new HttpResponseMessage(HttpStatusCode.OK);
            }

            if (request.Method == HttpMethod.Get && path == "/lookup/slots/lookup-2/progress")
            {
                return FakeResponses.Json(
                    HttpStatusCode.OK,
                    "{ \"slotId\": \"lookup-2\", \"status\": \"committed\", \"counts\": {}, \"entries\": [ { \"imageHash\": \"" + hash + "\", \"state\": \"answered\" } ] }");
            }

            if (request.Method == HttpMethod.Get && path == "/lookup/slots/lookup-2/results")
            {
                resultsCallCount++;
                return FakeResponses.Json(
                    HttpStatusCode.OK,
                    "{ \"lookupSlotId\": \"lookup-2\", \"queries\": [ { \"imageHash\": \"" + hash + "\", \"state\": \"answered\" } ] }");
            }

            throw new InvalidOperationException($"Unexpected request: {request.Method} {path}");
        });

        using var httpClient = new HttpClient(handler);
        var options = new ParallaxClientOptions { Batching = new UploadBatching(1_000_000, 10) };
        using var client = new ParallaxClient(options, httpClient);
        var images = new List<ImageUpload> { image };
        var batchOptions = new LookupBatchOptions();

        var result = await client.LookupBatchAsync(images, batchOptions, progress: null);

        Assert.Equal(1, resultsCallCount);
        Assert.Equal("answered", Assert.Single(result.Results.Queries!).State);
    }

    [Fact]
    public async Task LookupBatchAsync_WithDuplicateImages_DeclaresAndUploadsTheHashOnce()
    {
        var image = new ImageUpload("dup.png", "image/png", new byte[] { 5, 5, 5 });
        var duplicate = new ImageUpload("dup-again.png", "image/png", new byte[] { 5, 5, 5 });
        var hash = Convert.ToHexStringLower(SHA256.HashData(image.Bytes.Span));
        var declaredHashCounts = new List<int>();

        FakeHttpMessageHandler handler = null!;
        handler = new FakeHttpMessageHandler(request =>
        {
            var path = request.RequestUri!.AbsolutePath;
            if (request.Method == HttpMethod.Post && path == "/lookup/slots")
            {
                return FakeResponses.Json(HttpStatusCode.Created, "{ \"lookupSlotId\": \"lookup-3\" }");
            }

            if (request.Method == HttpMethod.Post && path == "/lookup/slots/lookup-3/queries/missing")
            {
                var body = JsonDocument.Parse(handler.Requests[^1].Body);
                declaredHashCounts.Add(body.RootElement.GetProperty("hashes").GetArrayLength());
                return FakeResponses.Json(HttpStatusCode.OK, "{ \"missing\": [\"" + hash + "\"] }");
            }

            if (request.Method == HttpMethod.Post && path == "/lookup/slots/lookup-3/queries")
            {
                return FakeResponses.Json(HttpStatusCode.OK, "{ \"outcomes\": [] }");
            }

            if (request.Method == HttpMethod.Post && path == "/lookup/slots/lookup-3/commit")
            {
                return FakeResponses.Json(
                    HttpStatusCode.OK,
                    "{ \"lookupSlotId\": \"lookup-3\", \"queries\": [ { \"imageHash\": \"" + hash + "\", \"state\": \"answered\" } ] }");
            }

            if (request.Method == HttpMethod.Get && path == "/lookup/slots/lookup-3/progress")
            {
                return FakeResponses.Json(
                    HttpStatusCode.OK,
                    "{ \"slotId\": \"lookup-3\", \"status\": \"committed\", \"counts\": {}, \"entries\": [ { \"imageHash\": \"" + hash + "\", \"state\": \"answered\" } ] }");
            }

            throw new InvalidOperationException($"Unexpected request: {request.Method} {path}");
        });

        using var httpClient = new HttpClient(handler);
        var options = new ParallaxClientOptions { Batching = new UploadBatching(1_000_000, 10) };
        using var client = new ParallaxClient(options, httpClient);
        var images = new List<ImageUpload> { image, duplicate };
        var batchOptions = new LookupBatchOptions();

        var result = await client.LookupBatchAsync(images, batchOptions, progress: null);

        Assert.Equal([1], declaredHashCounts);
        var uploadRequest = handler.Requests.Single(r => r.RequestUri.AbsolutePath == "/lookup/slots/lookup-3/queries");
        var uploadedParts = MultipartWireReader.Read(uploadRequest.ContentType, uploadRequest.Body);
        Assert.Single(uploadedParts);
        Assert.Equal(hash, Assert.Single(result.Results.Queries!).ImageHash);
    }

    [Fact]
    public async Task LookupBatchAsync_WithoutBatchingConfigured_RefusesBeforeSendingAnyRequest()
    {
        var handler = new FakeHttpMessageHandler(_ => throw new InvalidOperationException("No request should be sent."));
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);
        var images = new List<ImageUpload> { new("a.png", "image/png", new byte[] { 1 }) };
        var batchOptions = new LookupBatchOptions();

        await Assert.ThrowsAsync<ParallaxClientException>(() => client.LookupBatchAsync(images, batchOptions, progress: null));

        Assert.Empty(handler.Requests);
    }
}
