#!/usr/bin/env python3

from azure_mcp_agent_hassen.CD.terraform import TerraformConfig, write_tf_file, init, plan, apply, destroy
import tempfile
import os

def test_terraform_config():
    """Test Terraform configuration generation"""
    print("=== Testing Terraform Configuration ===")
    
    # Create test config
    config = TerraformConfig(
        user_id='test123',
        cluster_name='test-cluster',
        region='East US',
        node_count=3,
        vm_size='Standard_DS2_v2',
        auto_scaling=True,
        min_nodes=1,
        max_nodes=5,
        enable_monitoring=True,
        private_cluster=False,
        dns_domain='example.com',
        enable_oidc=True,
        tags={'env': 'test', 'project': 'terraform-test'}
    )

    # Test in temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f'Testing Terraform file generation in: {temp_dir}')
        try:
            tf_path = write_tf_file(temp_dir, config)
            print(f'✓ Successfully created Terraform file: {tf_path}')
            
            # Check if files were created
            main_tf = os.path.join(temp_dir, 'main.tf')
            backend_tf = os.path.join(temp_dir, 'backend.tf')
            
            if os.path.exists(main_tf):
                print(f'✓ main.tf exists ({os.path.getsize(main_tf)} bytes)')
                with open(main_tf, 'r') as f:
                    content = f.read()
                    print("✓ main.tf content preview:")
                    print(content[:500] + "..." if len(content) > 500 else content)
            else:
                print('✗ main.tf not found')
                
            if os.path.exists(backend_tf):
                print(f'✓ backend.tf exists ({os.path.getsize(backend_tf)} bytes)')
                with open(backend_tf, 'r') as f:
                    content = f.read()
                    print("✓ backend.tf content:")
                    print(content)
            else:
                print('✗ backend.tf not found')
                
        except Exception as e:
            print(f'✗ Error: {e}')
            import traceback
            traceback.print_exc()

def test_terraform_commands():
    """Test Terraform command functions"""
    print("\n=== Testing Terraform Commands ===")
    
    # Test with non-existent directory first
    test_dir = "c:/temp/terraform_test"
    
    try:
        print(f"Testing init in directory: {test_dir}")
        result = init(test_dir)
        print(f"Init result: {result}")
        print(f"Status: {result.status}")
        if hasattr(result, 'output') and result.output:
            print(f"Output: {result.output[:200]}...")
            
    except Exception as e:
        print(f"✗ Error testing init: {e}")
        import traceback
        traceback.print_exc()

def test_dns_prefix_validation():
    """Test DNS prefix validation edge cases"""
    print("\n=== Testing DNS Prefix Validation ===")
    
    test_cases = [
        ("ab", "Should fail - too short"),
        ("a", "Should fail - too short"), 
        ("test-cluster-123", "Should work"),
        ("", "Should fail - empty"),
        ("test cluster", "Should work with spaces"),
        ("test@cluster#", "Should work with special chars")
    ]
    
    for cluster_name, description in test_cases:
        try:
            config = TerraformConfig(
                user_id='test123',
                cluster_name=cluster_name,
                region='East US',
                node_count=3,
                vm_size='Standard_DS2_v2',
                auto_scaling=True,
                min_nodes=1,
                max_nodes=5,
                enable_monitoring=True,
                private_cluster=False,
                dns_domain='example.com',
                enable_oidc=True,
                tags={'env': 'test'}
            )
            
            with tempfile.TemporaryDirectory() as temp_dir:
                write_tf_file(temp_dir, config)
                print(f"✓ {description}: '{cluster_name}' - SUCCESS")
                
        except Exception as e:
            print(f"✗ {description}: '{cluster_name}' - ERROR: {e}")

if __name__ == "__main__":
    test_terraform_config()
    test_terraform_commands() 
    test_dns_prefix_validation()
