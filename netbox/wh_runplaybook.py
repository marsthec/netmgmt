import requests
from extras.scripts import Script, ObjectVar
from dcim.models import Device

class ForceSyncDevice(Script):
    class Meta:
        name = "Automation Playbook Runner"
        description = "Manual launch via Webhook Proxy"

    device = ObjectVar(model=Device)

    run_backup = BoolenVar(default=False, description="Run backup before sync")

    task = ChoiceVar(choices=[
        ('inventory', 'Read Inventory Only and populate Netbox data'),
        ('compare', 'Compare configurations and show diff'),
    ], default='inventory', description="Choose your task")

    def run(self, data, commit):
        device = data['device']
        
        # Send a request to the webhook proxy with the device name and task details
        proxy_url = "http://webhook-proxy:5000/netbox-webhook"
        payload = {
            "device": device.name,
            "action": "custom_run",
            "params": {
                "run_backup": data['run_backup'],
                "task": data['task']
            }
        }
        
        try:
            response = requests.post(proxy_url, json=payload, timeout=5)
            if response.status_code == 200:
                self.log_success(f"Task for {device.name} was sent to proxy.")
            else:
                self.log_failure(f"Proxy replied with error: {response.status_code}")
        except Exception as e:
            self.log_failure(f"Can't connect to proxy: {e}")
