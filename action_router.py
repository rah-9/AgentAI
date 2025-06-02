"""
Action Router: Routes actions to appropriate systems (CRM, risk, email, etc.)
Simulates REST API calls with retry logic and response handling
"""
import json
import time
import random
import logging
import requests
import datetime
from typing import Dict, Any, List, Optional, Union
from requests.exceptions import RequestException, Timeout, ConnectionError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('action_router')

class ActionRouter:
    def __init__(self, memory=None, simulate=True):
        """
        Initialize the action router
        
        Args:
            memory: Shared memory store for logging actions
            simulate: If True, simulate API calls instead of making real ones
        """
        self.memory = memory
        self.simulate = simulate
        
        # Define available endpoints and their configurations
        self.endpoints = {
            # CRM actions
            "/crm/escalate": {
                "method": "POST",
                "base_url": "https://api.example.com",
                "success_rate": 0.95,
                "timeout": 2.0,
                "retry_count": 3,
                "retry_delay": 1.0
            },
            "/crm/ticket/create": {
                "method": "POST",
                "base_url": "https://api.example.com",
                "success_rate": 0.98,
                "timeout": 1.5,
                "retry_count": 2,
                "retry_delay": 0.5
            },
            "/crm/contact/update": {
                "method": "PUT",
                "base_url": "https://api.example.com",
                "success_rate": 0.97,
                "timeout": 1.0,
                "retry_count": 2,
                "retry_delay": 0.5
            },
            # Risk management
            "/risk/escalate": {
                "method": "POST",
                "base_url": "https://risk.example.com",
                "success_rate": 0.99,
                "timeout": 1.0,
                "retry_count": 3,
                "retry_delay": 0.5
            },
            "/risk/alert": {
                "method": "POST",
                "base_url": "https://risk.example.com",
                "success_rate": 0.98,
                "timeout": 1.0,
                "retry_count": 3,
                "retry_delay": 0.5
            },
            # Alerts
            "/alerts/data_quality": {
                "method": "POST",
                "base_url": "https://alerts.example.com",
                "success_rate": 0.96,
                "timeout": 1.0,
                "retry_count": 2,
                "retry_delay": 0.5
            },
            "/alerts/send_email": {
                "method": "POST",
                "base_url": "https://alerts.example.com", 
                "success_rate": 0.95,
                "timeout": 2.0,
                "retry_count": 3,
                "retry_delay": 0.7
            },
            # Processing webhooks
            "/webhooks/{event_type}/process": {
                "method": "POST",
                "base_url": "https://webhooks.example.com",
                "success_rate": 0.93,
                "timeout": 2.0,
                "retry_count": 2,
                "retry_delay": 1.0
            },
            # Default fallback endpoint
            "default": {
                "method": "POST",
                "base_url": "https://api.example.com",
                "success_rate": 0.90,
                "timeout": 1.0,
                "retry_count": 1,
                "retry_delay": 0.5
            }
        }
    
    def route(self, agent_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route actions based on the agent result
        
        Args:
            agent_result: Result from agent processing
            
        Returns:
            Dict with action results
        """
        result = {
            "status": "pending",
            "actions_taken": [],
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Extract suggested action if available
        action = agent_result.get("suggested_action", None)
        
        # Legacy support for old format where action was a string
        if isinstance(agent_result.get("action"), str):
            action = {
                "action": agent_result["action"],
                "target": "legacy",
                "priority": "normal",
                "details": "Legacy action format",
                "endpoint": f"/actions/{agent_result['action']}"
            }
        
        # Check if there's an action to route
        if not action:
            if agent_result.get("valid", True) is False:
                # If data is invalid but no explicit action, create a default data quality alert
                action = {
                    "action": "alert",
                    "target": "data_quality",
                    "priority": "medium",
                    "details": "Data validation failed",
                    "endpoint": "/alerts/data_quality"
                }
            else:
                # If no action and data is valid, log and return
                result["status"] = "no_action_required"
                if self.memory:
                    self.memory.log_action("no_action", {}, "No action required", "success")
                return result
        
        # Process action
        action_result = self._process_action(action, agent_result)
        result["actions_taken"].append(action_result)
        
        # Update status based on action results
        if any(a.get("status") == "failed" for a in result["actions_taken"]):
            result["status"] = "partially_failed"
        else:
            result["status"] = "success"
        
        return result
    
    def _process_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single action
        
        Args:
            action: Action details
            context: Original agent result for context
            
        Returns:
            Dict with action processing result
        """
        action_type = action.get("action", "process")
        target = action.get("target", "default")
        priority = action.get("priority", "normal")
        details = action.get("details", "")
        endpoint = action.get("endpoint", f"/actions/{action_type}")
        
        # Replace any placeholders in the endpoint
        if "{event_type}" in endpoint and "event_type" in context.get("fields", {}):
            endpoint = endpoint.replace("{event_type}", context["fields"]["event_type"])
        
        # Get endpoint configuration
        endpoint_config = self.endpoints.get(endpoint, self.endpoints["default"])
        
        # Prepare request data
        request_data = {
            "action_type": action_type,
            "target": target,
            "priority": priority,
            "details": details,
            "timestamp": datetime.datetime.now().isoformat(),
            "context": {
                "format": context.get("format", "Unknown"),
                "tracking_id": context.get("tracking_id", f"TR-{random.randint(10000, 99999)}"),
                "fields": {k: v for k, v in context.get("fields", {}).items() if k != "text_excerpt"}
            }
        }
        
        # Add priority-specific fields
        if priority in ["high", "critical"]:
            request_data["escalation"] = True
            request_data["notify_manager"] = priority == "critical"
        
        # Start tracking the action
        action_result = {
            "action_type": action_type,
            "target": target,
            "endpoint": endpoint,
            "priority": priority,
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "pending",
            "attempts": 0,
            "response": None
        }
        
        # Execute the action with retry logic
        max_retries = endpoint_config["retry_count"]
        retry_delay = endpoint_config["retry_delay"]
        
        for attempt in range(max_retries + 1):
            action_result["attempts"] += 1
            
            try:
                # If simulating, use simulated response
                if self.simulate:
                    response = self._simulate_api_call(endpoint_config, request_data)
                else:
                    # Real API call (not implemented for this example)
                    url = f"{endpoint_config['base_url']}{endpoint}"
                    response = requests.request(
                        method=endpoint_config["method"],
                        url=url,
                        json=request_data,
                        timeout=endpoint_config["timeout"]
                    )
                    response = {
                        "success": response.status_code < 400,
                        "status_code": response.status_code,
                        "data": response.json() if response.status_code < 400 else {},
                        "error": response.text if response.status_code >= 400 else None
                    }
                
                # Process response
                if response["success"]:
                    action_result["status"] = "success"
                    action_result["response"] = response
                    
                    # Log successful action
                    if self.memory:
                        self.memory.log_action(
                            action_type=action_type,
                            data=request_data,
                            result=f"Success: {details}",
                            status="success"
                        )
                    
                    break
                else:
                    # Failed but might retry
                    action_result["response"] = response
                    logger.warning(f"Action failed: {action_type} to {endpoint}. Attempt {attempt+1}/{max_retries+1}")
                    
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                    else:
                        action_result["status"] = "failed"
                        
                        # Log failed action
                        if self.memory:
                            self.memory.log_action(
                                action_type=action_type,
                                data=request_data,
                                result=f"Failed after {attempt+1} attempts: {response.get('error', 'Unknown error')}",
                                status="failed"
                            )
            
            except (RequestException, Timeout, ConnectionError) as e:
                # Handle network errors
                logger.error(f"Network error in action {action_type}: {str(e)}")
                
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    action_result["status"] = "failed"
                    action_result["response"] = {"success": False, "error": str(e)}
                    
                    # Log failed action
                    if self.memory:
                        self.memory.log_action(
                            action_type=action_type,
                            data=request_data,
                            result=f"Network error after {attempt+1} attempts: {str(e)}",
                            status="failed"
                        )
            
            except Exception as e:
                # Handle unexpected errors
                logger.error(f"Unexpected error in action {action_type}: {str(e)}")
                action_result["status"] = "failed"
                action_result["response"] = {"success": False, "error": str(e)}
                
                # Log failed action
                if self.memory:
                    self.memory.log_action(
                        action_type=action_type,
                        data=request_data,
                        result=f"Unexpected error: {str(e)}",
                        status="failed"
                    )
                break
        
        return action_result
    
    def _simulate_api_call(self, endpoint_config: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate an API call for testing
        
        Args:
            endpoint_config: Configuration for the endpoint
            request_data: Request data
            
        Returns:
            Dict with simulated response
        """
        # Simulate network delay
        time.sleep(random.uniform(0.1, endpoint_config["timeout"]))
        
        # Determine if the call succeeds based on success_rate
        success = random.random() < endpoint_config["success_rate"]
        
        if success:
            # Generate a successful response
            return {
                "success": True,
                "status_code": 200,
                "data": {
                    "message": f"Successfully processed {request_data['action_type']} for {request_data['target']}",
                    "id": f"ACT-{random.randint(100000, 999999)}",
                    "timestamp": datetime.datetime.now().isoformat()
                }
            }
        else:
            # Generate an error response
            error_types = ["timeout", "server_error", "validation_error", "auth_error"]
            error_type = random.choice(error_types)
            
            if error_type == "timeout":
                raise Timeout("Simulated timeout error")
            elif error_type == "server_error":
                return {
                    "success": False,
                    "status_code": 500,
                    "error": "Internal Server Error: The server encountered an unexpected condition."
                }
            elif error_type == "validation_error":
                return {
                    "success": False,
                    "status_code": 400,
                    "error": "Validation Error: The request data did not pass validation."
                }
            else:  # auth_error
                return {
                    "success": False,
                    "status_code": 401,
                    "error": "Authentication Error: Invalid or expired credentials."
                }
    
    def process_batch(self, batch_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of agent results
        
        Args:
            batch_results: List of agent results
            
        Returns:
            Dict with batch processing results
        """
        batch_result = {
            "status": "success",
            "total": len(batch_results),
            "successful": 0,
            "failed": 0,
            "actions": []
        }
        
        for idx, result in enumerate(batch_results):
            try:
                action_result = self.route(result)
                batch_result["actions"].append(action_result)
                
                if action_result["status"] in ["success", "no_action_required"]:
                    batch_result["successful"] += 1
                else:
                    batch_result["failed"] += 1
            except Exception as e:
                logger.error(f"Error processing batch item {idx}: {str(e)}")
                batch_result["failed"] += 1
                batch_result["actions"].append({
                    "status": "error",
                    "error": str(e),
                    "item_index": idx
                })
        
        # Update overall batch status
        if batch_result["failed"] > 0:
            if batch_result["successful"] > 0:
                batch_result["status"] = "partially_successful"
            else:
                batch_result["status"] = "failed"
        
        return batch_result
