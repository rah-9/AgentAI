# JSONAgent: Parses webhook data, validates schema, flags anomalies
import json
import os
import datetime
import re
import random
from typing import Dict, List, Any, Optional, Union

class JSONAgent:
    def __init__(self, memory=None):
        self.memory = memory
        
        # Define known event types and their required schemas
        self.schemas = {
            'rfq': {
                'required_fields': ['rfq_id', 'customer', 'items', 'date_requested', 'priority'],
                'types': {
                    'rfq_id': str,
                    'customer': dict,
                    'items': list,
                    'date_requested': str,
                    'priority': str
                },
                'nested_required': {
                    'customer': ['id', 'name', 'contact_email'],
                    'items[*]': ['item_id', 'quantity', 'description']
                }
            },
            'invoice': {
                'required_fields': ['invoice_id', 'customer_id', 'amount', 'date_issued', 'items'],
                'types': {
                    'invoice_id': str,
                    'customer_id': str,
                    'amount': (int, float),
                    'date_issued': str,
                    'items': list
                },
                'nested_required': {
                    'items[*]': ['item_id', 'quantity', 'price', 'description']
                }
            },
            'complaint': {
                'required_fields': ['complaint_id', 'customer_id', 'description', 'severity', 'date_filed'],
                'types': {
                    'complaint_id': str,
                    'customer_id': str,
                    'description': str,
                    'severity': str,
                    'date_filed': str
                }
            },
            'fraud_alert': {
                'required_fields': ['alert_id', 'account_id', 'type', 'risk_score', 'timestamp'],
                'types': {
                    'alert_id': str,
                    'account_id': str,
                    'type': str,
                    'risk_score': (int, float),
                    'timestamp': str
                }
            }
        }
        
        # Define expected value ranges and patterns
        self.validation_rules = {
            'date_pattern': r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$',
            'email_pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'priority_values': ['low', 'medium', 'high', 'critical'],
            'severity_values': ['minor', 'moderate', 'major', 'critical'],
            'risk_threshold': 0.7,  # Risk scores above this are flagged
            'quantity_min': 1,
            'price_min': 0.01
        }

    def validate_field_type(self, field_name: str, value: Any, expected_type: Union[type, tuple]) -> List[str]:
        """Validate that a field has the expected type"""
        anomalies = []
        
        if not isinstance(value, expected_type):
            type_names = expected_type.__name__ if isinstance(expected_type, type) else \
                         ' or '.join(t.__name__ for t in expected_type)
            anomalies.append(f"Field '{field_name}' should be {type_names}, got {type(value).__name__}")
            
        return anomalies

    def validate_nested_fields(self, data: Dict, path: str, required_fields: List[str]) -> List[str]:
        """Validate required fields in nested structures including arrays"""
        anomalies = []
        
        # Handle array validation with [*] notation
        if '[*]' in path:
            base_path, array_part = path.split('[*]')
            if base_path in data and isinstance(data[base_path], list):
                for i, item in enumerate(data[base_path]):
                    if not isinstance(item, dict):
                        anomalies.append(f"Item {i} in {base_path} should be an object")
                        continue
                        
                    for field in required_fields:
                        if field not in item:
                            anomalies.append(f"Missing required field '{field}' in {base_path}[{i}]")
        else:
            # Regular nested object validation
            if path in data and isinstance(data[path], dict):
                for field in required_fields:
                    if field not in data[path]:
                        anomalies.append(f"Missing required field '{field}' in {path}")
            else:
                anomalies.append(f"Missing or invalid nested object '{path}'")
                
        return anomalies

    def validate_pattern(self, field_name: str, value: str, pattern: str) -> List[str]:
        """Validate that a string field matches a regex pattern"""
        anomalies = []
        
        if not re.match(pattern, value):
            anomalies.append(f"Field '{field_name}' with value '{value}' does not match expected pattern")
            
        return anomalies

    def validate_range(self, field_name: str, value: Union[int, float], min_val: Optional[float] = None, 
                      max_val: Optional[float] = None) -> List[str]:
        """Validate that a numeric field is within expected range"""
        anomalies = []
        
        if min_val is not None and value < min_val:
            anomalies.append(f"Field '{field_name}' with value {value} is below minimum {min_val}")
            
        if max_val is not None and value > max_val:
            anomalies.append(f"Field '{field_name}' with value {value} exceeds maximum {max_val}")
            
        return anomalies

    def validate_enum(self, field_name: str, value: str, allowed_values: List[str]) -> List[str]:
        """Validate that a field's value is in a set of allowed values"""
        anomalies = []
        
        if value not in allowed_values:
            anomalies.append(f"Field '{field_name}' with value '{value}' not in allowed values: {', '.join(allowed_values)}")
            
        return anomalies

    def process(self, json_data):
        """Process JSON data with comprehensive schema validation and anomaly detection"""
        # If json_data is a file path, read the file
        if isinstance(json_data, str) and os.path.isfile(json_data):
            try:
                with open(json_data, 'r', encoding='utf-8') as f:
                    try:
                        json_data = json.load(f)
                    except json.JSONDecodeError as e:
                        return {
                            "status": "error",
                            "format": "JSON",
                            "fields": {"error": f"Invalid JSON: {str(e)}", "text_excerpt": f"Failed to parse JSON: {str(e)}"},
                            "valid": False,
                            "anomalies": [f"JSON parse error: {str(e)}"]
                        }
            except Exception as e:
                return {
                    "status": "error",
                    "format": "JSON",
                    "fields": {"error": f"File read error: {str(e)}", "text_excerpt": f"Failed to read file: {str(e)}"},
                    "valid": False,
                    "anomalies": [f"File read error: {str(e)}"]
                }
                
        # Check if json_data is already parsed
        if not isinstance(json_data, dict):
            try:
                if isinstance(json_data, str):
                    json_data = json.loads(json_data)
                else:
                    return {
                        "status": "error",
                        "format": "JSON",
                        "fields": {"error": "Input is not valid JSON or a file path", "text_excerpt": "Invalid input type"},
                        "valid": False,
                        "anomalies": ["Input is not a dictionary, JSON string, or file path"]
                    }
            except json.JSONDecodeError as e:
                return {
                    "status": "error",
                    "format": "JSON",
                    "fields": {"error": f"Invalid JSON: {str(e)}", "text_excerpt": f"Failed to parse JSON: {str(e)}"},
                    "valid": False,
                    "anomalies": [f"JSON parse error: {str(e)}"]
                }
                
        # Initialize result dictionary
        result = {
            "status": "processed",
            "format": "JSON",
            "valid": True,
            "anomalies": [],
            "fields": {},
            "suggested_action": None
        }
        
        anomalies = []
        
        # Validate top-level required fields
        top_level_required = ['event_type', 'payload', 'timestamp', 'source', 'version']
        for field in top_level_required:
            if field not in json_data:
                anomalies.append(f'Missing required top-level field: {field}')
        
        # Extract and store basic fields
        event_type = json_data.get('event_type', '').lower()
        payload = json_data.get('payload', {})
        timestamp = json_data.get('timestamp', '')
        source = json_data.get('source', '')
        version = json_data.get('version', '')
        
        # Store extracted fields
        result['fields'] = {
            'event_type': event_type,
            'source': source,
            'version': version,
            'timestamp': timestamp
        }
        
        # Type validations for top-level fields
        if 'timestamp' in json_data:
            anomalies.extend(self.validate_field_type('timestamp', timestamp, str))
            if isinstance(timestamp, str):
                anomalies.extend(self.validate_pattern('timestamp', timestamp, self.validation_rules['date_pattern']))
                
        if 'payload' in json_data:
            anomalies.extend(self.validate_field_type('payload', payload, dict))
        
        if 'version' in json_data:
            anomalies.extend(self.validate_field_type('version', version, (str, int, float)))
            
        # Validate payload against known schema based on event_type
        if event_type in self.schemas and isinstance(payload, dict):
            schema = self.schemas[event_type]
            
            # Check required fields
            for field in schema['required_fields']:
                if field not in payload:
                    anomalies.append(f"Missing required field '{field}' for event_type '{event_type}'")
            
            # Type validations
            for field, expected_type in schema['types'].items():
                if field in payload:
                    anomalies.extend(self.validate_field_type(field, payload[field], expected_type))
            
            # Nested structure validations
            for path, required_fields in schema.get('nested_required', {}).items():
                anomalies.extend(self.validate_nested_fields(payload, path, required_fields))
            
            # Additional validations based on field names and values
            if event_type == 'rfq':
                if 'priority' in payload:
                    anomalies.extend(self.validate_enum('priority', payload['priority'], 
                                                      self.validation_rules['priority_values']))
                if 'date_requested' in payload:
                    anomalies.extend(self.validate_pattern('date_requested', payload['date_requested'], 
                                                         self.validation_rules['date_pattern']))
                if 'customer' in payload and isinstance(payload['customer'], dict) and 'contact_email' in payload['customer']:
                    anomalies.extend(self.validate_pattern('contact_email', payload['customer']['contact_email'], 
                                                         self.validation_rules['email_pattern']))
                if 'items' in payload and isinstance(payload['items'], list):
                    for i, item in enumerate(payload['items']):
                        if isinstance(item, dict) and 'quantity' in item:
                            anomalies.extend(self.validate_range(f"items[{i}].quantity", item['quantity'], 
                                                               self.validation_rules['quantity_min']))
                            
            elif event_type == 'invoice':
                if 'amount' in payload:
                    anomalies.extend(self.validate_range('amount', payload['amount'], self.validation_rules['price_min']))
                if 'date_issued' in payload:
                    anomalies.extend(self.validate_pattern('date_issued', payload['date_issued'], 
                                                         self.validation_rules['date_pattern']))
                if 'items' in payload and isinstance(payload['items'], list):
                    for i, item in enumerate(payload['items']):
                        if isinstance(item, dict):
                            if 'quantity' in item:
                                anomalies.extend(self.validate_range(f"items[{i}].quantity", item['quantity'], 
                                                                   self.validation_rules['quantity_min']))
                            if 'price' in item:
                                anomalies.extend(self.validate_range(f"items[{i}].price", item['price'], 
                                                                   self.validation_rules['price_min']))
                                
            elif event_type == 'complaint':
                if 'severity' in payload:
                    anomalies.extend(self.validate_enum('severity', payload['severity'], 
                                                      self.validation_rules['severity_values']))
                if 'date_filed' in payload:
                    anomalies.extend(self.validate_pattern('date_filed', payload['date_filed'], 
                                                         self.validation_rules['date_pattern']))
                    
            elif event_type == 'fraud_alert':
                if 'risk_score' in payload:
                    if payload['risk_score'] > self.validation_rules['risk_threshold']:
                        result['fields']['risk_flag'] = True
                        result['fields']['risk_score'] = payload['risk_score']
                if 'timestamp' in payload:
                    anomalies.extend(self.validate_pattern('timestamp', payload['timestamp'], 
                                                         self.validation_rules['date_pattern']))
        else:
            if not event_type:
                anomalies.append("Missing or empty event_type")
            elif event_type not in self.schemas:
                anomalies.append(f"Unknown event_type: '{event_type}'. Supported types: {', '.join(self.schemas.keys())}")
            
            if not isinstance(payload, dict):
                anomalies.append("Payload must be a JSON object")
        
        # Store all anomalies
        result['anomalies'] = anomalies
        result['valid'] = len(anomalies) == 0
        
        # Generate a tracking ID for reference
        tracking_id = f"JSON-{random.randint(10000, 99999)}"
        result['tracking_id'] = tracking_id
        
        # Build a human-readable summary
        summary = []
        summary.append(f"Event Type: {event_type or 'N/A'}")
        summary.append(f"Source: {source or 'N/A'}")
        summary.append(f"Version: {version or 'N/A'}")
        summary.append(f"Timestamp: {timestamp or 'N/A'}")
        summary.append(f"Tracking ID: {tracking_id}")
        summary.append(f"Validation: {'✓ VALID' if result['valid'] else '✗ INVALID'}")
        summary.append("")
        
        # Add payload summary
        summary.append("Payload:")
        if isinstance(payload, dict) and payload:
            # Display first level of payload
            for k, v in payload.items():
                if isinstance(v, (dict, list)):
                    summary.append(f"  - {k}: {type(v).__name__} with {len(v)} items")
                else:
                    summary.append(f"  - {k}: {v}")
        else:
            summary.append("  (No payload fields)")
        
        # Add anomalies to summary
        if anomalies:
            summary.append("")
            summary.append("Anomalies:")
            for a in anomalies:
                summary.append(f"  - {a}")
        
        # Store the summary as text excerpt
        result['fields']['text_excerpt'] = '\n'.join(summary)
        
        # Determine suggested action based on validation results
        if anomalies:
            result['suggested_action'] = {
                "action": "alert",
                "target": "data_quality",
                "priority": "high" if len(anomalies) > 3 else "medium",
                "details": f"Data quality issues detected in {event_type} webhook",
                "endpoint": "/alerts/data_quality"
            }
        else:
            if event_type == 'fraud_alert' and payload.get('risk_score', 0) > self.validation_rules['risk_threshold']:
                result['suggested_action'] = {
                    "action": "escalate",
                    "target": "risk",
                    "priority": "critical",
                    "details": f"High risk score detected: {payload.get('risk_score')}",
                    "endpoint": "/risk/escalate"
                }
            else:
                result['suggested_action'] = {
                    "action": "process",
                    "target": "webhook",
                    "priority": "normal",
                    "details": f"Valid {event_type} webhook received",
                    "endpoint": f"/webhooks/{event_type}/process"
                }
        
        return result
