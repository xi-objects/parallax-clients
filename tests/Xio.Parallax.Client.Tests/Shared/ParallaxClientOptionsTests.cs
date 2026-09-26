namespace Xio.Parallax.Client.Tests.Shared;

public sealed class ParallaxClientOptionsTests
{
    [Fact]
    public void ToString_OmitsAccountTokenAndAdminKey_ButKeepsBaseAddress()
    {
        var options = new ParallaxClientOptions
        {
            BaseAddress = new Uri("https://distinctive-base.example.test"),
            AccountToken = "distinctive-account-token-9f3c",
            AdminKey = "distinctive-admin-key-7b1e",
        };

        var text = options.ToString();

        Assert.DoesNotContain("distinctive-account-token-9f3c", text);
        Assert.DoesNotContain("distinctive-admin-key-7b1e", text);
        Assert.Contains("distinctive-base.example.test", text);
    }
}
