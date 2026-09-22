namespace Xio.Parallax.Client.Tests.Verification.Services;

public sealed class CanonicalPreimageBuilderTests
{
    private static readonly byte[] ContentHash = [0xAA, 0xBB];

    private readonly ICanonicalPreimageBuilder _builder = new CanonicalPreimageBuilder();

    [Fact]
    public void Manifest_preimage_is_version_then_length_prefixed_content_hash_kind_and_manifest_hash()
    {
        var preimage = _builder.Manifest(new XioManifestPreimageRequest(ContentHash, "c2pa", new byte[] { 0x01, 0x02, 0x03 }));

        byte[] expected =
        [
            0x02,
            0x00, 0x02, 0xAA, 0xBB,
            0x00, 0x04, (byte)'c', (byte)'2', (byte)'p', (byte)'a',
            0x00, 0x03, 0x01, 0x02, 0x03,
        ];
        Assert.Equal(expected, preimage);
    }

    [Fact]
    public void Manifest_preimage_prefixes_the_kind_by_its_utf8_byte_length()
    {
        var preimage = _builder.Manifest(new XioManifestPreimageRequest(ContentHash, "é", new byte[] { 0x09 }));

        byte[] expected = [0x02, 0x00, 0x02, 0xAA, 0xBB, 0x00, 0x02, 0xC3, 0xA9, 0x00, 0x01, 0x09];
        Assert.Equal(expected, preimage);
    }

    [Fact]
    public void Collection_preimage_carries_the_count_and_every_manifest_in_record_order()
    {
        CanonicalManifestEntry[] manifests =
        [
            new("c2pa", new byte[] { 0x01 }),
            new("xi", new byte[] { 0x02, 0x03 }),
        ];

        var preimage = _builder.Collection(new XioCollectionPreimageRequest(ContentHash, manifests));

        byte[] expected =
        [
            0x02,
            0x00, 0x02, 0xAA, 0xBB,
            0x00, 0x02,
            0x00, 0x04, (byte)'c', (byte)'2', (byte)'p', (byte)'a',
            0x00, 0x01, 0x01,
            0x00, 0x02, (byte)'x', (byte)'i',
            0x00, 0x02, 0x02, 0x03,
        ];
        Assert.Equal(expected, preimage);
    }

    [Fact]
    public void Collection_preimage_of_no_manifests_carries_a_zero_count()
    {
        var preimage = _builder.Collection(new XioCollectionPreimageRequest(ContentHash, []));

        byte[] expected = [0x02, 0x00, 0x02, 0xAA, 0xBB, 0x00, 0x00];
        Assert.Equal(expected, preimage);
    }

    [Fact]
    public void Image_preimage_is_the_content_hash_bytes_alone()
    {
        var preimage = _builder.Image(ContentHash);

        Assert.Equal(ContentHash, preimage);
    }
}
