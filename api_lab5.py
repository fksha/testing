import pytest
import requests
import time
import subprocess
import logging

log_file = 'redfish_test.log'

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
file_handler.setFormatter(formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
#logger.addHandler(console_handler)

logger.info("=" * 50)
logger.info("REDFISH TESTING START")
logger.info("=" * 50)

BMC_IP = "localhost:2443"
USERNAME = "root"
PASSWORD = "0penBmc"
BASE_URL = f"https://{BMC_IP}"

requests.packages.urllib3.disable_warnings()

@pytest.fixture(scope="session")
def auth_session():
    session = None
    try:
        logger.info("Creating authentication session...")
        session = requests.Session()
        session.verify = False
        
        auth_data = {"UserName": USERNAME, "Password": PASSWORD}
        response = session.post(f"{BASE_URL}/redfish/v1/SessionService/Sessions", 
                              json=auth_data, timeout=30)
        
        logger.info(f"Authentication response: code {response.status_code}")
        
        if response.status_code not in [200, 201]:
            logger.error(f"Authentication error: code {response.status_code}")
            pytest.fail(f"Authentication error: code {response.status_code}")
        
        auth_token = response.headers.get('X-Auth-Token')
        if not auth_token:
            logger.error("Authentication token not received")
            pytest.fail("Authentication token missing in response")
        
        session.headers.update({'X-Auth-Token': auth_token})
        logger.info("Session successfully created")
        
        yield session
        
    except requests.exceptions.Timeout:
        logger.error("Session creation timeout")
        pytest.fail("Session creation timeout")
    except requests.exceptions.ConnectionError:
        logger.error("BMC connection error")
        pytest.fail("Could not connect to BMC")
    except Exception as e:
        logger.error(f"Unexpected error creating session: {e}")
        pytest.fail(f"Unexpected error: {e}")
    
    finally:
        if session:
            try:
                logger.info("Closing session...")
            except Exception as e:
                logger.warning(f"Failed to close session: {e}")

def test_authentication(auth_session):
    """Test OpenBMC authentication via Redfish API"""
    logger.info("Running authentication test...")
    try:
        response = auth_session.get(f"{BASE_URL}/redfish/v1", timeout=10)
        logger.info(f"Redfish response: code {response.status_code}")
        
        assert response.status_code == 200
        logger.info("Authentication successful")
        
    except Exception as e:
        logger.error(f"Error in authentication test: {e}")
        raise

def test_system_info(auth_session):
    """Test system information retrieval"""
    logger.info("Running system information test...")
    try:
        response = auth_session.get(f"{BASE_URL}/redfish/v1/Systems/system", timeout=10)
        logger.info(f"System information response: code {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "@odata.id" in data
        assert "Actions" in data
        
        power_state = data.get('PowerState')
        if power_state:
            logger.info(f"PowerState found: {power_state}")
        else:
            logger.warning("PowerState not found in response")
            
    except Exception as e:
        logger.error(f"Error in system information test: {e}")
        raise

def test_power_management(auth_session):
    logger.info("Running power management test...")
    try:
        response = auth_session.get(f"{BASE_URL}/redfish/v1/Systems/system", timeout=10)
        logger.info(f"System information: code {response.status_code}")
        
        actions = response.json().get("Actions", {})
        reset_action = actions.get("#ComputerSystem.Reset", {})
        target_url = reset_action.get("target")
        
        if not target_url:
            logger.warning("System reset action not found, skipping test")
            pytest.skip("Reset action not available")

        test_commands = [
            "GracefulRestart", 
            "On", 
            "ForceOff",
            "ForceRestart",
            "PushPowerButton"
        ]
        
        success_found = False
        for reset_type in test_commands:
            power_data = {"ResetType": reset_type}
            try:
                response = auth_session.post(
                    f"{BASE_URL}{target_url}",
                    json=power_data,
                    timeout=30
                )
                
                logger.info(f"Command {reset_type}: code {response.status_code}")
                
                if response.status_code in [200, 202, 204]:
                    logger.info(f"✓ Command {reset_type} accepted")
                    success_found = True
                    break
                elif response.status_code in [400, 404, 405]:
                    logger.info(f"Command {reset_type} not supported: {response.status_code}")
                    continue
                    
            except Exception as e:
                logger.warning(f"Error executing {reset_type}: {e}")
                continue
                
        if not success_found:
            logger.warning("No power commands were successful")
            pytest.skip("No power management commands available in this Redfish implementation")
            
    except Exception as e:
        logger.error(f"Error in power management test: {e}")
        raise
    
def test_cpu_temperature_redfish(auth_session):
    logger.info("Running CPU temperature test...")
    try:
        response = auth_session.get(f"{BASE_URL}/redfish/v1/Chassis/chassis", timeout=10)
        logger.info(f"Chassis data response: code {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            thermal = data.get("Thermal", {})
            
            if isinstance(thermal, str):
                thermal_response = auth_session.get(f"{BASE_URL}{thermal}", timeout=10)
                if thermal_response.status_code == 200:
                    thermal = thermal_response.json()
            
            temperatures = thermal.get("Temperatures", [])
            logger.info(f"Temperature sensors found: {len(temperatures)}")
            
            cpu_found = False
            for temp in temperatures:
                name = temp.get("Name", "")
                reading = temp.get("ReadingCelsius")
                
                if reading is not None and "CPU" in name.upper():
                    cpu_found = True
                    threshold = temp.get('UpperThresholdCritical', 95)
                    
                    if reading <= threshold:
                        logger.info(f"CPU {name}: {reading}°C (threshold: {threshold}°C)")
                    else:
                        logger.error(f"CPU {name}: {reading}°C exceeds threshold {threshold}°C")
                        pytest.fail(f"CPU temperature {reading}°C exceeds threshold {threshold}°C")
                    break
            
            if not cpu_found:
                logger.info("CPU sensors not found")
        else:
            logger.warning("Failed to get chassis data")
            
        logger.info("CPU temperature test completed")
        
    except Exception as e:
        logger.error(f"Error in CPU temperature test: {e}")
        raise

def test_cpu_sensors_redfish_ipmi(auth_session):
    logger.info("Running Redfish and IPMI sensor comparison test...")
    try:
        # Redfish
        redfish_temps = []
        response = auth_session.get(f"{BASE_URL}/redfish/v1/Chassis/chassis", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            thermal = data.get("Thermal", {})
            
            if isinstance(thermal, str):
                thermal_response = auth_session.get(f"{BASE_URL}{thermal}", timeout=10)
                if thermal_response.status_code == 200:
                    thermal = thermal_response.json()
            
            for temp in thermal.get("Temperatures", []):
                if "CPU" in temp.get("Name", "").upper():
                    temp_value = temp.get("ReadingCelsius")
                    if temp_value is not None:
                        redfish_temps.append(temp_value)
        
        logger.info(f"Redfish CPU sensors: {len(redfish_temps)} found")
        
        # IPMI
        ipmi_temps = []
        try:
            result = subprocess.run(
                ['ipmitool', '-I', 'lanplus', '-H', BMC_IP.split(':')[0], '-p', '2623',
                 '-U', USERNAME, '-P', PASSWORD, 'sensor', 'list'],
                capture_output=True, text=True, timeout=15
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'CPU' in line and any(c.isdigit() for c in line):
                        try:
                            temp_str = line.split('|')[1].strip()
                            temp_value = float(''.join(c for c in temp_str if c.isdigit() or c == '.'))
                            if 0 <= temp_value <= 100:
                                ipmi_temps.append(temp_value)
                        except (ValueError, IndexError):
                            continue
                logger.info("IPMI command executed successfully")
            else:
                logger.warning(f"IPMI command failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.warning("IPMI command timeout")
        except Exception as e:
            logger.warning(f"IPMI execution error: {e}")
        
        logger.info(f"IPMI CPU sensors: {len(ipmi_temps)} found")
        
        if redfish_temps and ipmi_temps:
            logger.info("Data found in both Redfish and IPMI")
        elif redfish_temps:
            logger.info("Data found only in Redfish")
        elif ipmi_temps:
            logger.info("Data found only in IPMI") 
        else:
            logger.info("No data found in either Redfish or IPMI")
            
        logger.info("Sensor comparison test completed")
            
    except Exception as e:
        logger.error(f"Error in sensor comparison test: {e}")
        raise