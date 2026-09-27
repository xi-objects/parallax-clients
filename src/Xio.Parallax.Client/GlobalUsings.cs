global using System;
global using System.Buffers.Binary;
global using System.Collections.Generic;
global using System.Diagnostics;
global using System.Globalization;
global using System.IO;
global using System.Linq;
global using System.Net.Http;
global using System.Net.Http.Headers;
// PC-102: SequenceChainLinker's [EnumeratorCancellation] parameter
global using System.Runtime.CompilerServices;
global using System.Security.Cryptography;
global using System.Text;
global using System.Text.Json;
global using System.Text.RegularExpressions;
global using System.Threading;
global using System.Threading.Tasks;
// PC-102: composes Xio.Parallax.Common once, in SequenceFrameEncoder
global using Microsoft.Extensions.DependencyInjection;
// PC-102: the ILogger<T> Common's hash service asks for
global using Microsoft.Extensions.Logging;
// PC-102: NullLogger<T>, standing in for a host's own logging
global using Microsoft.Extensions.Logging.Abstractions;
global using Microsoft.Kiota.Abstractions;
global using Microsoft.Kiota.Abstractions.Authentication;
global using Microsoft.Kiota.Abstractions.Serialization;
global using Microsoft.Kiota.Http.HttpClientLibrary;
global using Org.BouncyCastle.Crypto.Parameters;
global using Org.BouncyCastle.Crypto.Signers;
global using Org.BouncyCastle.X509;
global using Xio.Parallax.Client.C2pa;
global using Xio.Parallax.Client.C2pa.Enums;
global using Xio.Parallax.Client.C2pa.Interfaces;
global using Xio.Parallax.Client.C2pa.Models;
global using Xio.Parallax.Client.C2pa.Services;
global using Xio.Parallax.Client.Generated;
global using Xio.Parallax.Client.Generated.Models;
global using Xio.Parallax.Client.Manifests.Interfaces;
global using Xio.Parallax.Client.Manifests.Models;
global using Xio.Parallax.Client.Multipart.Enums;
global using Xio.Parallax.Client.Multipart.Models;
global using Xio.Parallax.Client.Multipart.Services;
global using Xio.Parallax.Client.Problems;
// PC-102: the Sequences domain's models, referenced across Models and Services
global using Xio.Parallax.Client.Sequences.Models;
// PC-103: SequenceFrameEncoder, composed by the sequence route members on ParallaxClient
global using Xio.Parallax.Client.Sequences.Services;
global using Xio.Parallax.Client.Shared;
global using Xio.Parallax.Client.Shared.Models;
global using Xio.Parallax.Client.Slots.Models;
global using Xio.Parallax.Client.Verification.Enums;
global using Xio.Parallax.Client.Verification.Interfaces;
global using Xio.Parallax.Client.Verification.Models;
global using Xio.Parallax.Client.Verification.Services;
// PC-102: the PX frame types SequenceFrameEncoder and its models build on
global using Xio.Parallax.Common;
global using Blake3Hasher = Blake3.Hasher;
