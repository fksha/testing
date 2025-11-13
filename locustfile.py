
from locust import HttpUser, task, between

BMC_IP = "host.docker.internal:2443" 
BMC_USER = "root"
BMC_PASS = "0penBmc"

JSONPLACEHOLDER_URL = "https://jsonplaceholder.typicode.com"

class OpenBMCUser(HttpUser):
    host = f"https://{BMC_IP}"
    wait_time = between(1, 3)  

    def on_start(self):
        self.client.auth = (BMC_USER, BMC_PASS)
        self.client.verify = False  

    @task(2)  
    def get_system_info(self):
        self.client.get("/redfish/v1/Systems/system", name="System Info")

    @task(1)  # вес 1
    def get_power_state(self):
        with self.client.get(
            "/redfish/v1/Systems/system",
            name="PowerState",
            catch_response=True
        ) as response:
            try:
                data = response.json()
                power_state = data.get("PowerState", "Unknown")
                if power_state not in ["On", "Off", "PoweringOn", "PoweringOff"]:
                    response.failure(f"Unexpected PowerState: {power_state}")
            except:
                response.failure("Failed to parse PowerState")

class PublicAPIUser(HttpUser):
    host = JSONPLACEHOLDER_URL
    wait_time = between(0.5, 2)

    @task
    def get_posts(self):
        self.client.get("/posts", name="JSONPlaceholder: Posts")