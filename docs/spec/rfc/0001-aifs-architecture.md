
% AIFS – AI-Native File System Architecture
% U. Berman, Kimi, ChatGPT
% July 18 2025
%% version: 00
%% category: core
%% expires: 2026-01-18
%% BCP14
%% BSD-3-Clause

Abstract
   The AI-Native File System (AIFS) is a semantic, content-addressed, versioned
   storage fabric that treats *meaning*—not directory paths—as the primary
   lookup key.  It integrates vector search, lineage tracking, and snapshot
   semantics required by modern machine-learning pipelines while retaining
   optional POSIX compatibility for legacy applications.  This document
   specifies the AIFS object model, wire protocol, snapshot format, security
   properties, and performance targets.

Status of This Memo
   This Internet-Draft is submitted in full conformance with BCP 78 and BCP 79.
   Internet-Drafts are working documents of the IETF.  They have no formal
   status and should not be cited other than as *work in progress*.  The
   reference URL for all Internet-Drafts is <https://datatracker.ietf.org>.

Table of Contents
1.  Introduction .....................................................2  
2.  Conventions and Terminology ......................................3  
3.  Architectural Overview ...........................................3  
4.  Object Model .....................................................5  
5.  Wire Protocol ....................................................7  
6.  Snapshot & Versioning Model ......................................9  
7.  Security Considerations .........................................10  
8.  Performance Expectations ........................................12  
9.  Rationale & Alternatives ........................................13  
10. Prior Art .......................................................14  
11. IANA Considerations .............................................15  
12. Unresolved Questions ............................................15  
13. Future Work .....................................................16  
14. Security Considerations (additional) ............................16  
15. References ......................................................17  
Appendix A.  Glossary ...............................................18  
Appendix B.  Benchmark Methodology ..................................19  
Acknowledgements ....................................................19  
Authors’ Addresses ..................................................20  

----------------------------------------------------------------------

1.  Introduction

   General-purpose file systems such as NTFS, ext4, APFS, and ZFS expose
   hierarchical namespaces optimised around human-assigned file names and
   fixed-size block I/O.  Contemporary machine-learning (ML) systems,
   however, organise and retrieve information by *semantic similarity*
   (vector distance), demand immutable snapshots for reproducible training,
   and operate at data volumes that exceed the scalability envelope of
   bolt-on index layers.

   AIFS provides:

   *   **Content addressing** – every *Asset* is identified by a BLAKE3 hash;
   *   **Vector-first metadata** – one or more embeddings are stored
       alongside the raw data as primary indices;
   *   **Versioned snapshots** – Merkle-tree histories with cheap branching
       for experiment tracking;
   *   **Inline lineage capture** – transformations are recorded in a DAG so
       that models can be re-trained automatically when inputs change;
   *   **Optional POSIX shim** – a FUSE layer that exposes Assets as virtual
       files under `/aifs/<namespace>/<asset-id>`.

   The remainder of this draft specifies the normative requirements for an
   implementation conforming to *AIFS version 1.00*.

----------------------------------------------------------------------

2.  Conventions and Terminology

   The key words “**MUST**”, “**MUST NOT**”, “**REQUIRED**”, “**SHALL**”,
   “**SHALL NOT**”, “**SHOULD**”, “**SHOULD NOT**”, “**RECOMMENDED**”,
   “**MAY**”, and “**OPTIONAL**” in this document are to be interpreted as
   described in BCP 14 [RFC2119] [RFC8174] when, and only when, they appear
   in all capitals, as shown here.

   *Asset*           A logical unit of data (blob, tensor, embedding, model,
                     document, etc.) stored by AIFS.  
   *Chunk*           A physically stored fragment of an Asset.  
   *Embedding*       A fixed-length vector representation of an Asset or
                     Chunk.  
   *Snapshot*        A Merkle-root describing the state of a namespace at a
                     specific time.  
   *Namespace*       A logical grouping of Assets that share an access and
                     retention policy.

----------------------------------------------------------------------

3.  Architectural Overview

3.1.  Layered Stack

+---------------------------+
|  Application / ML SDKs    |
+---------------------------+
|    AIFS gRPC API          |
+---------------------------+
|  Metadata & Vector Index  |
|  (RocksDB/FDB + HNSW/PQ)  |
+---------------------------+
|  Object/Chunk Storage     |
|  (NVMe-oF, HDD, S3, etc.) |
+---------------------------+
|  Optional POSIX FUSE      |
+---------------------------+
| Kernel I/O                |
+---------------------------+

3.2.  Data Flow Patterns

*Write*: The client **MUST** send a `PutAsset` RPC containing user
metadata plus a stream of chunks.  The server computes the BLAKE3 digest,
persists chunks, executes **ingest operators** (e.g., embedding
generation), updates the vector index, and returns the canonical AssetID.

