#!/usr/bin/env python3

from azure_mcp_agent_hassen.CD.terraform import TerraformConfig, write_tf_file, init, plan, apply, destroy
import tempfile
import os

def test_terraform_commands_with_real_files():
    """Test Terraform commands with properly generated files"""
    print("=== Testing Terraform Commands with Generated Files ===")
    
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

    with tempfile.TemporaryDirectory() as temp_dir:
        print(f'Testing in directory: {temp_dir}')
        
        # Generate Terraform files
        try:
            tf_path = write_tf_file(temp_dir, config)
            print(f'✓ Generated Terraform files: {tf_path}')
            
            # List files created
            files = os.listdir(temp_dir)
            print(f'✓ Files created: {files}')
            
            # Test init
            print("\\nTesting terraform init...")
            init_result = init(temp_dir)
            print(f"Init Status: {init_result.status}")
            if init_result.message:
                print(f"Init Message: {init_result.message}")
            if init_result.output:
                print(f"Init Output (first 200 chars): {init_result.output[:200]}...")
                
            # Test plan (even if init fails, we should see what happens)
            print("\\nTesting terraform plan...")
            plan_result = plan(temp_dir)
            print(f"Plan Status: {plan_result.status}")
            if plan_result.message:
                print(f"Plan Message: {plan_result.message}")
            if plan_result.output:
                print(f"Plan Output (first 200 chars): {plan_result.output[:200]}...")
                
        except Exception as e:
            print(f'✗ Error: {e}')
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_terraform_commands_with_real_files()
