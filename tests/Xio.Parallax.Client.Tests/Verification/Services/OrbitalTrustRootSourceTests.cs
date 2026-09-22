namespace Xio.Parallax.Client.Tests.Verification.Services;

public sealed class OrbitalTrustRootSourceTests
{
    private static readonly Uri OrbitalUrl = new("https://orbital.example.test/");

    [Fact]
    public async Task FetchAsync_pins_the_roots_info_answers()
    {
        var first = TestPki.Create("Root One");
        var second = TestPki.Create("Root Two");
        var handler = new FakeHandler(HttpStatusCode.OK, JsonSerializer.Serialize(new { version = "1", PinnedRoots = new[] { first.RootPem, second.RootPem } }));
        using var http = new HttpClient(handler);
        IOrbitalTrustRootSource source = new OrbitalTrustRootSource(http);

        var roots = await source.FetchAsync(OrbitalUrl, CancellationToken.None);

        Assert.Equal(2, roots.Count);
        Assert.Equal(new Uri("https://orbital.example.test/info"), handler.RequestedUri);
        Assert.Null(handler.Authorization);
    }

    [Fact]
    public async Task FetchAsync_refuses_an_empty_pinned_roots_list()
    {
        using var http = new HttpClient(new FakeHandler(HttpStatusCode.OK, "{\"pinnedRoots\":[]}"));
        IOrbitalTrustRootSource source = new OrbitalTrustRootSource(http);

        var refusal = await Assert.ThrowsAsync<VerificationRefusedException>(() => source.FetchAsync(OrbitalUrl, CancellationToken.None));

        Assert.Contains("Control not activated", refusal.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task FetchAsync_refuses_an_answer_without_pinned_roots()
    {
        using var http = new HttpClient(new FakeHandler(HttpStatusCode.OK, "{\"version\":\"1\"}"));
        IOrbitalTrustRootSource source = new OrbitalTrustRootSource(http);

        await Assert.ThrowsAsync<VerificationRefusedException>(() => source.FetchAsync(OrbitalUrl, CancellationToken.None));
    }

    [Fact]
    public async Task FetchAsync_refuses_a_failed_answer()
    {
        using var http = new HttpClient(new FakeHandler(HttpStatusCode.ServiceUnavailable, "{}"));
        IOrbitalTrustRootSource source = new OrbitalTrustRootSource(http);

        await Assert.ThrowsAsync<VerificationRefusedException>(() => source.FetchAsync(OrbitalUrl, CancellationToken.None));
    }

    private sealed class FakeHandler(HttpStatusCode _status,
                                     string _body) : HttpMessageHandler
    {
        public Uri? RequestedUri { get; private set; }

        public string? Authorization { get; private set; }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            RequestedUri = request.RequestUri;
            Authorization = request.Headers.Authorization?.ToString();
            return Task.FromResult(new HttpResponseMessage(_status)
            {
                Content = new StringContent(_body, Encoding.UTF8, "application/json"),
            });
        }
    }
}
