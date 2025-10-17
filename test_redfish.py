import pytest
import requests
import time
import subprocess
import logging

log_file = 'redfish_test.log'

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Создаем formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# File handler
file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
file_handler.setFormatter(formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Добавляем handlers
logger.addHandler(file_handler)
#logger.addHandler(console_handler)

# Тестовые сообщения
logger.info("=" * 50)
logger.info("НАЧАЛО ТЕСТИРОВАНИЯ REDFISH")
logger.info("=" * 50)

# Конфигурация
BMC_IP = "localhost:2443"
USERNAME = "root"
PASSWORD = "0penBmc"
BASE_URL = f"https://{BMC_IP}"

# Отключение предупреждений о SSL
requests.packages.urllib3.disable_warnings()

@pytest.fixture(scope="session")
def auth_session():
    session = None
    try:
        logger.info("Создание сессии аутентификации...")
        session = requests.Session()
        session.verify = False
        
        auth_data = {"UserName": USERNAME, "Password": PASSWORD}
        response = session.post(f"{BASE_URL}/redfish/v1/SessionService/Sessions", 
                              json=auth_data, timeout=30)
        
        logger.info(f"Ответ аутентификации: код {response.status_code}")
        
        if response.status_code not in [200, 201]:
            logger.error(f"Ошибка аутентификации: код {response.status_code}")
            pytest.fail(f"Ошибка аутентификации: код {response.status_code}")
        
        auth_token = response.headers.get('X-Auth-Token')
        if not auth_token:
            logger.error("Токен аутентификации не получен")
            pytest.fail("Токен аутентификации отсутствует в ответе")
        
        session.headers.update({'X-Auth-Token': auth_token})
        logger.info("Сессия успешно создана")
        
        yield session
        
    except requests.exceptions.Timeout:
        logger.error("Таймаут при создании сессии")
        pytest.fail("Таймаут при создании сессии")
    except requests.exceptions.ConnectionError:
        logger.error("Ошибка подключения к BMC")
        pytest.fail("Не удалось подключиться к BMC")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при создании сессии: {e}")
        pytest.fail(f"Неожиданная ошибка: {e}")
    
    finally:
        # Завершение сессии
        if session:
            try:
                logger.info("Завершение сессии...")
            except Exception as e:
                logger.warning(f"Не удалось завершить сессию: {e}")

def test_authentication(auth_session):
    """Тест аутентификации в OpenBMC через Redfish API"""
    logger.info("Запуск теста аутентификации...")
    try:
        response = auth_session.get(f"{BASE_URL}/redfish/v1", timeout=10)
        logger.info(f"Ответ от Redfish: код {response.status_code}")
        
        assert response.status_code == 200
        logger.info("Аутентификация прошла успешно")
        
    except Exception as e:
        logger.error(f"Ошибка в тесте аутентификации: {e}")
        raise

def test_system_info(auth_session):
    """Тест получения информации о системе"""
    logger.info("Запуск теста информации о системе...")
    try:
        response = auth_session.get(f"{BASE_URL}/redfish/v1/Systems/system", timeout=10)
        logger.info(f"Ответ информации о системе: код {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "Status" in data
        assert "PowerState" in data
        
        power_state = data.get('PowerState')
        logger.info(f"Информация о системе получена. PowerState: {power_state}")
        
    except Exception as e:
        logger.error(f"Ошибка в тесте информации о системе: {e}")
        raise

def test_power_management(auth_session):
    logger.info("Запуск теста управления питанием...")
    try:
        # Получаем начальное состояние
        response = auth_session.get(f"{BASE_URL}/redfish/v1/Systems/system", timeout=10)
        initial_state = response.json().get("PowerState")
        logger.info(f"Начальное состояние питания: {initial_state}")

        # Отправляем команду включения
        power_data = {"ResetType": "On"}
        response = auth_session.post(
            f"{BASE_URL}/redfish/v1/Systems/system/Actions/ComputerSystem.Reset",
            json=power_data,
            timeout=30
        )
        
        logger.info(f"Ответ команды питания: код {response.status_code}")
        assert response.status_code in [202, 204]
        logger.info("Команда питания принята")

        # Ждем и проверяем состояние
        logger.info("Ожидание изменения состояния системы...")
        time.sleep(5)
        
        final_response = auth_session.get(f"{BASE_URL}/redfish/v1/Systems/system", timeout=10)
        final_state = final_response.json().get("PowerState")
        
        valid_states = ["On", "Off", "PoweringOn", "PoweringOff"]
        assert final_state in valid_states
        
        logger.info(f"Текущее состояние системы: {final_state}")
        logger.info("Тест управления питанием завершен")
        
    except Exception as e:
        logger.error(f"Ошибка в тесте управления питанием: {e}")
        raise

def test_cpu_temperature_redfish(auth_session):
    logger.info("Запуск теста температуры CPU...")
    try:
        response = auth_session.get(f"{BASE_URL}/redfish/v1/Chassis/chassis", timeout=10)
        logger.info(f"Ответ данных шасси: код {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            thermal = data.get("Thermal", {})
            
            if isinstance(thermal, str):
                thermal_response = auth_session.get(f"{BASE_URL}{thermal}", timeout=10)
                if thermal_response.status_code == 200:
                    thermal = thermal_response.json()
            
            temperatures = thermal.get("Temperatures", [])
            logger.info(f"Найдено температурных датчиков: {len(temperatures)}")
            
            cpu_found = False
            for temp in temperatures:
                name = temp.get("Name", "")
                reading = temp.get("ReadingCelsius")
                
                if reading is not None and "CPU" in name.upper():
                    cpu_found = True
                    threshold = temp.get('UpperThresholdCritical', 95)
                    
                    if reading <= threshold:
                        logger.info(f"CPU {name}: {reading}°C (порог: {threshold}°C)")
                    else:
                        logger.error(f"CPU {name}: {reading}°C превышает порог {threshold}°C")
                        pytest.fail(f"Температура CPU {reading}°C превышает порог {threshold}°C")
                    break
            
            if not cpu_found:
                logger.info("CPU датчики не найдены")
        else:
            logger.warning("Не удалось получить данные шасси")
            
        logger.info("Тест температуры CPU завершен")
        
    except Exception as e:
        logger.error(f"Ошибка в тесте температуры CPU: {e}")
        raise

def test_cpu_sensors_redfish_ipmi(auth_session):
    logger.info("Запуск теста сравнения датчиков Redfish и IPMI...")
    try:
        # Redfish данные
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
        
        logger.info(f"Redfish CPU датчики: {len(redfish_temps)} найдено")
        
        # IPMI данные
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
                logger.info("IPMI команда выполнена успешно")
            else:
                logger.warning(f"IPMI команда завершилась с ошибкой: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.warning("Таймаут выполнения IPMI команды")
        except Exception as e:
            logger.warning(f"Ошибка выполнения IPMI: {e}")
        
        logger.info(f"IPMI CPU датчики: {len(ipmi_temps)} найдено")
        
        # Анализ результатов
        if redfish_temps and ipmi_temps:
            logger.info("Данные найдены в Redfish и IPMI")
        elif redfish_temps:
            logger.info("Данные найдены только в Redfish")
        elif ipmi_temps:
            logger.info("Данные найдены только в IPMI") 
        else:
            logger.info("Данные не найдены ни в Redfish, ни в IPMI")
            
        logger.info("Тест сравнения датчиков завершен")
            
    except Exception as e:
        logger.error(f"Ошибка в тесте сравнения датчиков: {e}")
        raise



