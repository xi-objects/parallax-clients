namespace Xio.Parallax.Client.Tests.Verification.Services;

public sealed class TrustRootReaderTests
{
    private readonly ITrustRootReader _reader = new TrustRootReader();

    [Fact]
    public void Empty_roots_are_refused()
    {
        Assert.Throws<VerificationRefusedException>(() => _reader.FromPem([]));
    }

    [Fact]
    public void FromPem_refuses_text_that_carries_no_certificate()
    {
        Assert.Throws<VerificationRefusedException>(() => _reader.FromPem(["not a certificate"]));
    }

    [Fact]
    public void FromPemFile_pins_every_certificate_in_the_file()
    {
        var path = Path.Combine(Path.GetTempPath(), $"roots-{Guid.NewGuid():N}.pem");
        try
        {
            File.WriteAllText(path, TestPki.Create("Root One").RootPem + TestPki.Create("Root Two").RootPem);

            var roots = _reader.FromPemFile(path);

            Assert.Equal(2, roots.Count);
        }
        finally
        {
            File.Delete(path);
        }
    }
}