*Vector Query*: The client **SHOULD** use `VectorSearch` specifying
`k`, distance metric, and optional metadata filters.  The server **MUST**
return a list of `AssetReference` objects containing AssetIDs and scores.
Data streaming thereafter occurs directly from object targets to the
requesting client via an authorised pre-signed URL.

----------------------------------------------------------------------

4.  Object Model

4.1.  Asset Kinds

| Kind      | Encoding | Schema ID                       | Notes                   |
|-----------|----------|---------------------------------|-------------------------|
| **Blob**  | raw      | —                               | Arbitrary byte stream   |
| **Tensor**| Arrow2   | `schema/nd-array.proto`         | Supports n-D shapes     |
| **Embed** | FlatBuffers | `schema/embedding.fbs`       | One per modality/model  |
| **Artifact**| ZIP + MANIFEST | `schema/artifact.proto` | Heterogeneous bundle    |

4.2.  Canonical Identifiers

aifs:///[.]    ; AssetID
aifs-snap:///       ; SnapshotID

   The `<blake3-hash>` **SHALL** be encoded using lowercase hex (no “0x”),
   256-bit output.  SnapshotIDs are 128-bit BLAKE3 hashes of the Merkle root
   plus timestamp.

4.3.  Lineage Graph

   Each Asset **MUST** record zero or more `ParentEdge` entries:
   message ParentEdge {
bytes parent_asset_id = 1;
string transform_name = 2;
bytes transform_digest = 3; // e.g., container image hash
}

   Servers **MUST** provide strong causality: if Asset B lists Asset A as a
   parent, B **SHALL NOT** be visible until A is fully committed.

----------------------------------------------------------------------

5.  Wire Protocol

5.1.  Transport

*   **Transport:** gRPC over HTTP/2.  
*   **Serialization:** protobuf v3 with deterministic encoding.  
*   **Compression:** zstd level ≥ 1, negotiated via
    `grpc-accept-encoding`.  The client **MUST** support zstd; servers
    **MAY** fall back to identity.

5.2.  Core RPCs (non-exhaustive)

