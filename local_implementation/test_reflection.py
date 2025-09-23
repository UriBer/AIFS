#!/usr/bin/env python3
"""Test gRPC reflection and server connectivity."""

import grpc
import time
from aifs.proto import aifs_pb2, aifs_pb2_grpc

def test_reflection():
    """Test if reflection is working."""
    try:
        # Connect to server
        channel = grpc.insecure_channel('localhost:50051')
        
        # Test basic connectivity
        print("Testing basic connectivity...")
        health_stub = aifs_pb2_grpc.HealthStub(channel)
        
        # This should work without reflection
        try:
            response = health_stub.Check(aifs_pb2.HealthCheckRequest())
            print(f"✅ Health check successful: {response}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
        
        # Test reflection
        print("\nTesting reflection...")
        try:
            from grpc_reflection.v1alpha import reflection
            reflection_stub = reflection.ReflectionStub(channel)
            
            # List services
            services_response = reflection_stub.ListServices(aifs_pb2.DESCRIPTOR.services_by_name['Health'].full_name)
            print(f"✅ Reflection working! Services: {list(services_response.service)}")
            return True
        except Exception as e:
            print(f"❌ Reflection failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    finally:
        channel.close()

def test_grpcurl_commands():
    """Test grpcurl commands."""
    import subprocess
    
    commands = [
        ["grpcurl", "-plaintext", "localhost:50051", "list"],
        ["grpcurl", "-plaintext", "localhost:50051", "list", "aifs.v1.Health"],
        ["grpcurl", "-plaintext", "localhost:50051", "aifs.v1.Health/Check"],
    ]
    
    for cmd in commands:
        print(f"\n🔍 Testing: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✅ Success: {result.stdout}")
            else:
                print(f"❌ Failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("❌ Timeout")
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Main function."""
    print("🧪 Testing AIFS gRPC Server")
    print("=" * 40)
    
    # Wait a moment for server to be ready
    print("Waiting for server to be ready...")
    time.sleep(2)
    
    # Test reflection
    if test_reflection():
        print("\n🎉 Reflection is working!")
    else:
        print("\n⚠️  Reflection may not be working properly")
    
    # Test grpcurl commands
    print("\n" + "=" * 40)
    print("Testing grpcurl commands...")
    test_grpcurl_commands()

if __name__ == "__main__":
    main()
