# ActionRouter: Triggers follow-up actions based on agent outputs

class ActionRouter:
    def __init__(self, memory):
        self.memory = memory

    def route(self, agent_output):
        """
        Trigger simulated REST actions based on agent output.
        """
        import requests
        import time
        actions = []
        # Simulate REST calls based on action field
        action_map = {
            'escalate_to_crm': {'url': 'http://localhost:8000/crm/escalate', 'method': 'POST'},
            'flag_high_value_invoice': {'url': 'http://localhost:8000/risk_alert', 'method': 'POST'},
            'flag_compliance_risk': {'url': 'http://localhost:8000/risk_alert', 'method': 'POST'},
            'log_alert': {'url': 'http://localhost:8000/alerts', 'method': 'POST'},
            'log_and_close': {'url': 'http://localhost:8000/log', 'method': 'POST'},
            'store_ok': {'url': 'http://localhost:8000/store', 'method': 'POST'},
        }
        action = agent_output.get('action') or agent_output.get('fields', {}).get('action')
        payload = agent_output
        if action in action_map:
            url = action_map[action]['url']
            method = action_map[action]['method']
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Simulate REST call (replace with real requests.post in production)
                    # resp = requests.request(method, url, json=payload, timeout=2)
                    # For demo, just append action
                    actions.append({'action': action, 'url': url, 'payload': payload, 'status': 'success', 'attempt': attempt+1})
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        actions.append({'action': action, 'url': url, 'payload': payload, 'status': f'failed: {str(e)}', 'attempt': attempt+1})
                    else:
                        time.sleep(1)
        else:
            actions.append({'action': 'noop', 'status': 'no action triggered'})
        return actions
