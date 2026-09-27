global using System;
global using System.Buffers.Binary;
global using System.Collections.Generic;
// PC-104: parses the frame ids a fake sequence server reads back from part names
global using System.Globalization;
global using System.IO;
global using System.Linq;
global using System.Net;
global using System.Net.Http;
global using System.Net.Http.Headers;
// PC-102: FakeSequenceFrameSource's [EnumeratorCancellation] parameter
global using System.Runtime.CompilerServices;
global using System.Security.Cryptography;
global using System.Text;
global using System.Text.Json;
global using System.Threading;
global using System.Threading.Tasks;
// PC-102: SequenceFrameEncoderTests' own reference Common provider
global using Microsoft.Extensions.DependencyInjection;
global using Microsoft.Extensions.Logging;
global using Microsoft.Extensions.Logging.Abstractions;
global using Microsoft.Kiota.Abstractions;
global using Microsoft.Kiota.Abstractions.Serialization;
global using Microsoft.Kiota.Serialization.Json;
global using Org.BouncyCastle.Asn1.X509;
global using Org.BouncyCastle.Crypto;
global using Org.BouncyCastle.Crypto.Generators;
global using Org.BouncyCastle.Crypto.Operators;
global using Org.BouncyCastle.Crypto.Parameters;
global using Org.BouncyCastle.Crypto.Signers;
global using Org.BouncyCastle.Math;
global using Org.BouncyCastle.Security;
global using Org.BouncyCastle.X509;
global using Xio.Parallax.Client.C2pa.Enums;
global using Xio.Parallax.Client.C2pa.Interfaces;
global using Xio.Parallax.Client.C2pa.Models;
global using Xio.Parallax.Client.C2pa.Services;
global using Xio.Parallax.Client.Generated.Models;
global using Xio.Parallax.Client.Manifests.Models;
global using Xio.Parallax.Client.Manifests.Services;
global using Xio.Parallax.Client.Multipart.Enums;
global using Xio.Parallax.Client.Multipart.Models;
global using Xio.Parallax.Client.Problems;
// PC-102: FakeSequenceFrameSource implements ISequenceFrameSource
global using Xio.Parallax.Client.Sequences.Interfaces;
global using Xio.Parallax.Client.Sequences.Models;
// PC-102: the linker and encoder under test
global using Xio.Parallax.Client.Sequences.Services;
global using Xio.Parallax.Client.Shared;
global using Xio.Parallax.Client.Shared.Models;
global using Xio.Parallax.Client.Slots.Models;
global using Xio.Parallax.Client.Tests.C2pa.Support;
// PC-102: FakeSequenceFrameSource, the chain linker tests' fake source
global using Xio.Parallax.Client.Tests.Sequences.Support;
global using Xio.Parallax.Client.Tests.Shared;
global using Xio.Parallax.Client.Tests.Verification.Support;
global using Xio.Parallax.Client.Verification.Enums;
global using Xio.Parallax.Client.Verification.Interfaces;
global using Xio.Parallax.Client.Verification.Models;
global using Xio.Parallax.Client.Verification.Services;
// PC-102: the PX frame types the encoder round-trip tests assert on
global using Xio.Parallax.Common;
global using Xunit;
global using Blake3Hasher = Blake3.Hasher;
