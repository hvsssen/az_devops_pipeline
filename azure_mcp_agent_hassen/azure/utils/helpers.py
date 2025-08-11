"""
Azure Utility Functions

Common utilities and helpers for Azure operations including
session management, data formatting, and validation.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta


def format_azure_cost(cost_data: List[Dict]) -> Dict[str, Any]:
    """Format Azure cost data for display"""
    try:
        total_cost = 0.0
        formatted_entries = []
        
        for entry in cost_data:
            cost = float(entry.get("pretaxCost", 0))
            total_cost += cost
            
            formatted_entries.append({
                "service": entry.get("meterCategory", "Unknown"),
                "resource": entry.get("instanceName", "Unknown"),
                "cost": cost,
                "currency": entry.get("currency", "USD"),
                "billing_period": entry.get("billingPeriodEndDate", "Unknown")
            })
        
        return {
            "total_cost": round(total_cost, 2),
            "entries": formatted_entries,
            "currency": cost_data[0].get("currency", "USD") if cost_data else "USD"
        }
    except Exception as e:
        logging.error(f"Failed to format cost data: {e}")
        return {"total_cost": 0.0, "entries": [], "currency": "USD"}


def validate_vm_state(state: str) -> bool:
    """Validate VM power state"""
    valid_states = [
        "PowerState/running",
        "PowerState/stopped", 
        "PowerState/deallocated",
        "PowerState/starting",
        "PowerState/stopping"
    ]
    return state in valid_states


def format_vm_size_info(vm_size: str) -> Dict[str, Any]:
    """Get formatted information about VM size"""
    # Common VM size patterns and their specifications
    size_info = {
        # Standard series
        "Standard_B1s": {"vcpus": 1, "memory_gb": 1, "temp_storage_gb": 2},
        "Standard_B1ms": {"vcpus": 1, "memory_gb": 2, "temp_storage_gb": 4},
        "Standard_B2s": {"vcpus": 2, "memory_gb": 4, "temp_storage_gb": 8},
        "Standard_B2ms": {"vcpus": 2, "memory_gb": 8, "temp_storage_gb": 16},
        "Standard_B4ms": {"vcpus": 4, "memory_gb": 16, "temp_storage_gb": 32},
        
        # D series
        "Standard_D2s_v3": {"vcpus": 2, "memory_gb": 8, "temp_storage_gb": 16},
        "Standard_D4s_v3": {"vcpus": 4, "memory_gb": 16, "temp_storage_gb": 32},
        "Standard_D8s_v3": {"vcpus": 8, "memory_gb": 32, "temp_storage_gb": 64},
        
        # Default fallback
        "unknown": {"vcpus": "Unknown", "memory_gb": "Unknown", "temp_storage_gb": "Unknown"}
    }
    
    return size_info.get(vm_size, size_info["unknown"])


def parse_azure_date(date_str: str) -> Optional[datetime]:
    """Parse Azure date string to datetime object"""
    try:
        # Azure typically uses ISO format with timezone
        if 'T' in date_str and ('Z' in date_str or '+' in date_str):
            # Remove timezone info for simple parsing
            clean_date = date_str.replace('Z', '').split('+')[0].split('T')[0]
            return datetime.strptime(clean_date, '%Y-%m-%d')
        return None
    except Exception as e:
        logging.error(f"Failed to parse Azure date '{date_str}': {e}")
        return None


def get_billing_period_dates() -> Dict[str, str]:
    """Get current billing period start and end dates"""
    now = datetime.now()
    # Billing period is typically month-based
    start_of_month = now.replace(day=1)
    
    # Get next month's first day, then subtract one day for end of current month
    if now.month == 12:
        end_of_month = datetime(now.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_of_month = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
    
    return {
        "start_date": start_of_month.strftime('%Y-%m-%d'),
        "end_date": end_of_month.strftime('%Y-%m-%d')
    }


def sanitize_resource_name(name: str) -> str:
    """Sanitize resource name for Azure compatibility"""
    # Azure resource names have specific requirements
    # Generally: alphanumeric, hyphens, underscores, periods
    import re
    
    # Remove invalid characters
    sanitized = re.sub(r'[^a-zA-Z0-9\-_.]', '', name)
    
    # Ensure it doesn't start or end with special characters
    sanitized = sanitized.strip('-_.')
    
    # Ensure minimum length
    if len(sanitized) < 1:
        sanitized = "resource"
    
    # Ensure maximum length (varies by resource type, 64 is conservative)
    if len(sanitized) > 64:
        sanitized = sanitized[:64]
    
    return sanitized


def build_azure_filter(resource_type: Optional[str] = None, 
                      location: Optional[str] = None,
                      tag_filters: Optional[Dict[str, str]] = None) -> str:
    """Build JMESPath filter for Azure CLI queries"""
    filters = []
    
    if resource_type:
        filters.append(f"type=='{resource_type}'")
    
    if location:
        filters.append(f"location=='{location}'")
    
    if tag_filters:
        for key, value in tag_filters.items():
            filters.append(f"tags.{key}=='{value}'")
    
    if filters:
        return f"[?{' && '.join(filters)}]"
    return ""
