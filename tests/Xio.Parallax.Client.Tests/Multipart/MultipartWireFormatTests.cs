namespace Xio.Parallax.Client.Tests.Multipart;

public sealed class MultipartWireFormatTests
{
    [Fact]
    public async Task RegisterAsync_SendsTheManifestBeforeTheImage_WithTheirOwnPartNamesAndContentTypes()
    {
        var handler = new FakeHttpMessageHandler(_ => FakeResponses.Json(HttpStatusCode.Created, "{}"));
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);
        var image = new ImageUpload("photo.png", "image/png", new byte[] { 9, 9, 9 });
        var manifest = new ManifestPart("c2pa", ManifestForm.C2pa, new byte[] { 1, 2, 3, 4 });

        await client.RegisterAsync(image, [manifest]);

        var request = Assert.Single(handler.Requests);
        var parts = MultipartWireReader.Read(request.ContentType, request.Body);
        Assert.Collection(
            parts,
            part =>
            {
                Assert.Equal("manifest[c2pa]", part.Name);
                Assert.Equal("application/c2pa", part.ContentType);
            },
            part =>
            {
                Assert.Equal("image", part.Name);
                Assert.Equal("image/png", part.ContentType);
            });
    }

    [Fact]
    public async Task RegisterAsync_SendsEveryManifestBeforeTheImage_InTheGivenOrder()
    {
        var handler = new FakeHttpMessageHandler(_ => FakeResponses.Json(HttpStatusCode.Created, "{}"));
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);
        var image = new ImageUpload("photo.png", "image/png", new byte[] { 9 });
        var manifests = new[]
        {
            new ManifestPart("xi-manifest", ManifestForm.Json, new byte[] { 1 }),
            new ManifestPart("c2pa", ManifestForm.Jumbf, new byte[] { 2 }),
        };

        await client.RegisterAsync(image, manifests);

        var request = Assert.Single(handler.Requests);
        var names = MultipartWireReader.Read(request.ContentType, request.Body).Select(part => part.Name).ToList();
        Assert.Equal(["manifest[xi-manifest]", "manifest[c2pa]", "image"], names);
    }

    [Fact]
    public async Task LookupAsync_SendsTheImageAloneAsAnImagePart()
    {
        var handler = new FakeHttpMessageHandler(_ => FakeResponses.Json(HttpStatusCode.OK, "{}"));
        using var httpClient = new HttpClient(handler);
        using var client = new ParallaxClient(new ParallaxClientOptions(), httpClient);
        var image = new ImageUpload("photo.png", "image/png", new byte[] { 5, 5, 5 });

        await client.LookupAsync(image);

        var request = Assert.Single(handler.Requests);
        var part = Assert.Single(MultipartWireReader.Read(request.ContentType, request.Body));
        Assert.Equal("image", part.Name);
        Assert.Equal("image/png", part.ContentType);
    }
}
