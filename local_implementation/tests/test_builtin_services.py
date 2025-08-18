import grpc
import pytest
from aifs.proto import aifs_pb2, aifs_pb2_grpc

@pytest.fixture(scope="module")
def grpc_channel():
    # Assumes server is running on localhost:50051
    channel = grpc.insecure_channel("localhost:50051")
    yield channel
    channel.close()

def test_health(grpc_channel):
    stub = aifs_pb2_grpc.HealthStub(grpc_channel)
    resp = stub.Check(aifs_pb2.HealthCheckRequest())
    assert resp.healthy
    assert resp.status == "SERVING"

def test_introspect(grpc_channel):
    stub = aifs_pb2_grpc.IntrospectStub(grpc_channel)
    resp = stub.GetInfo(aifs_pb2.IntrospectRequest())
    assert resp.version
    assert "core" in resp.features

def test_admin(grpc_channel):
    stub = aifs_pb2_grpc.AdminStub(grpc_channel)
    ns_resp = stub.CreateNamespace(aifs_pb2.CreateNamespaceRequest(name="testns"))
    assert ns_resp.success
    assert ns_resp.namespace_id == "testns"
    prune_resp = stub.PruneSnapshot(aifs_pb2.PruneSnapshotRequest(snapshot_id="snap1"))
    assert prune_resp.success
    policy_resp = stub.ManagePolicy(aifs_pb2.ManagePolicyRequest(namespace_id="testns", policy="default"))
    assert policy_resp.success

def test_metrics(grpc_channel):
    stub = aifs_pb2_grpc.MetricsStub(grpc_channel)
    resp = stub.GetMetrics(aifs_pb2.MetricsRequest())
    assert "HELP" in resp.prometheus_metrics

def test_format(grpc_channel):
    stub = aifs_pb2_grpc.FormatStub(grpc_channel)
    resp = stub.FormatStorage(aifs_pb2.FormatRequest(dry_run=True))
    assert resp.success
    assert resp.root_snapshot_id
    assert "Formatted" in resp.log