| RPC                         | Direction  | Purpose                             |
|-----------------------------|------------|-------------------------------------|
| `PutAsset(stream Chunk)`    | client→srv | Store asset; returns `AssetID`.     |
| `GetAsset(Request)`         | client→srv | Retrieve metadata and chunk list.   |
| `VectorSearch(Query)`       | client→srv | k-NN search over embeddings.        |
| `CreateSnapshot(Namespace)` | client→srv | Atomically cut snapshot.            |
| `SubscribeEvents(filter)`   | client→srv | Server push for lineage/drift.      |

   Complete `.proto` definitions are located under
   `proto/aifs/v1/*.proto` in the reference repository
   (<https://github.com/aifs/rfcs>).

5.3.  Error Handling

   All RPC errors **MUST** map to gRPC status codes.  The server **SHOULD**
   populate the `google.rpc.Status` message with a machine-readable `reason`
   and human-readable `detail`.

----------------------------------------------------------------------

6.  Snapshot & Versioning Model

6.1.  Merkle Tree Structure
SnapshotRoot
├── AssetID_1  (BLAKE3)
├── AssetID_2
└── …

Each leaf is an AssetID; internal nodes are BLAKE3 hashes of their
children (ordered lexicographically).  The root node **MUST** be signed
with Ed25519 according to [RFC8032].

6.2.  Branching and Tagging

*Branches* are named pointers to snapshot roots.  Creating or updating a
branch **MUST** be an atomic metadata transaction.  Tags (immutable
labels) **SHOULD** be used for audit-grade provenance (e.g., “dataset
v1.2 regulatory-export”).

6.3.  POSIX View

The optional FUSE driver **MUST** expose:

* Files: `/<b3hash>` or symbolic names via extended attributes.  
* Directories: synthetic, based on branch names.  
* `stat()` size = original blob length; `ctime` = snapshot timestamp.

----------------------------------------------------------------------

7.  Security Considerations

7.1.  Confidentiality

Every Chunk **MUST** be encrypted with AES-256-GCM.  Per-chunk data keys
**SHALL** be wrapped by a customer-managed Key Management Service (KMS)
using envelope encryption.  The KMS key ID **MUST** be stored in chunk
metadata.

7.2.  Integrity & Authenticity

*   *Integrity*: verified by BLAKE3 hashes at read time.  
*   *Authenticity*: Ed25519 signatures of snapshot roots **MUST** be
    verified before exposing a branch.  
*   Clients **SHOULD** pin public keys by namespace.

7.3.  Authorisation

Capability tokens (*macaroons*) **SHALL** encode:

* Namespace  
* Allowed methods (put, get, search, snapshot, etc.)  
* Expiry timestamp

Servers **MUST** validate macaroons on every RPC, independent of TLS.

7.4.  Privacy

Differential-privacy budgets are out of scope for this document but **MAY**
be enforced by policy engines attached to lineage events.

+-----------------------------------------------------------------------+
| 8.  Performance Expectations                                          |
| Metric                               | Target (per node)              |
|--------------------------------------|--------------------------------|
| Random IOPS (4 KiB, read)            | ≥ 1 M IOPS (P50 < 200 µs)      |
| Vector search latency (1 B vectors)  | P99 < 1 ms (cosine, k = 10)    |
| Snapshot creation (100 k Assets)     | ≤ 200 ms                       |
| Ingest throughput (sequential)       | ≥ 5 GB/s per proxy             |
| These are **SHOULD**-level goals for reference implementations.       |
+-----------------------------------------------------------------------+

9.  Rationale & Alternatives

* **BLAKE3 vs SHA-256:** BLAKE3 offers tree-hashing, SIMD acceleration, and
equivalent security at lower CPU cost.  
* **gRPC vs Cap’n Proto RPC:** gRPC provides ubiquitous tooling, load
balancing, and first-class HTTP/2 streaming.  Zero-copy is achieved via
Apache Arrow2 buffers, mitigating framing overhead.  
* **FlatBuffers for embeddings:** Fits fixed-layout vectors without varint
overhead; supports direct memory access from C++ and Rust back-ends.

+-----------------------------------------------------------------------------+
| 10.  Prior Art                                                              |
| System    | Strengths                        | Limitations vs AIFS          |
|-----------|----------------------------------|------------------------------|
| IPFS      | Global content addressing        | Weak consistency; no vector  |
| LakeFS    | Git-like snapshots over S3       | No built-in ANN index        |
| ReFS      | Resiliency, checksums            | Windows-only; path-based     |
+-----------------------------------------------------------------------------+

11.  IANA Considerations

This document registers the URI scheme **`aifs://`** and
**`aifs-snap://`** (see Section 4.2) in the “URI Schemes” registry
following the procedures in [RFC7595].

----------------------------------------------------------------------

12.  Unresolved Questions

* Support for mutable tensors enabling delta training checkpoints?  
* Timeline for migrating Ed25519 to a quantum-safe signature (e.g., Dilithium)?  
* Metrics export format (OpenTelemetry vs Prom-remote-write)?

----------------------------------------------------------------------

13.  Future Work

* WASM-based **Transform Functions** executed inside storage nodes.  
* GPU-Direct Storage (GDS) offload for NVLink-attached accelerators.  
* CRDT-based edge synchronisation for intermittently-connected devices.

----------------------------------------------------------------------

14.  Security Considerations (additional)

Malicious embeddings could induce adversarial behaviour in downstream
models.  Operators **SHOULD** validate or quarantine new embeddings
before making them searchable.  Rate-limiting vector queries mitigates
model extraction attacks.  Further analysis is left to
*rfc/0002-security.md*.

----------------------------------------------------------------------

15.  References

15.1.  Normative

[RFC2119]  Bradner, S., “Key words for use in RFCs to Indicate
        Requirement Levels”, BCP 14, RFC 2119, March 1997.  
[RFC8174]  Leiba, B., “Ambiguity of Uppercase vs Lowercase in RFC 2119 Key
        Words”, BCP 14, RFC 8174, May 2017.  
[RFC8032]  Josefsson, S. and I. Liusvaara, “Edwards-curve Digital Signature
        Algorithm (EdDSA)”, RFC 8032, January 2017.  
[RFC7595]  Thaler, D., “Guidelines and Registration Procedures for URI
        Schemes”, BCP 115, RFC 7595, June 2015.

15.2.  Informative

*  *FAISS*: Facebook AI Similarity Search, 2024.  
*  *HNSWlib*: Hierarchical Navigable Small World graphs, 2025.  
*  *LakeFS*: Data versioning over object stores, 2025.

----------------------------------------------------------------------

Appendix A.  Glossary
*ANN*  Approximate Nearest Neighbour  
*DAG*  Directed Acyclic Graph  
*FDB*  FoundationDB  
*NVMe-oF*  NVMe over Fabrics

Appendix B.  Benchmark Methodology
See directory `bench/` in the reference implementation for scripts and
raw results reproducing Section 8.

Acknowledgements
The authors thank the early adopters at Even-Derech-IT, Kimi.com, and the
open-source community for their invaluable feedback.

Authors’ Addresses
Uri Berman
Even-Derech-IT  
Email: urib@even-derech-it.com

Kimi.com  
(email withheld)

ChatGPT.com  
(email withheld)

----------------------------------------------------------------------
