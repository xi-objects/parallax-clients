namespace Xio.Parallax.Client.Tests.Shared;

public sealed class RecordWaitTests
{
    private const string Hash = "abc123";

    [Fact]
    public async Task WaitForRecordAsync_WhenFirstPollIsPublished_ReturnsWithoutFurtherPolling()
    {
        var handler = new FakeHttpMessageHandler(request => RecordResponse(request, "published"));
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);
        var waitOptions = new RecordWaitOptions(TimeSpan.FromMilliseconds(1), TimeSpan.FromSeconds(5));

        var result = await client.WaitForRecordAsync(Hash, waitOptions);

        Assert.Equal(PublishedRecordOutcome.Published, result.Outcome);
        Assert.Single(handler.Requests);
    }

    [Fact]
    public async Task WaitForRecordAsync_WhenNoRecordAnsweredTwiceThenPublished_PollsThreeTimes()
    {
        var callCount = 0;
        var handler = new FakeHttpMessageHandler(request =>
        {
            callCount++;
            var outcome = callCount <= 2 ? "noRecordAnswered" : "published";
            return RecordResponse(request, outcome);
        });
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);
        var waitOptions = new RecordWaitOptions(TimeSpan.FromMilliseconds(1), TimeSpan.FromSeconds(5));

        var result = await client.WaitForRecordAsync(Hash, waitOptions);

        Assert.Equal(PublishedRecordOutcome.Published, result.Outcome);
        Assert.Equal(3, callCount);
        Assert.Equal(3, handler.Requests.Count);
    }

    [Fact]
    public async Task WaitForRecordAsync_WhenTakenDown_ReturnsWithoutThrowing()
    {
        var handler = new FakeHttpMessageHandler(request => RecordResponse(request, "takenDown"));
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);
        var waitOptions = new RecordWaitOptions(TimeSpan.FromMilliseconds(1), TimeSpan.FromSeconds(5));

        var result = await client.WaitForRecordAsync(Hash, waitOptions);

        Assert.Equal(PublishedRecordOutcome.TakenDown, result.Outcome);
        Assert.Single(handler.Requests);
    }

    [Fact]
    public async Task WaitForRecordAsync_WhenPollTimeoutElapses_ThrowsNamingTheHash()
    {
        var handler = new FakeHttpMessageHandler(request => RecordResponse(request, "retry"));
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);
        var waitOptions = new RecordWaitOptions(TimeSpan.FromMilliseconds(5), TimeSpan.FromMilliseconds(50));

        var exception = await Assert.ThrowsAsync<ParallaxClientException>(
            () => client.WaitForRecordAsync(Hash, waitOptions));

        Assert.Contains(Hash, exception.Message, StringComparison.Ordinal);
        Assert.True(handler.Requests.Count > 1);
    }

    private static HttpResponseMessage RecordResponse(HttpRequestMessage request, string outcome)
    {
        var path = request.RequestUri!.AbsolutePath;
        if (request.Method == HttpMethod.Get && path == $"/records/{Hash}")
        {
            return FakeResponses.Json(
                HttpStatusCode.OK,
                "{ \"originalImageHash\": \"" + Hash + "\", \"outcome\": \"" + outcome + "\" }");
        }

        throw new InvalidOperationException($"Unexpected request: {request.Method} {path}");
    }
}
